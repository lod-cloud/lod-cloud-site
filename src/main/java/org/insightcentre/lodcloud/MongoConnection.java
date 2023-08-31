package org.insightcentre.lodcloud;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import javax.servlet.http.HttpServletRequest;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * Access to in-memory store
 * @author jmccrae
 */
public class MongoConnection {
    private static final ArrayList<Document> documents = new ArrayList<>();
    private static final ArrayList<Document> history = new ArrayList<>();

    static {
        try {
            BufferedReader br = new BufferedReader(new FileReader(new File("lod-data.json")));
            Map<String, Object> data = new ObjectMapper().readValue(br, Map.class);
            for(Object o : data.values()) {
                Document d = new Document((Map<String,Object>)o);
                d.put("identifier", d.get("identifier", "").replaceAll(" ", "_").replaceAll("[?/\\\\]", ""));
                d.put("_id", d.get("_id", "").replaceAll(" ", "_").replaceAll("[?/\\\\]", ""));
                documents.add(d);
            }
        } catch(Exception x) {
            x.printStackTrace();
        }
    }

    public static List<Document> getDatasets() {
        return documents;
    }
	
    public static List<Document> getHistory() {
        return history;
    }

    public static String getRequestIdentifier(HttpServletRequest req) {
        return req.getPathInfo().replaceAll("^/*", "");
    }


}
