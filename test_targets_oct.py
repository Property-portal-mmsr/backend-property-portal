import sys
sys.path.append("/Users/maheswaranm/backend-property-portal")
from app.database.database import SessionLocal
from app.models.employee_monthly_target import EmployeeMonthlyTarget
from app.models.employee import Employee

db = SessionLocal()

oct_targets = db.query(EmployeeMonthlyTarget).filter(
    EmployeeMonthlyTarget.month == "October",
    EmployeeMonthlyTarget.year == 2026,
    EmployeeMonthlyTarget.target > 0
).all()

print("October targets > 0:")
for t in oct_targets:
    emp = db.query(Employee).get(t.employee_id)
    print(f"Emp {emp.id}: {emp.name}, Target: {t.target}")
