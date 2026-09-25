import requests

# 1. Login to get token
login_data = {"email": "admin@makemystay.com", "password": "password123"}
res = requests.post("http://127.0.0.1:8000/api/v1/auth/login", json=login_data)
if res.status_code != 200:
    print(f"Login failed: {res.status_code} {res.text}")
else:
    token = res.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Hit the properties endpoint
    res = requests.get("http://127.0.0.1:8000/api/v1/properties", headers=headers)
    print(f"Status: {res.status_code}")
    print(res.text[:1000])

