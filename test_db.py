from app.database.database import SessionLocal
from app.models.employee import Employee
from dotenv import load_dotenv
load_dotenv()

db = SessionLocal()
emps = db.query(Employee).all()
for e in emps:
    if e.role == 'TEAM LEADER' or e.is_team_leader:
        print(f"Name: {e.name}, Role: {e.role}, is_TL: {e.is_team_leader}, RM: {e.reporting_manager}")
