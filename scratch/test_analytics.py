import sys, time
sys.path.append('.')
from app.database.database import SessionLocal
from app.services.analytics_service import AnalyticsService

db = SessionLocal()
res = AnalyticsService.get_dashboard(db=db, month_str="2026-09", rm_name=None)
print("Team Leaders Found:", [t.team_leader_name for t in res.team_leader_tracker])
for t in res.team_leader_tracker:
    print(f"- {t.team_leader_name}: {[m.name for m in t.team_members]}")
