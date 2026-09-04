import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Assuming SQLite or whatever is used in backend
from app.database.database import engine
from app.models.employee import Employee
from app.models.employee_monthly_target import EmployeeMonthlyTarget

Session = sessionmaker(bind=engine)
db = Session()

emps = db.query(Employee).all()
for e in emps:
    print(f"ID:{e.id} Name:{e.name} Status:{e.status} RM:{e.reporting_manager}")
