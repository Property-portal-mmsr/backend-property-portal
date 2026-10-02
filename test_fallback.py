import sys
sys.path.append("/Users/maheswaranm/backend-property-portal")
from app.database.database import SessionLocal
from app.models.employee import Employee
from app.services.analytics_service import build_dashboard

db = SessionLocal()

# Find an active employee and set their monthly_target to 50000 temporarily
emp = db.query(Employee).filter(Employee.status.ilike("ACTIVE")).first()
old_target = emp.monthly_target
emp.monthly_target = 50000
db.commit()

print(f"Set {emp.name}'s monthly_target to 50000")

dash = build_dashboard(db, month="2026-10")
print("Oct API overall_target:", dash.kpis.overall_target)

# Restore
emp.monthly_target = old_target
db.commit()
