from dotenv import load_dotenv
load_dotenv()
from app.database.database import SessionLocal
from app.models.employee import Employee

db = SessionLocal()
emps = db.query(Employee).all()
print("Total employees:", len(emps))
for e in emps:
    print(f"{e.name}: role={e.role}, is_team_leader={e.is_team_leader}, reporting_manager={e.reporting_manager}")
