import urllib.request
import json
try:
    req = urllib.request.Request("http://127.0.0.1:8000/api/v1/analytics/dashboard")
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print("Team Leaders Found:")
        tracker = data.get("team_leader_tracker", [])
        if not tracker:
            print("NONE!")
        for t in tracker:
            print(t.get("team_leader_name"))
except Exception as e:
    print("Error:", e)
