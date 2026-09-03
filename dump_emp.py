from app.database import SessionLocal
from app.models.employee import Employee
db = SessionLocal()
emps = db.query(Employee).all()
for e in emps:
    print(e.name, e.reporting_manager)
db.close()
