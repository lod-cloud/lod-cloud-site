FROM jetty:9-jre17-alpine
MAINTAINER john:mccr.ae

EXPOSE 8080

USER root

RUN apk add msttcorefonts-installer fontconfig && \
    update-ms-fonts && \
    fc-cache -f

ADD target/lod-cloud-crud-java-0.1-SNAPSHOT.war /var/lib/jetty/webapps/ROOT.war
ADD lod-data.json /var/lib/jetty/lod-data.json
ADD oauth2 /var/lib/jetty/oauth2
ADD gh-token /var/lib/jetty/gh-token
