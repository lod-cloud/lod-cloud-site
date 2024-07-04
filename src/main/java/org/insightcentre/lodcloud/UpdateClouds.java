package org.insightcentre.lodcloud;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.core.type.TypeReference;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.InputStreamReader;
import java.io.IOException;
import java.io.PrintWriter;
import java.io.Writer;
import java.net.HttpURLConnection;
import java.net.URL;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;
import java.util.List;
import java.io.FileInputStream;
import java.util.Base64;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.ServletException;

public class UpdateClouds extends HttpServlet {

  private static String GH_TOKEN;

  static {
    try(BufferedReader reader = new BufferedReader(new FileReader("gh-token"))) {
      GH_TOKEN = reader.readLine();
    } catch(Exception x) {
      x.printStackTrace();
    }
  }

  public static void updateIndex(String links, String dataset, String date) throws IOException {
    StringBuffer newTemplate = new StringBuffer();
    StringBuffer newIndex = new StringBuffer();
    try(BufferedReader reader = new BufferedReader(new InputStreamReader(
      new URL("https://raw.githubusercontent.com/lod-cloud/lod-cloud-site/main/src/main/webapp/index-template").openStream()))) {
      String line;
      while((line = reader.readLine()) != null) {
        if(line.contains("==LINKS==")) {
          newIndex.append(line.replace("==LINKS==", links)
                  .replace("==DATASET==", dataset));
          newIndex.append("\n");
        } else if(line.contains("--TABLE--")) {
          String toInsert = "<tr typeof=\"dctype:Image\" about=\"#cloud\" property=\"dc:title\" content=\"LOD cloud diagram\">\n"
            + "<th property=\"dc:modified\" datatype=\"xsd:date\" content=\"" + date + "\">" + date + "</th>\n" 
            + "<td></td><td></td><td></td><td>\n"
            + "<a href=\"versions/" + date + "/lod-cloud.png\">png</a></td>\n" 
            + "<td></td>\n" 
            + "<td><a href=\"versions/" + date + "/lod-cloud.svg\">svg</a></td>\n"
            + "<td><a href=\"versions/" + date + "/lod-data.json\">json</a></td>\n" 
            + "<td></td><td class=\"dataset-count\">" + dataset + "</td></tr>\n";

          newTemplate.append(line);
          newTemplate.append("\n");
          newTemplate.append(toInsert);
          newTemplate.append("\n");
          newIndex.append(line);
          newIndex.append("\n");
        } else {
          newTemplate.append(line);
          newTemplate.append("\n");
          newIndex.append(line);
          newIndex.append("\n");
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

  private static byte[] readFile(File file) throws IOException {
    byte[] bytes = new byte[(int) file.length()];
    try(FileInputStream fis = new FileInputStream(file)) {
      fis.read(bytes);
    }
    return bytes;
  }

  private static String fileSha(String path) throws IOException {
    String url = "https://api.github.com/repos/lod-cloud/lod-cloud-site/contents/" + path;
    Map<String, Object> data = new ObjectMapper().readValue(new URL(url).openStream(), Map.class);
    return (String) data.get("sha");
  }

  public static void addFileToGitHub(String repo, File file, String path, String branch,
    String ghToken) throws IOException {
    System.err.println("Adding " + path + " to GitHub repo " + repo);
    String url = "https://api.github.com/repos/" + repo + "/contents/" + path;
    System.err.println(url);
    
    HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
    conn.setRequestMethod("PUT");
    conn.setRequestProperty("Authorization", "token " + ghToken);
    conn.setRequestProperty("Content-Type", "application/json");
    conn.setDoOutput(true);
    conn.setDoInput(true);
    
    try(PrintWriter out = new PrintWriter(conn.getOutputStream())) {
      out.println("{");
      out.println("\"message\" : \"Add file " + path + "\",");
      out.println("\"content\" : \"" + Base64.getEncoder().encodeToString(readFile(file)) + "\",");
      out.println("\"branch\" : \"" + branch + "\"");
      out.println("}");
    }
    if(conn.getResponseCode() != 201 && conn.getResponseCode() != 200) {
      BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getErrorStream()));
      String line;
            while((line = reader.readLine()) != null) {
        System.err.println(line);
      }
       throw new IOException("Error adding file " + path + " to GitHub repo " + repo + " : " + conn.getResponseCode() + " " + conn.getResponseMessage());
    }
  }


  public static void updateFileToGitHub(String repo, File file, String path, String branch,
    String ghToken, String sha) throws IOException {
    System.err.println("Updating " + path + " to GitHub repo " + repo);
    String url = "https://api.github.com/repos/" + repo + "/contents/" + path;
    HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
    conn.setRequestMethod("PUT");
    conn.setRequestProperty("Authorization", "token " + ghToken);
    conn.setRequestProperty("Content-Type", "application/json");
    conn.setDoOutput(true);
    try(PrintWriter out = new PrintWriter(conn.getOutputStream())) {
      out.println("{");
      out.println("\"message\" : \"Add file " + path + "\",");
      out.println("\"content\" : \"" + Base64.getEncoder().encodeToString(readFile(file)) + "\",");
      out.println("\"branch\" : \"" + branch + "\",");
      out.println("\"sha\" : \"" + sha + "\"");
      out.println("}");
    }
    if(conn.getResponseCode() != 201 && conn.getResponseCode() != 200) {
      BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getErrorStream()));
      String line;
            while((line = reader.readLine()) != null) {
        System.err.println(line);
      }
      throw new IOException("Error adding file " + path + " to GitHub repo " + repo + " : " + conn.getResponseCode() + " " + conn.getResponseMessage());
    }
  }

