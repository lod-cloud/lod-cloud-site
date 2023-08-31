package org.insightcentre.lodcloud;

import java.io.BufferedReader;
import java.io.PrintWriter;
import java.util.List;
import java.util.ListIterator;
import java.util.HashMap;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import static javax.servlet.http.HttpServletResponse.SC_OK;
import org.apache.http.HttpStatus;

import static org.insightcentre.lodcloud.MongoConnection.getDatasets;
import static org.insightcentre.lodcloud.MongoConnection.getRequestIdentifier;
import java.io.IOException;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import static javax.servlet.http.HttpServletResponse.SC_BAD_REQUEST;

import org.json.simple.JSONArray;
import org.json.simple.JSONObject;
import org.json.simple.parser.JSONParser;
import org.json.simple.parser.ParseException;

/**
 *
 * @author jmccrae
 */
public class LODCloudServlet extends HttpServlet {

    /**
     * Handles the HTTP <code>GET</code> method.
     *
     * @param request servlet request
     * @param response servlet response
     * @throws ServletException if a servlet-specific error occurs
     * @throws IOException if an I/O error occurs
     */
    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        final List<Document> datasets = getDatasets();
        final Document doc = datasets.stream().
            filter((d) -> d.get("identifier", "").equals(getRequestIdentifier(request))).
            findFirst().orElse(null);
        if (doc != null) {
            response.setContentType("application/javascript");
            response.setStatus(SC_OK);
            try (final PrintWriter out = response.getWriter()) {
                out.println(doc.toJson());
            }
        } else {
            response.setStatus(HttpServletResponse.SC_NOT_FOUND);
            try (final PrintWriter out = response.getWriter()) {
                out.println("Not found");
            }

        }
    }

    public boolean validate_json(Document doc) {
        JSONParser parser = new JSONParser();

        try {

            Object obj = parser.parse(doc.toJson());
            JSONObject jsonObject = (JSONObject) obj;

            //System.out.println(jsonObject);
//        System.out.println(jsonObject.get("website").toString());
//        System.out.println(jsonObject.get("full_download").getClass());
            if (jsonObject.get("website") != null) {
                if (jsonObject.get("website").toString().toLowerCase().startsWith("http")
                        || jsonObject.get("website").toString().toLowerCase().startsWith("https")) {
                    //System.out.println("website field is fine");
                }
            } else {
                return false;
            }

            if (jsonObject.get("description") instanceof org.json.simple.JSONObject) {
                //System.out.println("Description field is fine");
            } else {
                return false;
            }

            if (jsonObject.get("full_download") instanceof org.json.simple.JSONObject
                    || jsonObject.get("full_download") instanceof org.json.simple.JSONArray) {
                //System.out.println("full download field is fine");
            } else {
                return false;
            }
            //System.out.println(jsonObject.get("title").toString().indexOf(" "));
            if (jsonObject.get("title").toString().indexOf(" ") == -1) {
               // System.out.println("title field is fine");
            } else {
                return false;
            }
            if (((JSONObject) jsonObject.get("contact_point")).get("name") instanceof java.lang.String) {
                //System.out.println("name field is fine");
            } else {
                return false;
            }

            if (((JSONObject) jsonObject.get("contact_point")).get("email").toString().contains("@")) {
                //System.out.println("email field is fine");
            } else {
                return false;
            }

            if (jsonObject.get("domain").toString().toLowerCase().matches("government|cross-domain|geography|life_sciences|linguistics|media|publications|social_networking|user_generated")) {
                //System.out.println("domain field is fine");
            } else {
                return false;
            }

            for (int i = 0; i < ((JSONArray) jsonObject.get("keywords")).size(); i++) {
                if (((JSONArray) jsonObject.get("keywords")).get(i) instanceof java.lang.String) {
                    //System.out.println(((JSONArray) jsonObject.get("keywords")).get(i));
                } else {
                    return false;
                }
            }

            Pattern p = Pattern.compile("([0-9])");
            if(jsonObject.get("triples") instanceof String) {
                Matcher m = p.matcher((String) jsonObject.get("triples"));

                if (m.find()) {
                    //System.out.println("numbers in triples");
                } else {
                    return false;
                }
            }

        } catch (ParseException e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        }
        return true;

    }

    @Override
    protected void doPost(HttpServletRequest request, HttpServletResponse resp)
            throws ServletException, IOException {
        try {
        final User user = Authorize.getUser(request);
        if (user == null) {
            resp.setStatus(HttpStatus.SC_UNAUTHORIZED);
            try (PrintWriter out = resp.getWriter()) {
                out.println("Please authenticate with Google");
            }
            return;
        }
        final List<Document> datasets = getDatasets();
        final StringBuilder json = new StringBuilder();
        try (final BufferedReader reader = request.getReader()) {
            final String line = reader.readLine();
            if(line == null || line.equals("null")) {
                resp.sendError(SC_BAD_REQUEST);
                System.err.println("Null request");
                return;
            }
            json.append(line).append("\n");
            final Document doc = Document.parse(json.toString());
            doc.put("owner", new HashMap<String, String>() {
                {
                    put("name", user.name);
                    put("email", user.emailAddress);
                }
            });
           // if (validate_json(doc)) {
            int modifiedCount = 0;
            ListIterator<Document> iter = datasets.listIterator();
            while(iter.hasNext()) {
                Document d = iter.next();
                if(d.get("identifier").equals(getRequestIdentifier(request))) {
                    iter.set(doc);
                    modifiedCount++;
                }
            }
                if (modifiedCount > 0) {
                    resp.setStatus(SC_OK);
                    try (final PrintWriter out = resp.getWriter()) {
                        out.println("OK");
                    }
                } else {
                    resp.setStatus(HttpServletResponse.SC_NOT_FOUND);
                    try (final PrintWriter out = resp.getWriter()) {
                        out.println("No changes have been made");
                    }

                }

                String timeStamp = String.format("%016x", System.currentTimeMillis());
                doc.put("time", timeStamp);
                doc.put("_id", doc.get("identifier") + timeStamp);
                MongoConnection.getHistory().add(doc);
           // } else {
           //     resp.sendError(HttpServletResponse.SC_BAD_REQUEST);
           // }
        }
        } catch(Exception x) {
            x.printStackTrace();
            resp.sendError(HttpServletResponse.SC_INTERNAL_SERVER_ERROR, x.getMessage());
        }
    }

    /**
     * Handles the HTTP <code>DELETE</code> method.
     *
     * @param req servlet request
     * @param resp servlet response
     * @throws ServletException if a servlet-specific error occurs
     * @throws IOException if an I/O error occurs
     */
    @Override
    protected void doDelete(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        final User user = Authorize.getUser(req);
        if (user == null) {
            resp.setStatus(HttpStatus.SC_UNAUTHORIZED);
            try (PrintWriter out = resp.getWriter()) {
                out.println("Please authenticate with Google");
            }
            return;
        }
        final List<Document> datasets = getDatasets();
        int deletedCount = 0;
        ListIterator<Document> iter = datasets.listIterator();
        while(iter.hasNext()) {
            Document d = iter.next();
            if(d.get("identifier").equals(getRequestIdentifier(req))) {
                iter.remove();
                deletedCount++;
            }
        }
        if (deletedCount > 0) {
            Document doc = new Document();
            doc.put("identifier", getRequestIdentifier(req));
            doc.put("owner", new HashMap<String, String>() {
                {
                    put("name", user.name);
                    put("email", user.emailAddress);
                }
            });
            String timeStamp = String.format("%016x", System.currentTimeMillis());
            doc.put("time", timeStamp);
            doc.put("_id", doc.get("identifier") + timeStamp);
            MongoConnection.getHistory().add(doc);
            resp.setStatus(SC_OK);
            try (final PrintWriter out = resp.getWriter()) {
                out.println("OK");
            }
        } else {
            resp.setStatus(HttpServletResponse.SC_NOT_FOUND);
            try (final PrintWriter out = resp.getWriter()) {
                out.println("Not found");
            }

        }
    }

    /**
     * Handles the HTTP <code>DELETE</code> method.
     *
     * @param req servlet request
     * @param resp servlet response
     * @throws ServletException if a servlet-specific error occurs
     * @throws IOException if an I/O error occurs
     */
    @Override
    protected void doPut(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        final User user = Authorize.getUser(req);
        if (user == null) {
            resp.setStatus(HttpStatus.SC_UNAUTHORIZED);
            try (PrintWriter out = resp.getWriter()) {
                out.println("Please authenticate with Google");
            }
            return;
        }
        if(getRequestIdentifier(req).equals("")) {
            resp.setStatus(SC_BAD_REQUEST);
            try (final PrintWriter out = resp.getWriter()) {
                out.println("No identifier");
            }
            return;
        }
        if(getRequestIdentifier(req).contains(" ") || getRequestIdentifier(req).contains("/") || getRequestIdentifier(req).contains("\\") || getRequestIdentifier(req).contains("?")) {
            resp.setStatus(SC_BAD_REQUEST);
            try (final PrintWriter out = resp.getWriter()) {
                out.println("Identifier contains invalid characters");
            }
            return;
        }

        final List<Document> datasets = getDatasets();
        final StringBuilder json = new StringBuilder();
        try (final BufferedReader reader = req.getReader()) {
            json.append(reader.readLine()).append("\n");
            if (datasets.stream().filter((d) -> d.get("identifier", "").equals(getRequestIdentifier(req))).findFirst().orElse(null) == null) {
                Document doc = Document.parse(json.toString());
                doc.put("_id", doc.get("identifier"));
                if (doc.get("_id", "").equals("")) {
                    resp.setStatus(HttpServletResponse.SC_FORBIDDEN);
                    try (final PrintWriter out = resp.getWriter()) {
                        out.println("No identifier");
                    }
                    return;

                }
                doc.put("owner", new HashMap<String, String>() {
                    {
                        put("name", user.name);
                        put("email", user.emailAddress);
                    }
                });
                datasets.add(doc);
                String timeStamp = String.format("%016x", System.currentTimeMillis());
                doc.put("time", timeStamp);
                doc.put("_id", doc.get("identifier") + timeStamp);
                MongoConnection.getHistory().add(doc);
                resp.setStatus(SC_OK);
                try (final PrintWriter out = resp.getWriter()) {
                    out.println("OK");
                }
            } else {
                resp.setStatus(HttpServletResponse.SC_FORBIDDEN);
                try (final PrintWriter out = resp.getWriter()) {
                    out.println("Resource already exists");
                }
            }
        }
    }

    /**
     * Returns a short description of the servlet.
     *
     * @return a String containing servlet description
     */
    @Override
    public String getServletInfo() {
        return "LOD Cloud CRUD API";
    }

}
