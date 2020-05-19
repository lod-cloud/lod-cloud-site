package org.insightcentre.lodcloud;

import static com.mongodb.client.model.Filters.eq;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import javax.servlet.ServletException;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import org.bson.Document;
import static org.insightcentre.lodcloud.ContentType.html;
import static org.insightcentre.lodcloud.ContentType.json;
import static org.insightcentre.lodcloud.ContentType.nt;
import static org.insightcentre.lodcloud.ContentType.rdfxml;
import static org.insightcentre.lodcloud.ContentType.turtle;

/**
 *
 * @author jmccrae
 */
@WebServlet(name = "DatasetDetail", urlPatterns = {"/dataset"})
public class DatasetDetail extends HttpServlet {

    private HashMap<String, ContentType> mimeTypes() {
        HashMap<String, ContentType> mimeTypes = new HashMap<>();
        mimeTypes.put("text/html", html);
        mimeTypes.put("application/rdf+xml", rdfxml);
        mimeTypes.put("text/turtle", turtle);
        mimeTypes.put("application/x-turtle", turtle);
        mimeTypes.put("text/plain", nt);
        mimeTypes.put("application/ld+json", json);
        mimeTypes.put("application/json", json);
        mimeTypes.put("application/javascript", json);
        //mimeTypes.put("text/csv" -> csvw);
        return mimeTypes;
    }

    private ContentType negotiate(HttpServletRequest request) {
        try {
        String acceptString = request.getHeader("Accept");
        if (acceptString == null) {
            return html;
        } else {
            String[] acceptSplit = acceptString.split("\\s*,\\s*");
            final HashMap<String, Double> acceptWeighted = new HashMap<>();
            for (int idx = acceptSplit.length - 1; idx >= 0; idx--) {
                String[] qSplit = acceptSplit[idx].split("\\s*;q=\\s*");
                if (qSplit.length == 2 && qSplit[1].matches("0|1|[01]?\\.?[0-9]+")) {
                    acceptWeighted.put(qSplit[0], acceptSplit.length + (1.0 - Double.parseDouble(qSplit[1])));
                } else {
                    acceptWeighted.put(qSplit[0], (double) idx);
                }
            }
            HashMap<String, ContentType> acceptable = mimeTypes();
            List<String> accepted = new ArrayList<>();
            for (Map.Entry<String, Double> e : acceptWeighted.entrySet()) {
                if (acceptable.containsKey(e.getKey())) {
                    accepted.add(e.getKey());
                }
            }
            accepted.sort(new Comparator<String>() {
                @Override
                public int compare(String o1, String o2) {
                    return Double.compare(acceptWeighted.get(o1), acceptWeighted.get(o2));
                }
            });
            if (!accepted.isEmpty()) {
                return acceptable.get(accepted.get(0));
            } else {
                return html;
            }
        }
        } catch(Exception x) {
            x.printStackTrace();
            return html;
        }

    }

    /**
     * Processes requests for both HTTP <code>GET</code> and <code>POST</code>
     * methods.
     *
     * @param request servlet request
     * @param response servlet response
     * @throws ServletException if a servlet-specific error occurs
     * @throws IOException if an I/O error occurs
     */
    protected void processRequest(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        switch (negotiate(request)) {
            case html:
                final Document doc = MongoConnection.getDatasets().find(eq("identifier", MongoConnection.getRequestIdentifier(request))).first();
                if (doc != null) {
                    response.setContentType("text/html;charset=UTF-8");
                    response.addHeader("Vary", "Accept");
                    try (PrintWriter out = response.getWriter()) {
                        Templates.apply(out, Authorize.isLoggedIn(request), getServletContext(),
                                new Templates.XTemplate("dataset-detail", getServletContext()),
                                new Templates.Data(doc, "dataset"),
                                new Templates.JSTemplate("dataset-detail", getServletContext())
                        );
                    }
                } else {
                    response.setStatus(HttpServletResponse.SC_NOT_FOUND);
                    try (PrintWriter out = response.getWriter()) {
                        out.println("Not found");
                    }
                }
                break;
            case json:
                    response.addHeader("Vary", "Accept");
                response.sendRedirect("/json/" + MongoConnection.getRequestIdentifier(request));
                break;
            case rdfxml:
                    response.addHeader("Vary", "Accept");
                response.sendRedirect("/rdf/" + MongoConnection.getRequestIdentifier(request) + "?format=rdf");
                break;
            case turtle:
                    response.addHeader("Vary", "Accept");
                response.sendRedirect("/rdf/" + MongoConnection.getRequestIdentifier(request) + "?format=ttl");
                break;
            case nt:
                    response.addHeader("Vary", "Accept");
                response.sendRedirect("/rdf/" + MongoConnection.getRequestIdentifier(request) + "?format=nt");
                break;
        }
    }

    // <editor-fold defaultstate="collapsed" desc="HttpServlet methods. Click on the + sign on the left to edit the code.">
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
        processRequest(request, response);
    }

    /**
     * Handles the HTTP <code>POST</code> method.
     *
     * @param request servlet request
     * @param response servlet response
     * @throws ServletException if a servlet-specific error occurs
     * @throws IOException if an I/O error occurs
     */
    @Override
    protected void doPost(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        processRequest(request, response);
    }

    /**
     * Returns a short description of the servlet.
     *
     * @return a String containing servlet description
     */
    @Override
    public String getServletInfo() {
        return "Short description";
    }// </editor-fold>

}
