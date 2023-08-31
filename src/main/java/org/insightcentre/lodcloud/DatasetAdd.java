package org.insightcentre.lodcloud;

import com.google.api.client.auth.oauth2.AuthorizationCodeFlow;
import com.google.api.client.auth.oauth2.BearerToken;
import com.google.api.client.auth.oauth2.StoredCredential;
import com.google.api.client.extensions.servlet.auth.oauth2.AbstractAuthorizationCodeServlet;
import com.google.api.client.http.BasicAuthentication;
import com.google.api.client.http.GenericUrl;
import com.google.api.client.http.javanet.NetHttpTransport;
import com.google.api.client.util.store.FileDataStoreFactory;
import com.google.api.client.json.jackson.JacksonFactory;
import java.io.File;
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
import org.json.simple.JSONArray;
import org.json.simple.JSONObject;

/**
 *
 * @author John McCrae
 */
public class DatasetAdd extends /*AbstractAuthorizationCodeServlet*/ HttpServlet {

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
            Authorize.redirectToAuthorize(response, "/add-dataset" );
            return;
        }
        final Iterator<String> docs = datasets.stream().map((d) -> d.get("identifier","")).iterator();
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
        //final Document dataset = datasets.find(eq("identifier", MongoConnection.getRequestIdentifier(request))).first();
		
		JSONObject dataset_json = new JSONObject(){{
			put("_id", "");
			put("title", "");
			put("description", new JSONObject() {{
                            put("en","");
                        }});
			
			put("full_download", new JSONArray());
			put("other_download", new JSONArray());
			put("sparql", new JSONArray());
			put("example", new JSONArray());
			put("links", new JSONArray());
			put("contact_point", new JSONObject(){{
				put("email", "");
				put("name", "");
				}});			
			put("keywords", new JSONArray());
			put("domain", "");
			put("website", "");
			put("license", "");
			put("triples", 0);
			put("namespace", "");
			put("doi", "");
			put("Image", "");	
			
			put("owner", new JSONObject(){{
				put("email", "");
				put("name", "");
				}});
				
				
			}};
		//final Document dataset = Document.parse( dataset_json.toString() );
		
        final Document doc = new Document();
        doc.put("dataset", dataset_json);
        doc.put("forLinks", docList);
		doc.put("domains", domainList);
		doc.put("domainsMap", domainsMappings);

        if (doc != null) {
            response.setContentType("text/html;charset=UTF-8");
            response.addHeader("Vary", "Accept");
            try (PrintWriter out = response.getWriter()) {
                Templates.apply(out, Authorize.isLoggedIn(request), getServletContext(),
                        new Templates.XTemplate("dataset-edit", getServletContext()),
                        new Templates.Data(doc, null),
                        new Templates.JSTemplate("dataset-add", getServletContext())
                );
            }
	    UpdateClouds.triggerUpdate();
        } else {
            response.setStatus(HttpServletResponse.SC_NOT_FOUND);
            try (PrintWriter out = response.getWriter()) {
                out.println("Not found");
            }
        }
    }

}
