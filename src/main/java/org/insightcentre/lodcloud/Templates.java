package org.insightcentre.lodcloud;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.HashMap;
import java.util.Map;
import javax.servlet.ServletContext;

/**
 * The main templates for the application
 *
 * @author John McCrae
 */
public class Templates {

    private static String[] template;

    private static String[] template(ServletContext context) {
        if (template == null) {
            final File f = new File(context.getRealPath("/WEB-INF/templates/index.html"));
            if (!f.exists()) {
                throw new RuntimeException("Could not load index template");
            }
            StringBuilder sb = new StringBuilder();
            try (BufferedReader in = new BufferedReader(new FileReader(f))) {
                String s;
                while ((s = in.readLine()) != null) {
                    sb.append(s).append("\n");
                }
            } catch (IOException x) {
                throw new RuntimeException(x);
            }
            int i3 = sb.indexOf("{{logout1}}");
            int i4 = sb.indexOf("{{logout2}}");
            int i1 = sb.indexOf("{{body}}");
            int i2 = sb.indexOf("{{scriptFooter}}");
            template = new String[]{
                sb.substring(0, i3),
                sb.substring(i3 + 11, i4),
                sb.substring(i4 + 11, i1),
                sb.substring(i1 + 8, i2),
                sb.substring(i2 + 16, sb.length())
            };
        }
        return template;
    }
    public static void apply(PrintWriter out, boolean loggedin, ServletContext context, TemplateSection body) {
        String template[] = template(context);
        out.print(template[0]);
        if(loggedin) out.print(template[1]);
        out.print(template[2]);
        body.apply(out);
        out.print(template[3]);
        out.print(template[4]);
    }
    
    public static void apply(PrintWriter out, boolean loggedin, ServletContext context, TemplateSection body, TemplateSection scriptFooter) {
        String template[] = template(context);
        out.print(template[0]);
        if(loggedin) out.print(template[1]);
        out.print(template[2]);
        body.apply(out);
        out.print(template[3]);
        scriptFooter.apply(out);
        out.print(template[4]);
    }

    public static void apply(PrintWriter out, boolean loggedin, ServletContext context,
            TemplateSection body, TemplateSection scriptFooter1,
            TemplateSection scriptFooter2) {
        String template[] = template(context);
        out.print(template[0]);
        if(loggedin) out.print(template[1]);
        out.print(template[2]);
        body.apply(out);
        out.print(template[3]);
        scriptFooter1.apply(out);
        out.println();
        scriptFooter2.apply(out);
        out.print(template[4]);
    }

    public static interface TemplateSection {

        public void apply(PrintWriter out);
    }

    public static class XTemplate implements TemplateSection {

        private final String name;
        private final ServletContext context;
        private final HashMap<String,String> replacements = new HashMap<>();

        public XTemplate(String name, ServletContext context) {
            this.name = name;
            this.context = context;
        }
        
        public void addReplacement(String match, String repl)  {
            replacements.put(match, repl);
        }

        @Override
        public void apply(PrintWriter out) {
            final File f = new File(context.getRealPath("/WEB-INF/templates/" + name + ".html"));
            if (f.exists()) {
                try (final BufferedReader in = new BufferedReader(new FileReader(f))) {
                    String s;
                    while ((s = in.readLine()) != null) {
                        for(Map.Entry<String,String> e : replacements.entrySet()) {
                            s = s.replaceAll(e.getKey(), e.getValue());
                        }
                        out.println(s);
                    }
                } catch (IOException x) {
                    x.printStackTrace();
                    out.println(x.getMessage());
                }
            } else {
                out.println("Could not find template: " + name);
            }
        }
    }

    public static class JSTemplate implements TemplateSection {

        private final String name;
        private final ServletContext context;

        public JSTemplate(String name, ServletContext context) {
            this.name = name;
            this.context = context;
        }

        @Override
        public void apply(PrintWriter out) {
            final File f = new File(context.getRealPath("/WEB-INF/templates/" + name + ".js"));
            if (f.exists()) {
                try (final BufferedReader in = new BufferedReader(new FileReader(f))) {
                    String s;
                    while ((s = in.readLine()) != null) {
                        out.println(s);
                    }
                } catch (IOException x) {
                    x.printStackTrace();
                    out.println(x.getMessage());
                }
            } else {
                out.println("Could not find template: " + name);
            }
        }
    }

    public static class Data implements TemplateSection {

        private final Document doc;
        private final String name;

        public Data(Document doc, String name) {
            this.doc = doc;
            this.name = name;
        }

        @Override
        public void apply(PrintWriter out) {
            if (name != null) {
                out.print("function data() { return {" + name + ":");
            } else {
                out.print("function data() { return ");
            }
            out.print(doc.toJson());
            if (name != null) {
                out.print("}}");
            } else {
                out.print("}");
            }
        }

    }
}
