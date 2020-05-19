package org.insightcentre.lodcloud;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.util.HashMap;
import javax.servlet.ServletException;
import javax.servlet.http.Cookie;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

/**
 *
 * @author John McCrae
 */
public class Authorize extends HttpServlet {
    private static final HashMap<String, User> users = new HashMap<>();
    public static String CLIENT_ID;
    public static String CLIENT_SECRET;
    public static String URL_CALLBACK;

    static {
        try(final BufferedReader in = new BufferedReader(new FileReader("oauth2"))) {
            CLIENT_ID = in.readLine();
            CLIENT_SECRET = in.readLine();
            URL_CALLBACK = in.readLine();
        } catch(IOException x) {
            x.printStackTrace();
        }
    }
    
    public static void addUser(HttpServletResponse resp, String accessToken, User user) {
        users.put(accessToken, user);
        //System.err.println("user: " + accessToken + " -> " + user);
        Cookie accessTokenCookie = new Cookie("access_token", accessToken);
        accessTokenCookie.setMaxAge(60*60*24*7);
        resp.addCookie(accessTokenCookie);
    }
    
    public static User getUser(HttpServletRequest req) {
        Cookie[] cookies = req.getCookies();
        String accessToken = null;
        if(cookies != null) {
            for(Cookie cookie : cookies) {
                if(cookie.getName().equals("access_token")) {
                    accessToken = cookie.getValue();
                }
            }
        }
        if(accessToken != null && users.containsKey(accessToken)) {
            return users.get(accessToken);
        } else if(new File("skip_auth").exists()) {
            return new User("test", "test@test.com", "Test", "");
        } else {
            return null;
        }
    }
   
    public static boolean isLoggedIn(HttpServletRequest req) {
        return getUser(req) != null;
    }
    
    public static boolean removeUser(HttpServletRequest req) {
        Cookie[] cookies = req.getCookies();
        String accessToken = null;
        for(Cookie cookie : cookies) {
            if(cookie.getName().equals("access_token")) {
                accessToken = cookie.getValue();
            }
        }
        if(accessToken != null) {
            return users.remove(accessToken) != null;
        } else {
            return false;
        }
        
    }
    
    public static void redirectToAuthorize(HttpServletResponse resp, String finalLocation) throws IOException {
        resp.sendRedirect("/authorize" + (finalLocation != null ? "?target=" + finalLocation : ""));
    }
    
    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        final String state = req.getParameter("target") == null ? "/" : req.getParameter("target");
        

        // redirect to google for authorization
        String oauthUrl = 
        "https://accounts.google.com/o/oauth2/auth?client_id=" + CLIENT_ID 
         + "&response_type=code" + "&scope=openid%20email" 
         + "&redirect_uri=" + URL_CALLBACK
         + "&state=" + state + "&access_type=offline" 
         + "&approval_prompt=force"; 

        //resp.sendRedirect(oauthUrl.toString());
        resp.setContentType("text/html;charset=UTF-8");
        Templates.XTemplate template = new Templates.XTemplate("login", getServletContext());
        template.addReplacement("\\{\\{href\\}\\}", oauthUrl);
        Templates.apply(resp.getWriter(), Authorize.isLoggedIn(req), getServletContext(), template);
    }
}
