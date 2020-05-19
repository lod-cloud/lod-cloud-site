package org.insightcentre.lodcloud;

import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import com.mongodb.client.MongoCollection;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import javax.servlet.http.HttpServletRequest;
import org.bson.Document;

/**
 * Access to Mongo database
 * @author jmccrae
 */
public class MongoConnection {
    private static String server;
    static {
        try {
            server = new BufferedReader(new FileReader("mongodb.txt")).readLine();
        } catch(Exception x) {
            System.err.println("No file at " + new File("mongodb.txt").getAbsolutePath() + " defaulting to localhost for MongoDB");
            server = "mongodb://localhost:27017";
        }
    }

    private static final MongoClient mongo = MongoClients.create(server);

    public static MongoCollection<Document> getDatasets() {
        return mongo.getDatabase("mern-dataset-app").getCollection("datasets");
    }
	
    public static MongoCollection<Document> getHistory() {
        return mongo.getDatabase("mern-dataset-app").getCollection("history");
    }

    public static String getRequestIdentifier(HttpServletRequest req) {
        return req.getPathInfo().replaceAll("^/*", "");
    }


}
