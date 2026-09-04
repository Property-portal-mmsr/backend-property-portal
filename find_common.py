from app.database.database import SessionLocal
from app.models.employee import Employee
db = SessionLocal()
names = ["Likitha", "Lukmanul Hateem M A", "Kesava", "Pratima", "Kalyan Kumar Reddy"]
for name in names:
    e = db.query(Employee).filter(Employee.name == name).first()
    if e:
        print(f"{e.name} | Dept: {e.department} | RM: {e.reporting_manager} | Role: {e.role} | Desig: {e.designation} | Status: {e.status}")
