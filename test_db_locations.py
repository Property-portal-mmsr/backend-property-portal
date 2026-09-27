import urllib.request
import json
try:
    req = urllib.request.Request("http://127.0.0.1:8000/api/v1/properties/locations")
    with urllib.request.urlopen(req) as response:
        locations = json.loads(response.read().decode())
        print(locations)
except Exception as e:
    print(e)
