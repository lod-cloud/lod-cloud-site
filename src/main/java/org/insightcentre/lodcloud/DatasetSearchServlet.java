package org.insightcentre.lodcloud;

import java.io.IOException;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Iterator;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

//import org.springframework.data.mongodb.core.query.*;
//import org.springframework.data.mongodb.core.MongoOperations;

/**
 *
 * @author jmccrae
 */
public class DatasetSearchServlet extends HttpServlet {

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
		final String query = request.getParameter("search");
		final Boolean caseSensitive = "true".equals(request.getParameter("caseSensitive"));
		System.err.println(query);
		final Boolean diacriticSensitive = "true".equals(request.getParameter("diacriticSensitive"));
		
		//Criteria criteria = Criteria.where("description").regex(query);
		//Query query = Query.query(criteria);
		
        final ArrayList<Document> docList = new ArrayList<>();
		
        //final MongoCursor<Document> docs = MongoConnection.getDatasets().find(new Document("$title", new Document("$search", query).append("$caseSensitive", new Boolean(caseSensitive)).append("$diacriticSensitive", new Boolean(diacriticSensitive)))).map(new Function<Document, Document>() {
		//query == null ? new Document() : query.getQuery()
        final Iterator<Document> docs = MongoConnection.getDatasets().stream()
            .filter((d) -> d.get("identifier", "").toLowerCase().contains(query.toLowerCase()))
            .map((d) -> {
                Document doc = new Document();
                String id = d.get("identifier", "");
                String title = d.get("title", "");
                Object description = d.get("description");
                doc.put("_id", id);
                doc.put("title", title);
                doc.put("description", description);
                return doc;
            }).iterator();

        while (docs.hasNext()) {
            docList.add(docs.next());
        }
        Document doc = new Document();
        doc.put("datasets", docList);
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
	
	public static void redirectToSearch(HttpServletResponse resp, String searchValue) throws IOException {
        resp.sendRedirect( searchValue != null ? "?search=" + searchValue : "" );
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
