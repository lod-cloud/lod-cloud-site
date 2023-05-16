package org.insightcentre.lodcloud;

import java.io.BufferedReader;
import java.io.FileReader;

public class CountLinks {
  public int links = 0;
  public int datasets = 0;

  public void count(String svgFile) throws Exception {
    links = 0;
    datasets = 0;
    BufferedReader br = new BufferedReader(new FileReader(svgFile));

    String line;
    while((line = br.readLine()) != null) {
      if(line.contains("<line")) {
        links++;
      }
      if(line.contains("<circle")) {
        datasets++;
      }
    }
  }
}