  public static void createBranch(String repo, String branch, String ghToken) throws IOException {
    System.err.println("Creating branch " + branch + " in GitHub repo " + repo);
    String urlHeads = "https://api.github.com/repos/" + repo + "/git/refs/heads";
    HttpURLConnection conn = (HttpURLConnection) new URL(urlHeads).openConnection();
    if(conn.getResponseCode() != 200) {
      throw new RuntimeException("Error getting branches from GitHub repo " + repo + " : " + conn.getResponseCode() + " " + conn.getResponseMessage());
    }
    String sha = null;
    List<Map<String, Object>> branches = new ObjectMapper().readValue(conn.getInputStream(), new TypeReference<List<Map<String, Object>>>(){});
    for(Map<String, Object> b : branches) {
      if(b.get("ref").equals("refs/heads/main")) {
        sha = (String)((Map<String, Object>)b.get("object")).get("sha");
      }
    }
    
    if(sha == null) {
      throw new RuntimeException("Could not find main branch in GitHub repo " + repo);
    }
    String url = "https://api.github.com/repos/" + repo + "/git/refs";
    HttpURLConnection conn2 = (HttpURLConnection) new URL(url).openConnection();
    conn2.setRequestMethod("POST");
    conn2.setRequestProperty("Authorization", "token " + ghToken);
    conn2.setRequestProperty("Content-Type", "application/json");
    conn2.setDoOutput(true);
    conn2.setDoInput(true);

    try(PrintWriter out = new PrintWriter(conn2.getOutputStream())) {
      out.println("{");
      out.println("\"ref\": \"refs/heads/" + branch + "\",");
      out.println("\"sha\": \"" + sha + "\"");
      out.println("}");

    }
    if(conn2.getResponseCode() != 201 && conn2.getResponseCode() != 200) {
      BufferedReader reader = new BufferedReader(new InputStreamReader(conn2.getErrorStream()));
      String line;
            while((line = reader.readLine()) != null) {
        System.err.println(line);
      }
      throw new IOException("Error creating branch " + branch + " to GitHub repo " + repo + " : " + conn2.getResponseCode() + " " + conn2.getResponseMessage());
    }
    // curl -X POST  -H "Authorization: token $GH_TOKEN" https://api.github.com/repos/jmccrae/scratch/git/refs -d '{"ref": "refs/heads/foo", "sha": "25e8b7d84875490e3fe55b5c0fe15f7692548532"}'/
  }

