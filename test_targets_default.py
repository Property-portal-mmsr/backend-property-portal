import sys
sys.path.append("/Users/maheswaranm/backend-property-portal")
from app.database.database import SessionLocal
from app.models.employee import Employee
from app.services.analytics_service import build_dashboard
db = SessionLocal()

active_employees = db.query(Employee).filter(Employee.status.ilike("ACTIVE")).all()
print(f"Active employees: {len(active_employees)}")
print("Default monthly targets:")
for e in active_employees:
    if e.monthly_target:
        print(f"Emp {e.id} ({e.name}): {e.monthly_target}")
