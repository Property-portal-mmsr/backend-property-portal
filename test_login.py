import urllib.request
import json
import urllib.error

data = json.dumps({"email": "admin@makemystay.ai", "password": "password"}).encode('utf-8')
req = urllib.request.Request("http://127.0.0.1:8000/api/v1/auth/login", data=data, headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req) as res:
        print(res.read().decode())
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.code} {e.reason} - {e.read().decode()}")
