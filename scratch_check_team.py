from app.database.database import SessionLocal
from app.models.team import Team, TeamMember
from app.models.employee import Employee

db = SessionLocal()

print("TEAMS:")
teams = db.query(Team).all()
for t in teams:
    leader_name = "Unknown"
    if t.leader_id:
        leader = db.query(Employee).filter(Employee.id == t.leader_id).first()
        if leader:
            leader_name = leader.name
    print(f"ID={t.id}, Name={t.name}, Leader={leader_name}, Active={t.is_active}, From={t.active_from}, Until={t.active_until}")

print("\nTEAM MEMBERS:")
members = db.query(TeamMember).all()
for m in members:
    emp = db.query(Employee).filter(Employee.id == m.employee_id).first()
    team = db.query(Team).filter(Team.id == m.team_id).first()
    team_name = team.name if team else "Unknown"
    emp_name = emp.name if emp else "Unknown"
    print(f"ID={m.id}, Team={team_name}, Emp={emp_name}, Start={m.start_date}, End={m.end_date}")
