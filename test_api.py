import urllib.request
import json

login_data = json.dumps({'email': 'admin@makemystay.com', 'password': 'password123'}).encode('utf-8')
req = urllib.request.Request('http://127.0.0.1:8000/api/v1/auth/login', data=login_data, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read())
        token = data.get('access_token')
        req2 = urllib.request.Request('http://127.0.0.1:8000/api/v1/properties', headers={'Authorization': f'Bearer {token}'})
        with urllib.request.urlopen(req2) as res2:
            props = json.loads(res2.read())
            print("Total properties returned:", len(props.get('items', [])))
except Exception as e:
    print("Error:", e)
