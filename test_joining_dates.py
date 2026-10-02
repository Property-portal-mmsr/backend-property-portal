import sys
sys.path.append("/Users/maheswaranm/backend-property-portal")
from app.database.database import SessionLocal
from app.models.employee import Employee
from app.models.employee_monthly_target import EmployeeMonthlyTarget

db = SessionLocal()

print("Employee joining dates:")
employees = db.query(Employee).filter(Employee.name.in_(["Ankit Prajapati", "Pavan Tavarageri"])).all()
for e in employees:
    print(f"{e.name}: {e.joining_date}")

other_employees = db.query(Employee).filter(Employee.joining_date.isnot(None)).limit(5).all()
print("\nOther employees:")
for e in other_employees:
    print(f"{e.name}: {e.joining_date}")
