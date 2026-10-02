import sys
sys.path.append("/Users/maheswaranm/backend-property-portal")
from app.database.database import SessionLocal
from app.models.employee import Employee

db = SessionLocal()

print("All Ankits:")
employees = db.query(Employee).filter(Employee.name.ilike("%Ankit%")).all()
for e in employees:
    print(f"ID: {e.id}, Name: {e.name}, Joining: {e.joining_date}, Status: {e.status}")

print("All Pavans:")
employees = db.query(Employee).filter(Employee.name.ilike("%Pavan%")).all()
for e in employees:
    print(f"ID: {e.id}, Name: {e.name}, Joining: {e.joining_date}, Status: {e.status}")
