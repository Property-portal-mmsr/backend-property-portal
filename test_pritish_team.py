import sys
sys.path.append("/Users/maheswaranm/backend-property-portal")
from app.database.database import SessionLocal
from app.models.employee import Employee
from app.models.employee_monthly_target import EmployeeMonthlyTarget
from app.models.team import Team, TeamMember

db = SessionLocal()

pritish = db.query(Employee).filter(Employee.name == "Pritish Kumar Jena").first()
if pritish:
    print(f"Pritish Employee ID: {pritish.id}, RM: {pritish.reporting_manager}")
    memberships = db.query(TeamMember).filter(TeamMember.employee_id == pritish.id).all()
    if memberships:
        for m in memberships:
            team = db.query(Team).filter(Team.id == m.team_id).first()
            print(f"Member of team: {team.name if team else m.team_id} (from {m.start_date} to {m.end_date})")
    else:
        print("Pritish has no team memberships in the team_members table.")
        
sanjota_team = db.query(Team).filter(Team.name.ilike("%Sanjota%")).first()
if sanjota_team:
    print(f"Sanjota Team ID: {sanjota_team.id}")
else:
    print("Sanjota team not found.")
