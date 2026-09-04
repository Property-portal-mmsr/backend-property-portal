import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

from app.database.database import SessionLocal
from app.models.employee import Employee
db = SessionLocal()
emps = db.query(Employee).all()
print("First emp target:", getattr(emps[0], 'monthly_target'))
