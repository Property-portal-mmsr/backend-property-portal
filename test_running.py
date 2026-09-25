import urllib.request
import json
try:
    req = urllib.request.Request('http://127.0.0.1:8000/api/v1/properties', headers={'Authorization': 'Bearer DUMMY'})
    with urllib.request.urlopen(req) as res:
        pass
except urllib.error.HTTPError as e:
    print(e.read().decode())
