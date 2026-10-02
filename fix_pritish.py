import sys
sys.path.append("/Users/maheswaranm/backend-property-portal")
from app.database.database import SessionLocal
from app.models.employee import Employee
from app.models.employee_monthly_target import EmployeeMonthlyTarget
from app.models.team import Team, TeamMember

db = SessionLocal()

pritish = db.query(Employee).filter(Employee.name == "Pritish Kumar Jena").first()
if pritish:
    memberships = db.query(TeamMember).filter(TeamMember.employee_id == pritish.id).all()
    for m in memberships:
        team = db.query(Team).filter(Team.id == m.team_id).first()
        if team and team.name == "Team Sanjota":
            print(f"Updating Pritish end_date for {team.name} from {m.end_date} to None")
            m.end_date = None
    db.commit()
    print("Done")
