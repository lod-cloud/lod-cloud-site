package org.insightcentre.lodcloud;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.net.URL;
import java.net.HttpURLConnection;
import java.net.URLEncoder;
import java.io.*;
import java.util.*;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;

public class GetData {
    public static Map<String, String> loadIPFSHashes(File file) throws IOException {
        Map<String, String> hashes = new HashMap<>();
        try (BufferedReader br = new BufferedReader(new FileReader(file))) {
            String line;
            while ((line = br.readLine()) != null) {
                // process the line.
                hashes.put(line.split(",")[1], line.split(",")[0]);
            } 
        } catch(Exception x) {
            x.printStackTrace();
            System.out.println("Failed to load IPFS hashes");
            return new HashMap<>();
        }
        return hashes;
    }

    public static void checkURL(String url, Map<String, Object> entry, 
            boolean skipLaundromat, Map<String, String> ipfsHashes,
            final Logger logger, String dataset) {
        entry.put("mirror", new ArrayList<String>());
	List<String> uris = new ArrayList<>();
        if(!skipLaundromat) {
            if(ipfsHashes.containsKey(url)) {
                uris.add("ipfs:" + ipfsHashes.get(url));
            } else {
                uris = new ArrayList<>();
            }
        }
        try {
            Document soup = Jsoup.connect("http://lodlaundromat.org/sparql/?" +
                    URLEncoder.encode(
                        "query=\"PREFIX llo: <http://lodlaundromat.org/ontology/> SELECT DISTINCT ?dataset WHERE {?dataset llo:url <" +
                        url + ">}", "UTF-8")).get();
            for(Element e : soup.select("uri")) {
                uris.add(e.text());
            }
        } catch(Exception e) {
            logger.logError(dataset, e);
            uris = new ArrayList<>();
        }
        if(!uris.isEmpty()) {
            logger.log(dataset, String.format("%s => %s", url, uris.get(0)));
            entry.put("mirror", uris);
            entry.put("status", "OK");
        } else {
            try {
                Document soup = Jsoup.connect(url).get();
                logger.log(dataset, String.format("%s OK", url));
                entry.put("status", "OK");
                entry.put("media_type", soup.select("meta[name=Content-Type]").attr("content"));
            } catch(Exception e) {
                logger.log(dataset, String.format("%s FAIL: (%s)", url, e.getMessage()));
                entry.put("status", "FAIL (" + e.getMessage() + ")");
            }
        }
    }

    public static void checkExample(String url, Map<String, Object> entry,
            final Logger logger, String dataset) {
        try {
            URL u = new URL(url);
            HttpURLConnection conn = (HttpURLConnection)u.openConnection();
            conn.setReadTimeout(30000);
            conn.setConnectTimeout(30000);
            conn.setRequestProperty("Accept", "application/rdf+xml,text/turtle,application/n-triples,application/ld+json,*/*q=0.9");
            conn.connect();
            if(conn.getResponseCode() == 200) {
                logger.log(dataset, String.format("%s OK", url));
                entry.put("status", "OK");
                entry.put("media_type", conn.getContentType());
            } else {
                logger.log(dataset, String.format("%s %d", url, conn.getResponseCode()));
                entry.put("status", "FAIL (" + conn.getResponseCode() + ")");
            }
        } catch(Exception e) {
            logger.log(dataset, String.format("%s FAIL: (%s)", url, e.getMessage()));
            entry.put("status", "FAIL (" + e.getMessage() + ")");
        }
    }

    public static void checkSparql(String url, Map<String, Object> entry,
            final Logger logger, String dataset) {
        try {
            URL u = new URL(url);
            HttpURLConnection conn = (HttpURLConnection)u.openConnection();
            conn.setConnectTimeout(30000);
            conn.setReadTimeout(30000);
            conn.setRequestProperty("Accept", "application/rdf+xml,text/turtle,application/n-triples,application/ld+json,*/*q=0.9");
            conn.connect();
            if(conn.getResponseCode() == 200) {
                logger.log(dataset, String.format("%s OK", url));
                entry.put("status", "OK");
            } else {
                logger.log(dataset, String.format("%s %d", url, conn.getResponseCode()));
                entry.put("status", "FAIL (" + conn.getResponseCode() + ")");
            }
        } catch(Exception e) {
            logger.log(dataset, String.format("%s FAIL: (%s)", url, e.getMessage()));
            entry.put("status", "FAIL (" + e.getMessage() + ")");
        }
    }

