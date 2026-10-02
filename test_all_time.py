import sys
sys.path.append("/Users/maheswaranm/backend-property-portal")
from app.database.database import SessionLocal
from app.services.analytics_service import build_dashboard

db = SessionLocal()

print("Dashboard overall_target with All Time (month=None):")
dash = build_dashboard(db, month=None)
print("All Time API overall_target:", dash.kpis.overall_target)

