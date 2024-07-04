# LOD Cloud Java

## Running


    mvn install jetty:run
	
## Updating

**IMPORTANT:** Always pull `lod-data.json` from live site

    curl https://lod-cloud.net/extract/datasets > lod-data.json
    mvn clean package
    docker build -t nuig_uld/lod-cloud .
    docker stop lod-cloud
    docker rm lod-cloud
    docker run -d --restart always -p 9001:8080 --network lod-cloud-net --name lod-cloud nuig_uld/lod-cloud
