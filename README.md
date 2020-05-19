# LOD Cloud Java

## Running


    mvn install jetty:run

	

## Loading Mongo

    wget https://lod-cloud.net/lod-data.json
    python for-mongo.py lod-data.json > lod-data-mongo.json
    mongoimport --collection datasets --db mern-dataset-app --drop lod-data-mongo.json
    rm lod-data-mongo.json
