import os
import sys
from app.db.session import SessionLocal
from app.services.analytics_service import build_dashboard
db = SessionLocal()
try:
    resp = build_dashboard(db, None, None, None, None)
    print("Num trackers:", len(resp.team_leader_tracker))
    for t in resp.team_leader_tracker:
        print(t.team_leader_name, t.team_size)
finally:
    db.close()
