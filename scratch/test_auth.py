import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

try:
    # We will try to bypass auth by sending a dummy request to the health endpoint first
    req = urllib.request.Request('http://127.0.0.1:8000/api/v1/properties', headers={})
    with urllib.request.urlopen(req) as res:
        print(res.read().decode())
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code, e.read().decode())
