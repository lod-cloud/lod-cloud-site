import json
import sys

#data = json.load(open("/home/johmcc/lod-cloud-crud/angular-client/src/assets/files/lod-data.json"))
#data =json.load(open("/var/lib/tomcat8/webapps/lod-cloud/lod-data.json"))
#data = json.load(open("src/main/webapp/lod-data.json"))
data = json.load(open(sys.argv[1]))

for _,d in data.items():
	d["_id"] = d["identifier"]
	print(json.dumps(d))
