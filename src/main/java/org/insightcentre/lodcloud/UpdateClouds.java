package org.insightcentre.lodcloud;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.Map;
import java.util.HashMap;
import java.io.FileWriter;
import java.io.Writer;
import java.io.IOException;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.text.SimpleDateFormat;
import java.util.Date;

public class UpdateClouds {

  public static void updateIndex(String links, String dataset, String date) throws IOException {
    StringBuffer newTemplate = new StringBuffer();
    StringBuffer newIndex = new StringBuffer();
    try(BufferedReader reader = new BufferedReader(
          new InputStreamReader(UpdateClouds.class.getResourceAsStream("index-template")))) {
      String line;
      while((line = reader.readLine()) != null) {
        if(line.contains("==LINKS==")) {
          newIndex.append(line.replace("==LINKS==", links));
          newIndex.append(line.replace("==DATASET==", dataset));
        } else if(line.contains("--TABLE--")) {
          String toInsert = "<tr typeof=\"dctype:Image\" about=\"#cloud\" property=\"dc:title\" content=\"LOD cloud diagram\">\n"
            + "<th property=\"dc:modified\" datatype=\"xsd:date\" content=\"" + date + "\">" + date + "</th>\n" 
            + "<td></td><td></td><td></td><td>"
            + "<a href=\"versions/" + date + "/lod-cloud.png\">png</a></td>" 
            + "<td></td>" 
            + "<td><a href=\"versions/" + date + "/lod-cloud.svg\">svg</a></td>"
            + "<td><a href=\"versions/" + date + "/lod-data.json\">json</a></td>" 
            + "<td></td><td class=\"dataset-count\">" + dataset + "</td></tr>";

          newTemplate.append(line);
          newTemplate.append(toInsert);
          newIndex.append(line);
        } else {
          newTemplate.append(line);
        }
      }

    }
    try(PrintWriter out = new PrintWriter("index.html")) {
      out.println(newIndex.toString());
    }
    try(PrintWriter out = new PrintWriter("index-template")) {
      out.println(newTemplate.toString());
    }
  }

  public void doCloudUpdate() throws Exception {
    Map<String, Object> data = GetData.getData(false, new HashMap<String, String>(), 50,
        new GetData.Logger() {
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

    GenerateClouds.main(null);

    CountLinks cl = new CountLinks();
    cl.count("clouds/lod-cloud.svg");

    String date = new SimpleDateFormat("YYYY-MM-dd").format(new Date());

    
  }
}
