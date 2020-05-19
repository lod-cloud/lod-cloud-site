package org.insightcentre.lodcloud;

import com.mongodb.Function;
import com.mongodb.client.MongoCursor;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.Collections;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import org.bson.Document;

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
		final MongoCursor<Document> docs = MongoConnection.getDatasets().find( new Document("identifier", new Document("search", query))/*.append("caseSensitive", new Boolean(caseSensitive)).append("diacriticSensitive", new Boolean(diacriticSensitive)))*/ ).map(new Function<Document, Document>() {	
																			
			@Override
            public Document apply(Document t) {
				
                Document d = new Document();
                String id = t.get("identifier", "");
                String title = t.get("title", "");
                Object description = t.get("description");
                d.put("_id", id);
                d.put("title", title); 
				System.err.println(title);
                d.put("description", description);
                return d;
            }
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
