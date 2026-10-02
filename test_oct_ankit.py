import sys
sys.path.append("/Users/maheswaranm/backend-property-portal")
from app.database.database import SessionLocal
from app.services.analytics_service import build_dashboard

db = SessionLocal()

dash_oct = build_dashboard(db, month="2026-10")

print("October Performance Table RMs:")
for rm in dash_oct.performance_table:
    print(rm.rm_name, rm.monthly_target)

print("\nTeam Members for Sanjota:")
for t in dash_oct.team_leader_tracker:
    if t.team_leader_name == "Sanjota":
        for m in t.team_members:
            print(m.name, m.revenue, m.target)
