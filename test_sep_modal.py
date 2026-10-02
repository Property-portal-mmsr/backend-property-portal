import sys
sys.path.append("/Users/maheswaranm/backend-property-portal")
from app.database.database import SessionLocal
from app.services.analytics_service import build_dashboard

db = SessionLocal()

print("Fetching dash for September...")
dash_sep = build_dashboard(db, month="2026-09")
for t in dash_sep.team_leader_tracker:
    if "Sanjota" in t.team_leader_name:
        print("Team Sanjota Members in Sep:")
        for m in t.team_members:
            print(f"- {m.name}")
