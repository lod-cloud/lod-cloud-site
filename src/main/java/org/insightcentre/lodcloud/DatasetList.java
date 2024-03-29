package org.insightcentre.lodcloud;

import java.io.IOException;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Iterator;
import java.util.regex.Pattern;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

/**
 *
 * @author jmccrae
 */
public class DatasetList extends HttpServlet {

    /**
     * Processes requests for both HTTP <code>GET</code> and <code>POST</code>
     * methods.
     *
     * @param request servlet request
     * @param response servlet response
     * @throws ServletException if a servlet-specific error occurs
     * @throws IOException if an I/O error occurs
     */
    protected void processRequest(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
		
		final String searchString = (request.getParameter("search") != null) ? request.getParameter("search") : "";
				
		
                Pattern regexQuery = Pattern.compile(".*" + Pattern.quote(searchString) + ".*", Pattern.CASE_INSENSITIVE);
		//Document regexQuery = new Document();
		//regexQuery.append("$regex", ".*" + Pattern.quote(searchString) + ".*");
		//		
		//BasicDBList or = new BasicDBList();
		//or.add(new BasicDBObject("_id", regexQuery));
		//or.add(new BasicDBObject("title", regexQuery));
		//or.add(new BasicDBObject("description.en", regexQuery));
		//BasicDBObject findQuery = new BasicDBObject("$or", or);
		
		final long collectionSize = MongoConnection.getDatasets().size();
		//System.err.println(MongoConnection.getDatasets().count());
		//System.err.println(collectionSize["$numberLong"]);
		
        final ArrayList<Document> docList = new ArrayList<>();
        final Iterator<Document> docs = MongoConnection.getDatasets().stream()
            .filter((d) -> {
                if(searchString.equals("")) {
                    return true;
                } else {
                    String id = d.get("_id", "");
                    String title = d.get("title", "");
                    Object description = d.get("description");
                    return regexQuery.matcher(id).matches() || regexQuery.matcher(title).matches() || regexQuery.matcher(description.toString()).matches();
                }
            }).map((t) -> {
                Document d = new Document();
                String id = t.get("identifier", "");
                String title = t.get("title", "");
                Object description = t.get("description");				
				//description["en"] = description["en"].substring(0,50) + "...";
                d.put("_id", id);
                d.put("title", title);
                d.put("description", description);
                return d;
        }).iterator();

        while (docs.hasNext()) {
            docList.add(docs.next());
        }
        Document doc = new Document();
        doc.put("datasets", docList);
		doc.put("collectionSize", collectionSize);
        doc.put("searchQuery", "");
        doc.put("datasetsToShow",Collections.EMPTY_LIST);
        doc.put("pager", "{}");

        response.setContentType("text/html;charset=UTF-8");
        try (PrintWriter out = response.getWriter()) {
            Templates.apply(out, Authorize.isLoggedIn(request), getServletContext(),
                    new Templates.XTemplate("dataset-list", getServletContext()),
                    new Templates.Data(doc, null),
                    new Templates.JSTemplate("dataset-list", getServletContext())
            );
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
