import sys
sys.path.append('.')
from app.database.database import SessionLocal
from app.models.employee import Employee
from app.core.security import verify_password
import json

db = SessionLocal()
emp = db.query(Employee).filter(Employee.email == 'admin@makemystay.com').first()
if emp:
    print(f"Admin found in DB: {emp.email}")
    # Just print all properties to see how many there are!
    from app.models.property import Property
    props = db.query(Property).count()
    print("Total Properties:", props)
else:
    print("Admin NOT found!")
