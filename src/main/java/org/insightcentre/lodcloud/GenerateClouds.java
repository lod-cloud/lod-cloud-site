package org.insightcentre.lodcloud;

import java.awt.Color;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Paths;
import org.apache.batik.transcoder.TranscoderInput;
import org.apache.batik.transcoder.TranscoderOutput;
import org.apache.batik.transcoder.image.PNGTranscoder;
import org.apache.batik.transcoder.image.ImageTranscoder;

public class GenerateClouds {

  public static void generateCloud(int c, String jsonFile, String data, String target) throws Exception {
    if(!new File("lod-cloud-draw").exists()) {
      exportResource("lod-cloud-draw"); 
    }
    new File("lod-cloud-draw").setExecutable(true);
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

  public static void svg2png(String svgFile, String pngFile, float width) throws Exception {
    String svgURI = Paths.get(svgFile).toUri().toURL().toString();
    TranscoderInput inputSvgImage = new TranscoderInput(svgURI);        
    OutputStream pngOstream = new FileOutputStream(pngFile);
    TranscoderOutput outputPngImage = new TranscoderOutput(pngOstream);              
    PNGTranscoder transcoder = new PNGTranscoder();
    transcoder.addTranscodingHint(ImageTranscoder.KEY_BACKGROUND_COLOR, Color.WHITE);
    transcoder.addTranscodingHint(PNGTranscoder.KEY_WIDTH, (Float)width);
    transcoder.transcode(inputSvgImage, outputPngImage);
    pngOstream.flush();
    pngOstream.close();   
  }

  private static int MAX_TRIES = 5;

  public static void main(String[] args) throws Exception {

    new File("clouds").mkdirs();

    exportResource("clouds/cross-domain-lod.json");
    generateCloud(350, "clouds/cross-domain-lod.json", "lod-data.json", "clouds/cross-domain-lod.svg");
    svg2png("clouds/cross-domain-lod.svg", "clouds/cross-domain-lod.png", 1875);

    exportResource("clouds/cross-domain-lod.json");
    generateCloud(300, "clouds/geography-lod.json", "lod-data.json", "clouds/geography-lod.svg");
    svg2png("clouds/geography-lod.svg", "clouds/geography-lod.png", 1875);

    exportResource("clouds/government-lod.json");
    generateCloud(400, "clouds/government-lod.json", "lod-data.json", "clouds/government-lod.svg");
    svg2png("clouds/government-lod.svg", "clouds/government-lod.png", 2606);

    exportResource("clouds/life-sciences-lod.json");
    generateCloud(600, "clouds/life-sciences-lod.json", "lod-data.json", "clouds/life-sciences-lod.svg");
    svg2png("clouds/life-sciences-lod.svg", "clouds/life-sciences-lod.png", 3913);

    exportResource("clouds/linguistic-lod.json");
    generateCloud(500, "clouds/linguistic-lod.json", "lod-data.json", "clouds/linguistic-lod.svg");
    svg2png("clouds/linguistic-lod.svg", "clouds/linguistic-lod.png", 3244);

    exportResource("clouds/media-lod.json");
    generateCloud(300, "clouds/media-lod.json", "lod-data.json", "clouds/media-lod.svg");
    svg2png("clouds/media-lod.svg", "clouds/media-lod.png", 1875);

    exportResource("clouds/publications-lod.json");
    generateCloud(400, "clouds/publications-lod.json", "lod-data.json", "clouds/publications-lod.svg");
    svg2png("clouds/publications-lod.svg", "clouds/publications-lod.png", 2581);

    exportResource("clouds/social-networking-lod.json");
    generateCloud(400, "clouds/social-networking-lod.json", "lod-data.json", "clouds/social-networking-lod.svg");
    svg2png("clouds/social-networking-lod.svg", "clouds/social-networking-lod.png", 2500);

    exportResource("clouds/user-generated-lod.json");
    generateCloud(300, "clouds/user-generated-lod.json", "lod-data.json", "clouds/user-generated-lod.svg");
    svg2png("clouds/user-generated-lod.svg", "clouds/user-generated-lod.png", 1875);

    exportResource("clouds/lod-cloud-settings.json");
    generateCloud(-1, "clouds/lod-cloud-settings.json", "lod-data.json", "clouds/lod-cloud.svg");
    svg2png("clouds/lod-cloud.svg", "clouds/lod-cloud.png", 6619);
    svg2png("clouds/lod-cloud.svg", "clouds/lod-cloud-sm.png", 2648);

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
            File out = new File(resourceName);
            resStreamOut = new FileOutputStream(out.getAbsolutePath());
            while ((readBytes = stream.read(buffer)) > 0) {
                resStreamOut.write(buffer, 0, readBytes);
            }
            System.err.println("Exported resource: " + resourceName + " to " + out.getAbsolutePath() + " " + out.length() + " bytes");
        } catch (Exception ex) {
            throw ex;
        } finally {
            if(stream != null) stream.close();
            if(resStreamOut != null) resStreamOut.close();
        }
    } 
}
