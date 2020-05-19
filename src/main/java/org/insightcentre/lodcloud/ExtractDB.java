package org.insightcentre.lodcloud;

import com.mongodb.client.MongoCollection;
import java.io.IOException;
import java.io.OutputStream;
import java.io.PrintWriter;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.riot.RDFFormat;
import org.bson.Document;
import org.bson.json.JsonWriterSettings;

/**
 *
 * @author John McCrae <john@mccr.ae>
 */
public class ExtractDB extends HttpServlet {

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
        String pathInfo = request.getPathInfo();
        if ("/datasets".equals(pathInfo)) {
            MongoCollection<Document> docs = MongoConnection.getDatasets();
            Document docMap = new Document();
            for (Document doc : docs.find()) {
                docMap.put(doc.get("identifier", "doc" + doc.hashCode()), doc);
            }

            response.setContentType("application/json");
            try (PrintWriter out = response.getWriter()) {
                out.println(docMap.toJson(JsonWriterSettings.builder().indent(true).build()));
            }
        } else if ("/history".equals(pathInfo))  {
            MongoCollection<Document> docs = MongoConnection.getHistory();
            response.setContentType("text/plain");
            try (PrintWriter out = response.getWriter()) {
                for (Document doc : docs.find()) {
                    out.println(doc.toJson());

                }
            }
        } else if ("/rdf".equals(pathInfo)) {
            MongoCollection<Document> docs = MongoConnection.getDatasets();
            Model model = ModelFactory.createDefaultModel();
            for(Document doc : docs.find()) {
                RDFView.createResource(doc, doc.get("identifier", ""), model);
            }
            try (OutputStream out = response.getOutputStream()) {
                //model.write(out, "N-TRIPLE");
                RDFDataMgr.write(out, model, RDFFormat.NTRIPLES_ASCII);
            }
            
        } else {
            response.sendError(HttpServletResponse.SC_NOT_FOUND);
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
