package org.insightcentre.lodcloud;

import java.io.IOException;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.List;
import java.util.Iterator;
import static java.util.Collections.sort;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.util.HashMap;

/**
 *
 * @author John McCrae
 */
public class DatasetEdit extends /*AbstractAuthorizationCodeServlet*/ HttpServlet {

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
        final List<Document> datasets = MongoConnection.getDatasets();
        final User user = Authorize.getUser(request);
        if(user == null) {
            Authorize.redirectToAuthorize(response, "/edit-dataset/" + MongoConnection.getRequestIdentifier(request));
            return;
        }
        final Iterator<String> docs = datasets.stream().
            map((d) -> d.get("identifier","")).iterator();
        final ArrayList<String> docList = new ArrayList<>();
        while (docs.hasNext()) {
            docList.add(docs.next());
        }
        sort(docList);
		final ArrayList<String> domainList = new ArrayList<String>() {{
			add("cross-domain");
			add("geography");
			add("government");
			add("life_sciences");
			add("linguistics");
			add("media");
			add("publications");
			add("social_networking");
			add("user_generated");
		}}; 
		
		
		final HashMap<String,String> domainsMappings = new HashMap<String,String>(){{
			put("cross-domain", "Cross-domain");
			put("geography", "Geography");
			put("government", "Government");
			put("life_sciences", "Life Sciences");
			put("linguistics", "Linguistics");
			put("media", "Media");
			put("publications", "Publications");
			put("social_networking", "Social Networking");
			put("user_generated", "User Generated");			
			}};
		//["cross-domain", "geography", "government", "life_sciences", "linguistics", "media", "publications", "social_networking", "user_generated"];
        final Document dataset = datasets.stream().
            filter((d) -> d.get("identifier", "").equals(MongoConnection.getRequestIdentifier(request))).findFirst().orElse(null);
        if (dataset != null) {

        final Document doc = new Document();
        doc.put("dataset", dataset);
        doc.put("forLinks", docList);
		doc.put("domains", domainList);
		doc.put("domainsMap", domainsMappings);

            response.setContentType("text/html;charset=UTF-8");
            response.addHeader("Vary", "Accept");
            try (PrintWriter out = response.getWriter()) {
                Templates.apply(out, Authorize.isLoggedIn(request), getServletContext(),
                        new Templates.XTemplate("dataset-edit", getServletContext()),
                        new Templates.Data(doc, null),
                        new Templates.JSTemplate("dataset-edit", getServletContext())
                );
            }
        } else {
            response.setStatus(HttpServletResponse.SC_NOT_FOUND);
            try (PrintWriter out = response.getWriter()) {
                out.println("Not found");
            }
        }
    }

}
