package org.insightcentre.lodcloud;

import static com.mongodb.client.model.Filters.eq;
import java.io.IOException;
import java.io.PrintWriter;
import java.io.UnsupportedEncodingException;
import java.net.URLEncoder;
import java.util.ArrayList;
import java.util.Map;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.vocabulary.DCAT;
import org.apache.jena.vocabulary.DCTerms;
import org.apache.jena.vocabulary.RDF;
import org.apache.jena.vocabulary.RDFS;
import org.apache.jena.vocabulary.VOID;
import org.apache.jena.vocabulary.XSD;
import static org.insightcentre.lodcloud.MongoConnection.getDatasets;
import static org.insightcentre.lodcloud.MongoConnection.getRequestIdentifier;

/**
 *
 * @author jmccrae
 */
public class RDFView extends HttpServlet {

    private static Resource mkUri(Model model, String uri) {
        return model.createResource(uri.replaceAll("<", "%3C").replaceAll(">", "%3E"));
    }
    
    static Model createResource(Document document, String identifier, Model model) throws UnsupportedEncodingException {
        
        final String FOAF = "http://xmlns.com/foaf/0.1/";
               
        Resource ds_node = model.createResource("http://lod-cloud.net/dataset/" + URLEncoder.encode(identifier, "UTF-8"));
        
        ds_node.addProperty(RDF.type, VOID.Dataset);
        ds_node.addProperty(DCTerms.title, model.createLiteral(document.get("title", ""), "en"));
        for(Map.Entry<String,Object> e : document.get("description", new Document()).entrySet()) {
            ds_node.addProperty(DCTerms.description, model.createLiteral(
                    e.getValue() != null ? e.getValue().toString() : "", e.getKey()));
        }
        for(Document d : document.get("full_download", new ArrayList<Document>())) {
            ds_node.addProperty(VOID.dataDump, mkUri(model, d.get("download_url", "")));
        }
        for(Document d : document.get("sparql", new ArrayList<Document>())) {
            ds_node.addProperty(VOID.sparqlEndpoint, mkUri(model, d.get("access_url", "")));
        }
        for(Document d : document.get("example", new ArrayList<Document>())) {
            ds_node.addProperty(VOID.exampleResource, mkUri(model, d.get("access_url", "")));
        }
        for(Document d : document.get("other_download", new ArrayList<Document>())) {
            Resource b = model.createResource();
            ds_node.addProperty(DCAT.distribution, b);
            b.addProperty(DCAT.accessURL, mkUri(model, d.get("access_url", "")));
        }
        for(String keyword : document.get("keywords", new ArrayList<String>())) {
            ds_node.addProperty(DCTerms.subject, model.createLiteral(keyword));
        }
        if(document.containsKey("domain") && !document.get("domain", "").equals("")) {
            ds_node.addProperty(DCTerms.subject, model.createLiteral(document.get("domain", "")));
        }
        if(document.containsKey("website") && !document.get("website", "").equals("")) {
            ds_node.addProperty(model.createProperty(FOAF, "homepage"), 
                    mkUri(model,document.get("website", "")));
        }
        
        if(document.containsKey("contact_point")) {
            Resource b = model.createResource();
            ds_node.addProperty(DCTerms.publisher, b);
            Document cp = document.get("contact_point", new Document());
            if(cp.containsKey("name")) {
                b.addProperty(RDFS.label, model.createLiteral(cp.get("name","")));
            }
            if(cp.containsKey("email")) {
                b.addProperty(model.createProperty(FOAF, "mbox"),
                        model.createLiteral(cp.get("email","")));
                
            }
        }
        for(Document l : document.get("links", new ArrayList<Document>())) {
            Resource b = model.createResource();
            b.addProperty(VOID.target, ds_node);
            Resource targ = model.createResource("http://lod-cloud.net/dataset/" + l.get("target", ""));
            b.addProperty(VOID.target, targ);
            b.addProperty(VOID.triples, model.createTypedLiteral(l.get("value", ""), XSD.integer.getURI()));
        }
        if(document.containsKey("triples")) {
            Object o = document.get("triples");
            if(o == null) {
                ds_node.addProperty(VOID.triples, model.createTypedLiteral(0, XSD.integer.getURI()));
            } else if (o instanceof Integer) {
                ds_node.addProperty(VOID.triples, model.createTypedLiteral((int)o));
            } else {
                ds_node.addProperty(VOID.triples, model.createTypedLiteral(o.toString(), XSD.integer.getURI()));
            }
        }
        if(document.containsKey("license_url")) {
            ds_node.addProperty(DCTerms.license, mkUri(model, document.get("license_url", "")));
        }
        
        model.setNsPrefix("void", VOID.getURI());
        model.setNsPrefix("dcterms", DCTerms.getURI());
        model.setNsPrefix("foaf", FOAF);
        model.setNsPrefix("dcat", DCAT.getURI());
        model.setNsPrefix("rdfs", RDFS.getURI());
        model.setNsPrefix("xsd", XSD.getURI());
        
      
        return model;
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
        final Document doc = getDatasets().stream()
            .filter((d) -> d.get("identifier", "").equals(getRequestIdentifier(request))).findFirst().orElse(null);
        String format = request.getParameter("format");
        final String mimeType;
        if(format == null) {
            format = "TURTLE";
            mimeType = "text/turtle;charset=UTF-8";
        } else if(format.equals("ttl")) {
            format = "TURTLE";
            mimeType = "text/turtle;charset=UTF-8";            
        } else if(format.equals("rdf")) {
            format = "RDF/XML";
            mimeType = "application/rdf+xml;charset=UTF-8";       
        } else if(format.equals("nt")) {
            format = "N-TRIPLES";
            mimeType = "application/n-triples;charset=UTF-8";       
        } else {
            format = "TURTLE";
            mimeType = "text/turtle;charset=UTF-8";
        }
        if (doc != null) {
            
            response.setContentType(mimeType);
            final Model model = createResource(doc, getRequestIdentifier(request),
                    ModelFactory.createDefaultModel());
            try (PrintWriter out = response.getWriter()) {
                model.write(out, format);
            }
        } else {
            response.setStatus(HttpServletResponse.SC_NOT_FOUND);
            try (PrintWriter out = response.getWriter()) {
                out.println("Not found");
            }
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
