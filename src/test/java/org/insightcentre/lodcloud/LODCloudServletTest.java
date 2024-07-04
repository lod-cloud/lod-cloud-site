/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package org.insightcentre.lodcloud;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import static org.junit.Assert.*;
import org.insightcentre.lodcloud.GenerateClouds;

/**
 *
 * @author jmccrae
 */
public class LODCloudServletTest {
    
    public LODCloudServletTest() {
    }
    
    @BeforeClass
    public static void setUpClass() {
    }
    
    @AfterClass
    public static void tearDownClass() {
    }
    
    @Before
    public void setUp() {
    }
    
    @After
    public void tearDown() {
    }


    /**
     * Test of validate_json method, of class LODCloudServlet.
     */
    @Test
    public void testValidate_json() throws IOException {
        System.out.println("validate_json");
        Document doc = Document.parse("{\n" +
"  \"_id\" : \"wordnet-rdf\",\n" +
"  \"website\" : \"http://www.example.com/\",\n" +
"  \"domain\" : \"linguistics\",\n" +
"  \"doi\" : \"\",\n" +
"  \"triples\" : \"8903374\",\n" +
"  \"sparql\" : [],\n" +
"  \"links\" : [{\n" +
"      \"target\" : \"lemonuby\",\n" +
"      \"value\" : \"475503\"\n" +
"    }, {\n" +
"      \"target\" : \"lexvo\",\n" +
"      \"value\" : \"458907\"\n" +
"    }, {\n" +
"      \"target\" : \"verbnet\",\n" +
"      \"value\" : \"26353\"\n" +
"    }, {\n" +
"      \"target\" : \"w3c-wordnet\",\n" +
"      \"value\" : \"99927\"\n" +
"    }],\n" +
"  \"title\" : \"WordNet-RDF\",\n" +
"  \"image\" : \"\",\n" +
"  \"namespace\" : \"\",\n" +
"  \"other_download\" : [{\n" +
"      \"status\" : \"OK\",\n" +
"      \"media_type\" : \"application/octet-stream\",\n" +
"      \"access_url\" : \"http://wordnet-rdf.princeton.edu/wn31.nt.gz\",\n" +
"      \"description\" : \"The complete data dump\",\n" +
"      \"title\" : \"WordNet 3.1 RDF data dump\"\n" +
"    }],\n" +
"  \"owner\" : \"\",\n" +
"  \"identifier\" : \"wordnet-rdf\",\n" +
"  \"keywords\" : [\"lexicon\", \"linguistics\"],\n" +
"  \"contact_point\" : {\n" +
"    \"name\" : \"Christiane Fellbaum\",\n" +
"    \"email\" : \"fellbaum@princeton.edu\"\n" +
"  },\n" +
"  \"full_download\" : [],\n" +
"  \"example\" : [],\n" +
"  \"description\" : {\n" +
"    \"en\" : \"RDF version of WordNet from Princeton\"\n" +
"  }\n" +
"}");
        Document doc2 = Document.parse("{"
                + "\"this\": \"is a bad document\""
                + "}");
        LODCloudServlet instance = new LODCloudServlet();
        assertEquals(true, instance.validate_json(doc));
        assertEquals(false, instance.validate_json(doc2));
    }

    @Test
    public void testSvg2Jpg() {
        System.out.println("svg2jpeg");
        String svg = "clouds/lod-cloud.svg";
        String jpg = "clouds/lod-cloud-sm.jpg";
        int width = 2648;
        try {
            GenerateClouds.svg2jpeg(svg, jpg, width);
        } catch (Exception x) {
            fail(x.getMessage());
        }
        assertTrue(new java.io.File(jpg).exists());
    }
    
}
