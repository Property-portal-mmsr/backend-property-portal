"""
Seed teams and team_members tables from existing employee data.

This script:
1. Creates the teams and team_members tables if they don't exist.
2. Reads is_team_leader + reporting_manager from employees to build teams.
3. Populates active_from dates based on your current team structure.

Usage:
    python seed_teams.py
"""

import sys
import os
from datetime import date

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.database import SessionLocal, engine, Base
from app.models.employee import Employee
from app.models.employee_monthly_target import EmployeeMonthlyTarget
from app.models.team import Team, TeamMember


def _normalize(name: str) -> str:
    return " ".join(name.lower().split())


def seed_teams():
    print("Connecting to database...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Fetch all active employees
        employees = db.query(Employee).filter(Employee.status.ilike("ACTIVE")).all()

        # Find team leaders
        team_leaders = [e for e in employees if e.is_team_leader]
        print(f"Found {len(team_leaders)} team leaders: {[e.name for e in team_leaders]}")

        if not team_leaders:
            print("No team leaders found. Make sure is_team_leader is set on the correct employees.")
            print("Current employees with is_team_leader:")
            for e in employees:
                if e.is_team_leader:
                    print(f"  - {e.name} (is_team_leader={e.is_team_leader})")
            return

        created_teams = 0
        created_members = 0

        for leader in team_leaders:
            team_name = f"Team {leader.name}"
            leader_name_norm = _normalize(leader.name)

            # Check if team already exists
            existing_team = db.query(Team).filter(Team.name == team_name).first()
            if existing_team:
                print(f"  Team '{team_name}' already exists (id={existing_team.id}), skipping creation.")
                team = existing_team
            else:
                team = Team(
                    name=team_name,
                    leader_id=leader.id,
                    active_from=date(2026, 7, 1),  # Default: active from July
                    active_until=None,  # Still active
                    is_active=True,
                    target=0.0,
                )
                db.add(team)
                db.flush()  # Get the ID
                created_teams += 1
                print(f"  Created team: '{team_name}' (id={team.id}, leader={leader.name})")

            # Find members who report to this leader
            members = [
                e for e in employees
                if e.reporting_manager and _normalize(e.reporting_manager) == leader_name_norm
            ]

            for member in members:
                # Check if assignment already exists
                existing = db.query(TeamMember).filter(
                    TeamMember.employee_id == member.id,
                    TeamMember.team_id == team.id
                ).first()
                if not existing:
                    tm = TeamMember(
                        employee_id=member.id,
                        team_id=team.id,
                        start_date=date(2026, 7, 1),
                        end_date=None,
                    )
                    db.add(tm)
                    created_members += 1

            print(f"    -> {len(members)} members assigned to {team_name}")

        db.commit()
        print(f"\nDone! Created {created_teams} teams, {created_members} member assignments.")

        # Print summary
        print("\nTeam Summary:")
        all_teams = db.query(Team).all()
        for t in all_teams:
            member_count = db.query(TeamMember).filter(TeamMember.team_id == t.id).count()
            leader = db.query(Employee).filter(Employee.id == t.leader_id).first()
            print(f"  {t.name}: leader={leader.name if leader else 'None'}, "
                  f"members={member_count}, active_from={t.active_from}, "
                  f"active_until={t.active_until}")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed_teams()
