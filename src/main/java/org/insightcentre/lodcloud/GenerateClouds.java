package org.insightcentre.lodcloud;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;

public class GenerateClouds {

  public static void generateCloud(int c, String jsonFile, String data, String target) throws Exception {
    if(!new File("lod-cloud-draw").exists()) {
      exportResource("lod-cloud-draw"); 
      new File("lod-cloud-draw").setExecutable(true);
    }
    final ProcessBuilder proc;
    if(c > 0) { 
      proc = new ProcessBuilder(new String[] { new File("lod-cloud-draw").getAbsolutePath(),
          "-c", Integer.toString(c), 
          "--settings=" + jsonFile, "-i", "5000", "--ident=neighbour",
          data, target }).inheritIO();
    } else {
      proc = new ProcessBuilder(new String[] { new File("lod-cloud-draw").getAbsolutePath(),
          "--settings=" + jsonFile, "-i", "5000", "--ident=neighbour",
          data, target }).inheritIO();
    }

    for(int i = 0; i < MAX_TRIES; i++) {
      try {
        Process p = proc.start();
        
          int exit = p.waitFor();
          if(exit == 0) {
            break;
        }
      } catch(Exception x) {
        x.printStackTrace();
      }
    }
  }

  private static int MAX_TRIES = 5;

  public static void main(String[] args) throws Exception {

    new File("clouds").mkdirs();

    exportResource("clouds/cross-domain-lod.json");
    generateCloud(350, "clouds/cross-domain-lod.json", "lod-data.json", "clouds/cross-domain-lod.svg");

    exportResource("clouds/cross-domain-lod.json");
    generateCloud(300, "clouds/geography-lod.json", "lod-data.json", "clouds/geography-lod.svg");

    exportResource("clouds/government-lod.json");
    generateCloud(400, "clouds/government-lod.json", "lod-data.json", "clouds/government-lod.svg");

    exportResource("clouds/life-sciences-lod.json");
    generateCloud(600, "clouds/life-sciences-lod.json", "lod-data.json", "clouds/life-sciences-lod.svg");

    exportResource("clouds/linguistic-lod.json");
    generateCloud(500, "clouds/linguistic-lod.json", "lod-data.json", "clouds/linguistic-lod.svg");

    exportResource("clouds/media-lod.json");
    generateCloud(300, "clouds/media-lod.json", "lod-data.json", "clouds/media-lod.svg");

    exportResource("clouds/publications-lod.json");
    generateCloud(400, "clouds/publications-lod.json", "lod-data.json", "clouds/publications-lod.svg");

    exportResource("clouds/social-networking-lod.json");
    generateCloud(400, "clouds/social-networking-lod.json", "lod-data.json", "clouds/social-networking-lod.svg");

    exportResource("clouds/user-generated-lod.json");
    generateCloud(300, "clouds/user-generated-lod.json", "lod-data.json", "clouds/user-generated-lod.svg");

    exportResource("clouds/lod-cloud-settings.json");
    generateCloud(-1, "clouds/lod-cloud-settings.json", "lod-data.json", "clouds/lod-cloud.svg");

    //exportResource("clouds/ipfs-lod.json");
    //generateCloud(350, "clouds/ipfs-cloud-settings.json", "ipfs-lod.json", "clouds/ipfs-lod.svg");
  }

  /**
     * Export a resource embedded into a Jar file to the local file path.
     *
     * From: https://stackoverflow.com/questions/10308221/how-to-copy-file-inside-jar-to-outside-the-jar 
     * @param resourceName ie.: "/SmartLibrary.dll"
     * @return The path to the exported resource
     * @throws Exception
     */
    static public void exportResource(String resourceName) throws Exception {
        InputStream stream = null;
        OutputStream resStreamOut = null;
        String jarFolder;
        try {
            stream = GenerateClouds.class.getResourceAsStream("/" + resourceName);//note that each / is a directory down in the "jar tree" been the jar the root of the tree
            if(stream == null) {
                throw new Exception("Cannot get resource \"" + resourceName + "\" from Jar file.");
            }

            int readBytes;
            byte[] buffer = new byte[4096];
            resStreamOut = new FileOutputStream(resourceName);
            while ((readBytes = stream.read(buffer)) > 0) {
                resStreamOut.write(buffer, 0, readBytes);
            }
        } catch (Exception ex) {
            throw ex;
        } finally {
            if(stream != null) stream.close();
            if(resStreamOut != null) resStreamOut.close();
        }
    } 
}