    public static Map<String,Object> getData(boolean skipLaundromat, 
            final Map<String, String> ipfsHashes, int numThreads,
            final Logger logger) throws IOException {
        Map<String,Object> data = new ObjectMapper().readValue(
                new URL("https://lod-cloud.net/extract/datasets").openStream(), Map.class);


        logger.log("*", "# Report for LOD Cloud availability");
        logger.log("*", "");

        ExecutorService executor = Executors.newFixedThreadPool(numThreads);

        int counter = 0;
        for(final Map.Entry<String, Object> e : data.entrySet()) {
            executor.execute(new Runnable() {
                public void run() {

                    String identifier = e.getKey();
                    Map<String, Object> dataset = (Map<String, Object>)e.getValue();
                    logger.log(identifier, "## Dataset name: " + dataset.get("identifier"));
                    logger.log(identifier, "");
                    logger.log(identifier, "### Full Downloads (" + ((List)dataset.get("full_download")).size() + ")");
                    logger.log(identifier, "");

                    for(Map<String, Object> full_download : (List<Map<String, Object>>)dataset.get("full_download")) {
                        checkURL((String)full_download.get("download_url"), 
                                full_download, false, ipfsHashes,
                                logger, identifier);
                        logger.log(identifier, "");
                    }

                    logger.log(identifier, "");
                    logger.log(identifier, "### Other downloads (" + ((List)dataset.get("other_download")).size() + ")");

                    if(dataset.containsKey("other_download")) {
                        for(Map<String, Object> other_download : (List<Map<String, Object>>)dataset.get("other_download")) {
                            checkURL((String)other_download.get("access_url"), 
                                    other_download, true, ipfsHashes,
                                    logger, identifier);
                            logger.log(identifier, "");
                        }
                    }

                    if(dataset.containsKey("example")) {
                        logger.log(identifier, "### Examples (" + ((List)dataset.get("example")).size() + ")");

                        for(Map<String, Object> example : (List<Map<String, Object>>)dataset.get("example")) {
                            checkExample((String)example.get("access_url"), example,
                                    logger, identifier);
                            logger.log(identifier, "");
                        }
                    }

                    if(dataset.containsKey("sparql")) {
                        logger.log(identifier, "### SPARQL Endpoints (" + ((List)dataset.get("sparql")).size() + ")");

                        for(Map<String, Object> sparql : (List<Map<String, Object>>)dataset.get("sparql")) {
                            checkSparql((String)sparql.get("access_url"), sparql,
                                    logger, identifier);
                            logger.log(identifier, "");
                        }
                    }

                    if(dataset.containsKey("domain") && dataset.get("domain").equals("cross-domain")) {
                        dataset.put("domain", "cross_domain");
                    }
                    logger.log(identifier, "");
                }
            });
                    
            counter++;
            // For testing
            //if(counter > 5) break;
        }

        executor.shutdown();
        try {
            executor.awaitTermination(1, TimeUnit.DAYS);
        } catch(InterruptedException e) {
            throw new RuntimeException(e);
        }
        return data;
    }

    public static void main(String[] args) throws Exception {
        Map<String, String> ipfsHashes = loadIPFSHashes(new File("ipfs.csv"));

        Map<String, Object> data = getData(false, ipfsHashes, 50,
                new Logger() {
                    public void log(String dataset, String message) {
                        System.out.println("[" + dataset + "] " + message);
                    }
                    public void logError(String dataset, Exception x) {
                        x.printStackTrace();
                    }
                });
        
        try(Writer out = new FileWriter("lod-data.json")) {
            new ObjectMapper().writeValue(out, data);
        }

        int resources = 0;
        int resourcesAvailable = 0;
        Map<String, Integer> links = new HashMap<>();
        links.put("full_download", 0);
        links.put("other_download", 0);
        links.put("example", 0);
        links.put("sparql", 0);
        Map<String, Integer> linksAvailable = new HashMap<>();
        linksAvailable.put("full_download", 0);
        linksAvailable.put("other_download", 0);
        linksAvailable.put("example", 0);
        linksAvailable.put("sparql", 0);

        for(Map.Entry<String, Object> e : data.entrySet()) {
            Map<String, Object> dataset = (Map<String, Object>)e.getValue();
            resources++;
            boolean success = false;
            for(Map.Entry<String, Object> res : dataset.entrySet()) {
                String clazz = res.getKey();
                if(clazz.equals("full_download") || clazz.equals("other_download") || clazz.equals("example") || clazz.equals("sparql")) {
                    List<Map<String, Object>> linkList = (List<Map<String,Object>>)res.getValue();
                    for(Map<String, Object> link : linkList) {
                        links.put(clazz, links.get(clazz) + 1);
                        if(!link.containsKey("status")) {
                            System.out.println("Missing status for " + link.get("access_url") + " (" + clazz + ") of " + dataset.get("identifier"));
                        } else if(link.get("status").equals("OK")) {
                            linksAvailable.put(clazz, linksAvailable.get(clazz) + 1);
                            if(!success) {
                                success = true;
                                resourcesAvailable++;
                            }
                        }
                    }
                }
            }
        }

        System.out.println("|                | Status    |");
        System.out.println("|----------------|-----------|");
        System.out.println(String.format("| Resources      | %4d/%4d |", resourcesAvailable, resources));
        System.out.println(String.format("| Full Download  | %4d/%4d |", linksAvailable.get("full_download"), links.get("full_download")));
        System.out.println(String.format("| Other Download | %4d/%4d |", linksAvailable.get("other_download"), links.get("other_download")));
        System.out.println(String.format("| Example        | %4d/%4d |", linksAvailable.get("example"), links.get("example")));
        System.out.println(String.format("| SPARQL         | %4d/%4d |", linksAvailable.get("sparql"), links.get("sparql")));


    }

    public static interface Logger {
        public void log(String dataset, String message);
        public void logError(String dataset, Exception e);
    }
}