  public static void makePullRequest(String repo, String branch, String ghToken, String date) throws IOException {
    System.err.println("Creating pull request for branch " + branch + " in GitHub repo " + repo);
    String url = "https://api.github.com/repos/" + repo + "/pulls";
    HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
    conn.setRequestMethod("POST");
    conn.setRequestProperty("Authorization", "token " + ghToken);
    conn.setRequestProperty("Content-Type", "application/json");
    conn.setDoOutput(true);
    conn.setDoInput(true);

    try(PrintWriter out = new PrintWriter(conn.getOutputStream())) {
      out.println("{");
      out.println("\"title\": \"Update from LOD\",");
      out.println("\"base\": \"main\",");
      out.println("\"head\": \"" + branch + "\",");
      out.println("\"body\": \"This pull request will update the LOD cloud to " + date + "\\n\\n" +
        "The steps to deploy this after accepting this pull request are as follows:\\n" +
        "    cd lod-cloud-site\\n" +
                        "    git pull\\n" +
                        "    rm src/main/webapp/versions/latest\\n" +
                        "    ln -s " + date + " src/main/webapp/versions/latest\\n" +
                        "    git add src/main/webapp/versions/latest\\n" +
                        "    git commit -m \\\"Update symlink\\\"\\n" +
        "    git push\\n" +
        "    curl https://lod-cloud.net/extract/datasets > lod-data.json\\n" +
        "    mvn clean package\\n" +
        "    docker build -t nuig_uld/lod-cloud .\\n" +
        "    docker stop lod-cloud\\n" +
        "    docker rm lod-cloud\\n" +
        "   docker run -d --restart always -p 9001:8080 --network lod-cloud-net --name lod-cloud nuig_uld/lod-cloud\\n" + 
        "\"");
      out.println("}");
    }
    
    if(conn.getResponseCode() != 201 && conn.getResponseCode() != 200) {
      BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getErrorStream()));
      String line;
            while((line = reader.readLine()) != null) {
        System.err.println(line);
      }
      throw new RuntimeException("Error creating pull request for branch " + branch + " to GitHub repo " + repo + " : " + conn.getResponseCode() + " " + conn.getResponseMessage());
    }
  }

  public static Date getLatestDateFromGitHub(String repo) throws Exception {
    String url = "https://api.github.com/repos/" + repo + "/contents/src/main/webapp/versions";

    HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
    if(conn.getResponseCode() != 200) {
      throw new RuntimeException("Error getting date info from GitHub repo " + repo + " : " + conn.getResponseCode() + " " + conn.getResponseMessage());
    }
    Date date = null;
    List<Map<String, Object>> branches = new ObjectMapper().readValue(conn.getInputStream(), new TypeReference<List<Map<String, Object>>>(){});
    for(Map<String, Object> b : branches) {
      if(b.get("name").toString().matches("\\d{4}-\\d{2}-\\d{2}")) {
        System.err.println(b.get("name"));
        Date d = new SimpleDateFormat("YYYY-MM-dd").parse(b.get("name").toString());
        if(date == null || d.after(date)) {
          date = d;
        }
      }
    }
    return date;
  }
    

  public static void doCloudUpdate(String repo, String ghToken) throws Exception {
    String date = new SimpleDateFormat("YYYY-MM-dd").format(new Date());
    String branch = "lod-cloud-" + date;
    createBranch(repo, branch, ghToken);

    Map<String, Object> data = GetData.getData(false, new HashMap<String, String>(), 50,
        new GetData.Logger() {
          public void log(String dataset, String message) {
            System.out.println("[" + dataset + "] " + message);
          }
          public void logError(String dataset, Exception x) {
            x.printStackTrace();
          }
        });

    for(Map.Entry<String, Object> e : data.entrySet()) {
      if(e.getValue() instanceof Map) {
        Map<String, Object> m = (Map<String, Object>)e.getValue();
        if(m.get("keywords") instanceof String) {
          m.put("keywords", new ArrayList<>());
        }
      }
    }
    

    try(Writer out = new FileWriter("lod-data.json")) {
      new ObjectMapper().writeValue(out, data);
    }

    GenerateClouds.main(null);

    CountLinks cl = new CountLinks();
    cl.count("clouds/lod-cloud.svg");


    String indexSha = fileSha("src/main/webapp/index.html");
    String indexTmpSha = fileSha("src/main/webapp/index-template");

    updateIndex("" + cl.links, "" + cl.datasets, date);


    addFileToGitHub(repo, new File("clouds/cross-domain-lod.json"), "src/main/webapp/versions/" + date + "/cross-domain-lod.json", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/cross-domain-lod.png"), "src/main/webapp/versions/" + date + "/cross-domain-lod.png", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/cross-domain-lod.svg"), "src/main/webapp/versions/" + date + "/cross-domain-lod.svg", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/geography-lod.json"), "src/main/webapp/versions/" + date + "/geography-lod.json", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/geography-lod.png"), "src/main/webapp/versions/" + date + "/geography-lod.png", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/geography-lod.svg"), "src/main/webapp/versions/" + date + "/geography-lod.svg", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/government-lod.json"), "src/main/webapp/versions/" + date + "/government-lod.json", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/government-lod.png"), "src/main/webapp/versions/" + date + "/government-lod.png", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/government-lod.svg"), "src/main/webapp/versions/" + date + "/government-lod.svg", branch, ghToken);
    //addFileToGitHub(repo, new File("clouds/ipfs-lod.json"), "src/main/webapp/versions/" + date + "/ipfs-lod.json", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/life-sciences-lod.json"), "src/main/webapp/versions/" + date + "/life-sciences-lod.json", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/life-sciences-lod.png"), "src/main/webapp/versions/" + date + "/life-sciences-lod.png", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/life-sciences-lod.svg"), "src/main/webapp/versions/" + date + "/life-sciences-lod.svg", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/linguistic-lod.json"), "src/main/webapp/versions/" + date + "/linguistic-lod.json", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/linguistic-lod.png"), "src/main/webapp/versions/" + date + "/linguistic-lod.png", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/linguistic-lod.svg"), "src/main/webapp/versions/" + date + "/linguistic-lod.svg", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/lod-cloud.png"), "src/main/webapp/versions/" + date + "/lod-cloud.png", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/lod-cloud-settings.json"), "src/main/webapp/versions/" + date + "/lod-cloud-settings.json", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/lod-cloud.svg"), "src/main/webapp/versions/" + date + "/lod-cloud.svg", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/media-lod.json"), "src/main/webapp/versions/" + date + "/media-lod.json", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/media-lod.png"), "src/main/webapp/versions/" + date + "/media-lod.png", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/media-lod.svg"), "src/main/webapp/versions/" + date + "/media-lod.svg", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/publications-lod.json"), "src/main/webapp/versions/" + date + "/publications-lod.json", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/publications-lod.png"), "src/main/webapp/versions/" + date + "/publications-lod.png", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/publications-lod.svg"), "src/main/webapp/versions/" + date + "/publications-lod.svg", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/social-networking-lod.json"), "src/main/webapp/versions/" + date + "/social-networking-lod.json", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/social-networking-lod.png"), "src/main/webapp/versions/" + date + "/social-networking-lod.png", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/social-networking-lod.svg"), "src/main/webapp/versions/" + date + "/social-networking-lod.svg", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/user-generated-lod.json"), "src/main/webapp/versions/" + date + "/user-generated-lod.json", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/user-generated-lod.png"), "src/main/webapp/versions/" + date + "/user-generated-lod.png", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/user-generated-lod.svg"), "src/main/webapp/versions/" + date + "/user-generated-lod.svg", branch, ghToken);
    addFileToGitHub(repo, new File("clouds/lod-cloud-sm.jpg"),
        "src/main/webapp/" + date + "/lod-cloud-sm.jpg", branch, ghToken);

    addFileToGitHub(repo, new File("lod-data.json"), "src/main/webapp/versions/" + date + "/lod-data.json", branch, ghToken);

    updateFileToGitHub(repo, new File("index.html"), "src/main/webapp/index.html", branch, ghToken, indexSha);
    updateFileToGitHub(repo, new File("index-template"), "src/main/webapp/index-template", branch, ghToken, indexTmpSha);

    makePullRequest(repo, branch, ghToken, date);
  }

  @Override
  protected void doGet(HttpServletRequest request, HttpServletResponse response)
    throws ServletException, IOException {
    // The point here is that we can trigger cloud updates with
    //   curl http://localhost:8080/update-clouds
    String ipAddr = request.getRemoteAddr();
    if(!ipAddr.equals("localhost") && !ipAddr.equals("127.0.0.1")) {
      response.sendError(403, "Access denied");
    } else if(GH_TOKEN == null) {
      response.sendError(500, "GitHub token not loaded. This installation does not support generating new cloud images");
    } else {
      try {
        Date lastUpdate = getLatestDateFromGitHub("lod-cloud/lod-cloud-site");
        if(new Date().getTime() - lastUpdate.getTime() > 30 * 24 * 60 * 60 * 1000) {
          response.getWriter().println("Updating cloud images");
          new Thread(new Runnable() {
            public void run() {
              try {
                doCloudUpdate("lod-cloud/lod-cloud-site", GH_TOKEN);
              } catch(Exception x) {
                x.printStackTrace();
              }
            }
          }).start();
        } else {
          response.sendError(500, "Cloud images updated less than 30 days ago");
        }
      } catch(Exception x) {
        x.printStackTrace();
      }
    }
  }

  public static Date lastTriggeredUpdate = null;

  public static void triggerUpdate() {
    if(GH_TOKEN == null) {
      System.err.println("No GH_TOKEN, skipping update");
    }
    try {
      Date lastUpdate = getLatestDateFromGitHub("lod-cloud/lod-cloud-site");
      if(new Date().getTime() - lastUpdate.getTime() > 30 * 24 * 60 * 60 * 1000 &&
        (lastTriggeredUpdate == null ||
              new Date().getTime() - lastTriggeredUpdate.getTime() > 30 * 24 * 60 * 60 * 1000)) {
          lastTriggeredUpdate = new Date();
        new Thread(new Runnable() {
          public void run() {
            try {
              doCloudUpdate("lod-cloud/lod-cloud-site", GH_TOKEN);
            } catch(Exception x) {
              x.printStackTrace();
            }
          }
        }).start();
      }
    } catch(Exception x) {
      x.printStackTrace();
    }
  }

  public static void main(String[] args) throws Exception {
    if(args.length != 2) {
      System.err.println("Usage: mvn exec:java -Dexec.mainClass=\"org.insightcentre.lodcloud.UpdateClouds\" -Dexec.args=\"repo/name $GH_TOKEN\"");
      System.exit(-1);
    }
    doCloudUpdate(args[0], args[1]);
  }
}
