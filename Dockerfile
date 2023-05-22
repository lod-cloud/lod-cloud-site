FROM jetty:jre8-alpine
MAINTAINER john:mccr.ae

EXPOSE 8080

ADD target/lod-cloud-crud-java-0.1-SNAPSHOT.war /var/lib/jetty/webapps/ROOT.war
ADD mongodb.txt /var/lib/jetty/mongodb.txt
ADD oauth2 /var/lib/jetty/oauth2
