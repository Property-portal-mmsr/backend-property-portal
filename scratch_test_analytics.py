import sys, os
sys.path.append(os.getcwd())
from app.database.database import SessionLocal
from app.services.analytics_service import build_dashboard

db = SessionLocal()
dashboard = build_dashboard(db, month="2026-08") # The UI screenshot shows August 2026 is selected
print(dashboard.model_dump_json(indent=2))
