import time
import httpx

start = time.time()
try:
    response = httpx.get("http://127.0.0.1:8000/api/v1/properties", timeout=60.0)
    end = time.time()
    print(f"Status: {response.status_code}")
    print(f"Time taken: {end - start:.2f} seconds")
    print(f"Body length: {len(response.text)}")
except Exception as e:
    print(f"Error: {e}")
