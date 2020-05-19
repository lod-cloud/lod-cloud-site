package org.insightcentre.lodcloud;

import java.util.Date;

/**
 *
 * @author jmccrae
 */
public class User {
    public final String id;
    public final String emailAddress;
    public final String name;
    public final String picture;
    public final Date lastLogin;

    public User(String id, String emailAddress, String name, String picture) {
        this.id = id;
        this.emailAddress = emailAddress;
        this.name = name;
        this.picture = picture;
        this.lastLogin = new Date();
    }

    @Override
    public String toString() {
        return "User{" + "id=" + id + ", emailAddress=" + emailAddress + ", name=" + name + ", picture=" + picture + ", lastLogin=" + lastLogin + '}';
    }
    
}
