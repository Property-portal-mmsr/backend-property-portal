"""
Safe, Idempotent Database Migration and Configuration Seeding Service.

Handles:
1. Schema creation and column synchronization for all 8 logical entities (A–H).
2. Phase 3 Employee Status Implementation:
   - Deactivates Raj Singh and Sanjota effective November 1, 2026 (Employment end date: October 31, 2026).
   - Preserves all employee records, IDs, and historical associations.
   - Populates EmployeeEmploymentHistory for effective-dated eligibility checks.
3. Period Configuration Seeding:
   - September 2026 (2026-09)
   - October 2026 (2026-10)
   - November 2026 First Half (2026-11-01 to 2026-11-15)
   - November 2026 Second Half (2026-11-16 to 2026-11-30)
"""

import json
import logging
from datetime import date, datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.database.database import Base, engine, sync_table_schema
from app.models.employee import Employee
from app.models.employee_monthly_target import EmployeeMonthlyTarget
from app.models.team import Team, TeamMember
from app.models.period_config import (
    PeriodConfiguration,
    EmployeeEmploymentHistory,
    PeriodTeamAssignment,
    PeriodTargetConfiguration,
    PeriodIncentiveConfiguration,
    PeriodTeamTargetConfiguration,
    PerformanceCalculationRecord,
    ConfigurationAuditHistory,
)

logger = logging.getLogger(__name__)


def _find_emp_by_name(employees: List[Employee], name_query: str) -> Optional[Employee]:
    q = " ".join(name_query.lower().split())
    # Exact match first
    for e in employees:
        if e.name and " ".join(e.name.lower().split()) == q:
            return e
    # Specific disambiguation for Vinod vs Vinod Kumar
    if q == "vinod":
        for e in employees:
            if e.name and " ".join(e.name.lower().split()) == "vinod":
                return e
    # Token / substring match
    for e in employees:
        if not e.name:
            continue
        en = " ".join(e.name.lower().split())
        if q in en or en in q:
            return e
    return None


def _log_config_audit(
    db: Session,
    entity_type: str,
    entity_id: str,
    previous_value: Optional[dict],
    new_value: Optional[dict],
    changed_by: str = "System Migration",
    reason: Optional[str] = None,
):
    existing = (
        db.query(ConfigurationAuditHistory)
        .filter(
            ConfigurationAuditHistory.entity_type == entity_type,
            ConfigurationAuditHistory.entity_id == str(entity_id),
            ConfigurationAuditHistory.reason == reason,
        )
        .first()
    )
    if existing:
        return
    audit = ConfigurationAuditHistory(
        entity_type=entity_type,
        entity_id=str(entity_id),
        previous_value=json.dumps(previous_value) if previous_value is not None else None,
        new_value=json.dumps(new_value) if new_value is not None else None,
        changed_by=changed_by,
        change_timestamp=datetime.utcnow(),
        reason=reason,
    )
    db.add(audit)


def ensure_period_system_migrated_and_seeded(db: Session) -> dict:
    """
    Idempotently creates tables, syncs columns, applies effective-dated employee status
    changes, and seeds period configurations in MySQL.
    """
    sync_table_schema(engine, Base)
    Base.metadata.create_all(bind=engine)

    summary = {
        "deactivated_employees": [],
        "periods_seeded": [],
        "teams_ensured": [],
    }

    all_employees = db.query(Employee).all()

    # -----------------------------------------------------------------------
    # 0. Ensure historical September-exited employees (MMSR16, MMSR17) exist
    #    in the database with effective-dated INACTIVE status (end: 2026-09-30)
    #    so historical September reporting requires zero hardcoded rows in code.
    # -----------------------------------------------------------------------
    historical_sep_specs = [
        {
            "emp_id": "MMSR16",
            "name": "Abhishek",
            "email": "abhishek@makemystay.ai",
            "designation": "R.M",
            "department": "Sales",
            "reporting_manager": "Sanjota",
            "joining_date": "2026-06-01",
            "employment_end_date": "2026-09-30",
            "deactivation_effective_date": "2026-10-01",
        },
        {
            "emp_id": "MMSR17",
            "name": "Pratima",
            "email": "pratima@makemystay.ai",
            "designation": "R.M",
            "department": "Sales",
            "reporting_manager": "Kesava",
            "joining_date": "2026-04-01",
            "employment_end_date": "2026-09-30",
            "deactivation_effective_date": "2026-10-01",
        },
    ]
    for h_spec in historical_sep_specs:
        existing_h = _find_emp_by_name(all_employees, h_spec["name"])
        if not existing_h:
            existing_h = Employee(
                emp_id=h_spec["emp_id"],
                name=h_spec["name"],
                email=h_spec["email"],
                role="EMPLOYEE",
                designation=h_spec["designation"],
                department=h_spec["department"],
                reporting_manager=h_spec["reporting_manager"],
                joining_date=h_spec["joining_date"],
                employment_end_date=h_spec["employment_end_date"],
                deactivation_effective_date=h_spec["deactivation_effective_date"],
                status="INACTIVE",
                monthly_target=0.0,
                is_team_leader=False,
            )
            db.add(existing_h)
            db.flush()
            all_employees.append(existing_h)
        else:
            existing_h.status = "INACTIVE"
            existing_h.employment_end_date = h_spec["employment_end_date"]
            existing_h.deactivation_effective_date = h_spec["deactivation_effective_date"]
            if not existing_h.joining_date:
                existing_h.joining_date = h_spec["joining_date"]

        hist_row = (
            db.query(EmployeeEmploymentHistory)
            .filter(
                EmployeeEmploymentHistory.employee_id == existing_h.id,
                EmployeeEmploymentHistory.employment_status == "INACTIVE",
            )
            .first()
        )
        if not hist_row:
            db.add(
                EmployeeEmploymentHistory(
                    employee_id=existing_h.id,
                    employment_start_date=date.fromisoformat(h_spec["joining_date"]),
                    employment_end_date=date.fromisoformat(h_spec["employment_end_date"]),
                    employment_status="INACTIVE",
                    effective_date=date.fromisoformat(h_spec["deactivation_effective_date"]),
                    reason="Historical resignation effective October 1, 2026",
                    changed_by="System Migration",
                )
            )

    # -----------------------------------------------------------------------
    # 1. Ensure October 2026 joiners have joining_date = '2026-10-01' in DB
    #    so no hardcoded IDs/names are needed in eligibility checks.
    # -----------------------------------------------------------------------
    oct_joiner_names = [
        "Ankit Prajapati",
        "Pavan Tavarageri",
        "Vinod Kumar",
        "Kuncha Pavani",
        "Raj Singh",
        "Dheeraj Yadav",
        "Midabalam Manasa",
    ]
    for j_name in oct_joiner_names:
        emp = _find_emp_by_name(all_employees, j_name)
        if emp and emp.joining_date != "2026-10-01":
            prev_join = emp.joining_date
            emp.joining_date = "2026-10-01"
            _log_config_audit(
                db,
                entity_type="EmployeeJoiningDate",
                entity_id=str(emp.id),
                previous_value={"joining_date": prev_join},
                new_value={"joining_date": "2026-10-01"},
                reason="Standardize October 2026 joining date in database for effective-dated eligibility",
            )

    # -----------------------------------------------------------------------
    # 2. Phase 3 – Employee Deactivation: Raj Singh & Sanjota
    #    Effective deactivation date: November 1, 2026
    #    Employment end date: October 31, 2026
    #    Status from November 1: Inactive
    # -----------------------------------------------------------------------
    deactivation_specs = [
        {
            "name": "Raj Singh",
            "employment_start": date(2026, 10, 1),
            "employment_end": date(2026, 10, 31),
            "effective_date": date(2026, 11, 1),
            "reason": "Deactivated effective November 1, 2026 (Employment end date: October 31, 2026)",
        },
        {
            "name": "Sanjota",
            "employment_start": date(2023, 7, 1),
            "employment_end": date(2026, 10, 31),
            "effective_date": date(2026, 11, 1),
            "reason": "Deactivated effective November 1, 2026 (Employment end date: October 31, 2026)",
        },
        {
            "name": "Chaithra",
            "employment_start": date(2024, 7, 1),
            "employment_end": date(2026, 10, 31),
            "effective_date": date(2026, 11, 1),
            "reason": "Excluded from November 2026 calculations (Employment end date: October 31, 2026)",
        },
        {
            "name": "Pavan Tavarageri",
            "employment_start": date(2026, 10, 1),
            "employment_end": date(2026, 11, 15),
            "effective_date": date(2026, 11, 16),
            "reason": "Excluded from November 2026 Second Half calculations (Employment end date: November 15, 2026)",
        },
    ]

    for spec in deactivation_specs:
        emp = _find_emp_by_name(all_employees, spec["name"])
        if not emp:
            continue

        prev_state = {
            "status": emp.status,
            "employment_end_date": emp.employment_end_date,
            "deactivation_effective_date": emp.deactivation_effective_date,
        }

        emp.status = "INACTIVE"
        emp.employment_end_date = spec["employment_end"].isoformat()
        emp.deactivation_effective_date = spec["effective_date"].isoformat()

        # Ensure ACTIVE employment history record up to Oct 31, 2026
        active_hist = (
            db.query(EmployeeEmploymentHistory)
            .filter(
                EmployeeEmploymentHistory.employee_id == emp.id,
                EmployeeEmploymentHistory.employment_status == "ACTIVE",
            )
            .first()
        )
        if not active_hist:
            db.add(
                EmployeeEmploymentHistory(
                    employee_id=emp.id,
                    employment_start_date=spec["employment_start"],
                    employment_end_date=spec["employment_end"],
                    employment_status="ACTIVE",
                    effective_date=spec["employment_start"],
                    reason="Initial active employment period",
                    changed_by="System Migration",
                )
            )
        else:
            active_hist.employment_end_date = spec["employment_end"]

        # Ensure INACTIVE employment history record effective Nov 1, 2026
        inactive_hist = (
            db.query(EmployeeEmploymentHistory)
            .filter(
                EmployeeEmploymentHistory.employee_id == emp.id,
                EmployeeEmploymentHistory.employment_status == "INACTIVE",
                EmployeeEmploymentHistory.effective_date == spec["effective_date"],
            )
            .first()
        )
        if not inactive_hist:
            db.add(
                EmployeeEmploymentHistory(
                    employee_id=emp.id,
                    employment_start_date=spec["employment_start"],
                    employment_end_date=spec["employment_end"],
                    employment_status="INACTIVE",
                    effective_date=spec["effective_date"],
                    reason=spec["reason"],
                    changed_by="System Administrator",
                )
            )

        _log_config_audit(
            db,
            entity_type="EmployeeStatus",
            entity_id=str(emp.id),
            previous_value=prev_state,
            new_value={
                "name": emp.name,
                "status": "INACTIVE",
                "employment_end_date": spec["employment_end"].isoformat(),
                "deactivation_effective_date": spec["effective_date"].isoformat(),
            },
            changed_by="System Administrator",
            reason=spec["reason"],
        )
        summary["deactivated_employees"].append(emp.name)

    # Ensure all other employees have an EmployeeEmploymentHistory record
    for emp in all_employees:
        has_hist = (
            db.query(EmployeeEmploymentHistory)
            .filter(EmployeeEmploymentHistory.employee_id == emp.id)
            .first()
        )
        if not has_hist:
            start_dt = date(2024, 1, 1)
            if emp.joining_date:
                try:
                    start_dt = date.fromisoformat(emp.joining_date[:10])
                except ValueError:
                    pass
            db.add(
                EmployeeEmploymentHistory(
                    employee_id=emp.id,
                    employment_start_date=start_dt,
                    employment_end_date=None,
                    employment_status=(emp.status or "ACTIVE").upper(),
                    effective_date=start_dt,
                    reason="Employment record initialized",
                    changed_by="System Migration",
                )
            )

    # Also close Team Sanjota in `teams` table effective 2026-10-31 and ensure Team Madhav exists from 2026-11-01
    sanjota_emp = _find_emp_by_name(all_employees, "Sanjota")
    madhava_emp = _find_emp_by_name(all_employees, "Madhava R")
    arun_emp = _find_emp_by_name(all_employees, "Arun N")
    goutham_emp = _find_emp_by_name(all_employees, "Goutham N")
    kesava_emp = _find_emp_by_name(all_employees, "Kesava")

    team_sanjota = db.query(Team).filter(Team.name == "Team Sanjota").first()
    if team_sanjota and team_sanjota.active_until != date(2026, 10, 31):
        team_sanjota.active_until = date(2026, 10, 31)

    team_madhav = db.query(Team).filter(Team.name == "Team Madhav").first()
    if not team_madhav and madhava_emp:
        team_madhav = Team(
            name="Team Madhav",
            leader_id=madhava_emp.id,
            active_from=date(2026, 11, 1),
            active_until=None,
            is_active=True,
            target=360000.0,
        )
        db.add(team_madhav)
        db.flush()
        summary["teams_ensured"].append("Team Madhav")

    team_arun = db.query(Team).filter(Team.name == "Team Arun").first()
    team_goutham = db.query(Team).filter(Team.name == "Team Goutham").first()
    team_kesava = db.query(Team).filter(Team.name == "Team Kesava").first()

    db.flush()

    # -----------------------------------------------------------------------
    # 2b. Synchronize `team_members` table with effective start_date / end_date
    #     for Team Sanjota (up to 2026-10-31), Team Madhav (Nov 1-15 & Nov 16+),
    #     Team Goutham, Team Arun, and Team Kesava.
    # -----------------------------------------------------------------------
    def _ensure_team_member_window(team_obj: Optional[Team], emp_name: str, s_date: date, e_date: Optional[date]):
        if not team_obj:
            return
        emp = _find_emp_by_name(all_employees, emp_name)
        if not emp:
            return
        existing_rows = (
            db.query(TeamMember)
            .filter(TeamMember.team_id == team_obj.id, TeamMember.employee_id == emp.id)
            .order_by(TeamMember.id.asc())
            .all()
        )
        # Check if an exact matching window already exists
        for row in existing_rows:
            if row.start_date == s_date and row.end_date == e_date:
                return
        # If there is a single open-ended legacy row starting 2026-07-01 or 2026-10-01, update its end_date if needed
        if len(existing_rows) == 1 and existing_rows[0].start_date in (date(2026, 7, 1), date(2026, 10, 1)) and s_date in (date(2026, 7, 1), date(2026, 10, 1)):
            existing_rows[0].end_date = e_date
            return
        db.add(
            TeamMember(
                team_id=team_obj.id,
                employee_id=emp.id,
                start_date=s_date,
                end_date=e_date,
            )
        )

    # Close Team Sanjota member windows at 2026-10-31
    if team_sanjota:
        for tm in db.query(TeamMember).filter(TeamMember.team_id == team_sanjota.id).all():
            if tm.end_date is None or tm.end_date > date(2026, 10, 31):
                tm.end_date = date(2026, 10, 31)

    # Rebuild Team Madhav (team_id=5) effective windows cleanly:
    # Nov 1–15, 2026: Chethan P, Pritish Kumar Jena, Vinod, Pavan Tavarageri, Ankit Prajapati
    # Nov 16–30, 2026: Pritish Kumar Jena, Kalyan Kumar Reddy, Chethan P, Likitha
    if team_madhav:
        db.query(TeamMember).filter(TeamMember.team_id == team_madhav.id).delete()
        #Chethan P and Pritish Kumar Jena are in Team Madhav for both Nov 1–15 and Nov 16–30 (2026-11-01 onwards)
        for m_name in ["Chethan P", "Pritish Kumar Jena"]:
            _ensure_team_member_window(team_madhav, m_name, date(2026, 11, 1), None)
        # Vinod, Pavan Tavarageri, Ankit Prajapati are in Team Madhav ONLY for Nov 1–15 (2026-11-01 to 2026-11-15)
        for m_name in ["Vinod", "Pavan Tavarageri", "Ankit Prajapati"]:
            _ensure_team_member_window(team_madhav, m_name, date(2026, 11, 1), date(2026, 11, 15))
        # Kalyan Kumar Reddy and Likitha join Team Madhav from Nov 16 (2026-11-16 onwards)
        for m_name in ["Kalyan Kumar Reddy", "Likitha"]:
            _ensure_team_member_window(team_madhav, m_name, date(2026, 11, 16), None)

    # Update Team Kesava member windows for Nov 16 transitions
    if team_kesava:
        for m_name in ["Kalyan Kumar Reddy", "Likitha"]:
            emp = _find_emp_by_name(all_employees, m_name)
            if emp:
                for tm in db.query(TeamMember).filter(TeamMember.team_id == team_kesava.id, TeamMember.employee_id == emp.id).all():
                    tm.end_date = date(2026, 11, 15)
        for m_name in ["Ankit Prajapati", "Vinod"]:
            _ensure_team_member_window(team_kesava, m_name, date(2026, 11, 16), None)

    # Update Team Goutham member windows for Nov 16 transitions (Chaithra ends Oct 31, 2026; Pavan excluded from Nov H2)
    if team_goutham:
        chaithra_emp = _find_emp_by_name(all_employees, "Chaithra")
        if chaithra_emp:
            for tm in db.query(TeamMember).filter(TeamMember.team_id == team_goutham.id, TeamMember.employee_id == chaithra_emp.id).all():
                tm.end_date = date(2026, 10, 31)
        pavan_emp = _find_emp_by_name(all_employees, "Pavan Tavarageri")
        if pavan_emp:
            db.query(TeamMember).filter(
                TeamMember.team_id == team_goutham.id,
                TeamMember.employee_id == pavan_emp.id,
            ).delete()

    db.flush()

    # -----------------------------------------------------------------------
    # 3. Helper to upsert a PeriodConfiguration and its child records
    # -----------------------------------------------------------------------
    def _upsert_period(
        period_code: str,
        period_name: str,
        start_dt: date,
        end_dt: date,
        month_str: str,
        year_val: int,
        period_type: str,
        team_specs: List[dict],
        individual_targets: List[tuple],
        rm_slabs: List[dict],
        tl_slabs: List[dict],
    ):
        period = (
            db.query(PeriodConfiguration)
            .filter(PeriodConfiguration.period_code == period_code)
            .first()
        )
        if not period:
            period = PeriodConfiguration(
                period_code=period_code,
                period_name=period_name,
                start_date=start_dt,
                end_date=end_dt,
                month=month_str,
                year=year_val,
                period_type=period_type,
                configuration_status="ACTIVE",
                approval_status="APPROVED",
                version=1,
                created_by="System Administrator",
            )
            db.add(period)
            db.flush()
            _log_config_audit(
                db,
                entity_type="PeriodConfiguration",
                entity_id=str(period.id),
                previous_value=None,
                new_value={
                    "period_code": period_code,
                    "period_name": period_name,
                    "start_date": start_dt.isoformat(),
                    "end_date": end_dt.isoformat(),
                },
                changed_by="System Administrator",
                reason=f"Initialized period configuration {period_name}",
            )
            summary["periods_seeded"].append(period_code)
        else:
            # If period was already created and has expected target count, preserve any admin edits
            has_targets = (
                db.query(PeriodTargetConfiguration)
                .filter(PeriodTargetConfiguration.period_id == period.id)
                .count()
            )
            if has_targets == len(individual_targets):
                return period

        # Clear any partial child records for clean initialization
        db.query(PeriodTeamAssignment).filter(PeriodTeamAssignment.period_id == period.id).delete()
        db.query(PeriodTargetConfiguration).filter(PeriodTargetConfiguration.period_id == period.id).delete()
        db.query(PeriodIncentiveConfiguration).filter(PeriodIncentiveConfiguration.period_id == period.id).delete()
        db.query(PeriodTeamTargetConfiguration).filter(PeriodTeamTargetConfiguration.period_id == period.id).delete()
        db.query(PerformanceCalculationRecord).filter(PerformanceCalculationRecord.period_id == period.id).delete()

        # Insert individual targets
        target_lookup: Dict[int, float] = {}
        for emp_name, tgt_amount in individual_targets:
            emp = _find_emp_by_name(all_employees, emp_name)
            if not emp:
                logger.warning(f"Employee '{emp_name}' not found while seeding {period_code}")
                continue
            target_lookup[emp.id] = float(tgt_amount)
            db.add(
                PeriodTargetConfiguration(
                    period_id=period.id,
                    employee_id=emp.id,
                    assigned_target_amount=float(tgt_amount),
                    target_type="INDIVIDUAL_RM",
                    approval_status="APPROVED",
                )
            )

        # Insert team assignments and team target configurations
        for t_spec in team_specs:
            t_obj: Optional[Team] = t_spec["team"]
            leader_obj: Optional[Employee] = t_spec["leader"]
            display_team_name: str = t_spec["team_name"]
            if not t_obj or not leader_obj:
                continue

            member_emps: List[Employee] = []
            for m_name in t_spec["members"]:
                m_emp = _find_emp_by_name(all_employees, m_name)
                if m_emp and m_emp not in member_emps:
                    member_emps.append(m_emp)

            for m_emp in member_emps:
                db.add(
                    PeriodTeamAssignment(
                        period_id=period.id,
                        employee_id=m_emp.id,
                        team_id=t_obj.id,
                        team_leader_id=leader_obj.id,
                        team_name=display_team_name,
                        effective_start_date=start_dt,
                        effective_end_date=end_dt,
                    )
                )

            agg_target = t_spec.get("aggregate_target")
            if agg_target is None:
                agg_target = sum(target_lookup.get(m.id, 0.0) for m in member_emps)

            db.add(
                PeriodTeamTargetConfiguration(
                    period_id=period.id,
                    team_id=t_obj.id,
                    team_leader_id=leader_obj.id,
                    team_name=display_team_name,
                    aggregate_target=float(agg_target),
                    team_leader_incentive=float(t_spec.get("tl_incentive", 20000.0)),
                    eligibility_percentage=float(t_spec.get("eligibility_pct", 100.0)),
                )
            )

        # Insert RM incentive slabs
        for idx, slab in enumerate(rm_slabs):
            db.add(
                PeriodIncentiveConfiguration(
                    period_id=period.id,
                    incentive_type="RM",
                    slab_label=slab.get("label"),
                    assigned_target_amount=slab.get("assigned_target"),
                    min_assigned_target=slab.get("min_target"),
                    max_assigned_target=slab.get("max_target"),
                    achievement_threshold=float(slab.get("threshold", 100.0)),
                    incentive_amount=float(slab.get("incentive", 0.0)),
                    eligibility_conditions=slab.get("condition", "EXACT_TARGET_PCT"),
                    calculation_method=slab.get("method", "FIXED_SLAB"),
                    priority=int(slab.get("priority", idx + 1)),
                    active_status=True,
                )
            )

        # Insert Team Leader incentive slabs
        for idx, slab in enumerate(tl_slabs):
            db.add(
                PeriodIncentiveConfiguration(
                    period_id=period.id,
                    incentive_type="TEAM_LEADER",
                    slab_label=slab.get("label"),
                    assigned_target_amount=slab.get("assigned_target"),
                    min_assigned_target=slab.get("min_target"),
                    max_assigned_target=slab.get("max_target"),
                    achievement_threshold=float(slab.get("threshold", 100.0)),
                    incentive_amount=float(slab.get("incentive", 0.0)),
                    eligibility_conditions=slab.get("condition", "TEAM_TARGET_PCT"),
                    calculation_method=slab.get("method", "FIXED_SLAB"),
                    priority=int(slab.get("priority", idx + 1)),
                    active_status=True,
                )
            )

        return period

    # -----------------------------------------------------------------------
    # 4. Seed Period Configurations
    # -----------------------------------------------------------------------

    # --- A. September 2026 (Historical preservation) ---
    _upsert_period(
        period_code="2026-09",
        period_name="September 2026",
        start_dt=date(2026, 9, 1),
        end_dt=date(2026, 9, 30),
        month_str="2026-09",
        year_val=2026,
        period_type="FULL_MONTH",
        team_specs=[
            {
                "team": team_sanjota,
                "leader": sanjota_emp,
                "team_name": "Team Sanjota",
                "members": ["Chethan P", "Pritish Kumar Jena", "Vinod", "Abhishek"],
                "aggregate_target": 510000.0,
                "tl_incentive": 15000.0,
                "eligibility_pct": 100.0,
            },
            {
                "team": team_kesava,
                "leader": kesava_emp,
                "team_name": "Team Kesava",
                "members": ["Kalyan Kumar Reddy", "Likitha", "Lukmanul Hateem M A", "Pratima"],
                "aggregate_target": 505000.0,
                "tl_incentive": 15000.0,
                "eligibility_pct": 100.0,
            },
        ],
        individual_targets=[
            ("Arun N", 150000.0),
            ("Goutham N", 150000.0),
            ("Chethan P", 135000.0),
            ("Pritish Kumar Jena", 135000.0),
            ("Kalyan Kumar Reddy", 135000.0),
            ("Likitha", 125000.0),
            ("Lukmanul Hateem M A", 125000.0),
            ("Vinod", 120000.0),
            ("Abhishek", 120000.0),
            ("Pratima", 120000.0),
        ],
        rm_slabs=[
            {"label": "Revenue >= ₹2,00,000 -> ₹30,000", "threshold": 200000.0, "incentive": 30000.0, "condition": "ABSOLUTE_REVENUE", "method": "ABSOLUTE_REVENUE", "priority": 3},
            {"label": "Revenue >= ₹1,50,000 -> ₹18,000", "threshold": 150000.0, "incentive": 18000.0, "condition": "ABSOLUTE_REVENUE", "method": "ABSOLUTE_REVENUE", "priority": 2},
            {"label": "100% Target Achieved -> ₹12,000", "threshold": 100.0, "incentive": 12000.0, "condition": "ANY_TARGET_PCT", "method": "FIXED_SLAB", "priority": 1},
        ],
        tl_slabs=[
            {"label": "Team Revenue >= ₹7,00,000 -> ₹50,000", "threshold": 700000.0, "incentive": 50000.0, "condition": "ABSOLUTE_REVENUE", "method": "ABSOLUTE_REVENUE", "priority": 3},
            {"label": "Team Revenue >= ₹6,00,000 -> ₹30,000", "threshold": 600000.0, "incentive": 30000.0, "condition": "ABSOLUTE_REVENUE", "method": "ABSOLUTE_REVENUE", "priority": 2},
            {"label": "100% Team Target -> ₹15,000", "threshold": 100.0, "incentive": 15000.0, "condition": "TEAM_TARGET_PCT", "method": "FIXED_SLAB", "priority": 1},
        ],
    )

    # --- B. October 2026 (Historical preservation) ---
    _upsert_period(
        period_code="2026-10",
        period_name="October 2026",
        start_dt=date(2026, 10, 1),
        end_dt=date(2026, 10, 31),
        month_str="2026-10",
        year_val=2026,
        period_type="FULL_MONTH",
        team_specs=[
            {
                "team": team_sanjota,
                "leader": sanjota_emp,
                "team_name": "Team Sanjota",
                "members": ["Chethan P", "Pritish Kumar Jena", "Vinod", "Ankit Prajapati", "Pavan Tavarageri"],
                "aggregate_target": 470000.0,
                "tl_incentive": 15000.0,
                "eligibility_pct": 100.0,
            },
            {
                "team": team_kesava,
                "leader": kesava_emp,
                "team_name": "Team Kesava",
                "members": ["Kalyan Kumar Reddy", "Likitha", "Lukmanul Hateem M A", "Vinod Kumar", "Midabalam Manasa"],
                "aggregate_target": 470000.0,
                "tl_incentive": 15000.0,
                "eligibility_pct": 100.0,
            },
            {
                "team": team_goutham,
                "leader": goutham_emp,
                "team_name": "Team Goutham",
                "members": ["Chaithra", "Akhila G", "Bavitha", "Gyananjay", "Joys"],
                "aggregate_target": 275000.0,
                "tl_incentive": 15000.0,
                "eligibility_pct": 100.0,
            },
            {
                "team": team_arun,
                "leader": arun_emp,
                "team_name": "Team Arun",
                "members": ["Mounika Rudraraju", "kaveri Gogoi", "Kuncha Pavani", "Raj Singh", "Dheeraj Yadav"],
                "aggregate_target": 275000.0,
                "tl_incentive": 15000.0,
                "eligibility_pct": 100.0,
            },
        ],
        individual_targets=[
            ("Chethan P", 120000.0),
            ("Pritish Kumar Jena", 120000.0),
            ("Kalyan Kumar Reddy", 120000.0),
            ("Vinod", 120000.0),
            ("Likitha", 120000.0),
            ("Lukmanul Hateem M A", 120000.0),
            ("Chaithra", 55000.0),
            ("Akhila G", 55000.0),
            ("Ankit Prajapati", 55000.0),
            ("Pavan Tavarageri", 55000.0),
            ("Mounika Rudraraju", 55000.0),
            ("kaveri Gogoi", 55000.0),
            ("Bavitha", 55000.0),
            ("Gyananjay", 55000.0),
            ("Joys", 55000.0),
            ("Vinod Kumar", 55000.0),
            ("Kuncha Pavani", 55000.0),
            ("Raj Singh", 55000.0),
            ("Dheeraj Yadav", 55000.0),
            ("Midabalam Manasa", 55000.0),
        ],
        rm_slabs=[
            {"label": "Slab A (>=₹1.2L): 200% -> ₹40,000", "min_target": 120000.0, "threshold": 200.0, "incentive": 40000.0, "condition": "MIN_TARGET_PCT", "method": "FIXED_SLAB", "priority": 6},
            {"label": "Slab A (>=₹1.2L): 125% -> ₹18,000", "min_target": 120000.0, "threshold": 125.0, "incentive": 18000.0, "condition": "MIN_TARGET_PCT", "method": "FIXED_SLAB", "priority": 5},
            {"label": "Slab A (>=₹1.2L): 100% -> ₹12,000", "min_target": 120000.0, "threshold": 100.0, "incentive": 12000.0, "condition": "MIN_TARGET_PCT", "method": "FIXED_SLAB", "priority": 4},
            {"label": "Slab B (>=₹55k): 130% -> ₹10,000", "min_target": 55000.0, "max_target": 119999.0, "threshold": 130.0, "incentive": 10000.0, "condition": "MIN_TARGET_PCT", "method": "FIXED_SLAB", "priority": 2},
            {"label": "Slab B (>=₹55k): 100% -> ₹5,000", "min_target": 55000.0, "max_target": 119999.0, "threshold": 100.0, "incentive": 5000.0, "condition": "MIN_TARGET_PCT", "method": "FIXED_SLAB", "priority": 1},
        ],
        tl_slabs=[
            {"label": "150% Team Target -> ₹60,000", "threshold": 150.0, "incentive": 60000.0, "condition": "TEAM_TARGET_PCT", "method": "FIXED_SLAB", "priority": 3},
            {"label": "125% Team Target -> ₹35,000", "threshold": 125.0, "incentive": 35000.0, "condition": "TEAM_TARGET_PCT", "method": "FIXED_SLAB", "priority": 2},
            {"label": "100% Team Target -> ₹15,000", "threshold": 100.0, "incentive": 15000.0, "condition": "TEAM_TARGET_PCT", "method": "FIXED_SLAB", "priority": 1},
        ],
    )

    # --- C. November 2026 First Half (Nov 1–15, 2026) ---
    # Preserves all previously approved first-half assignments, targets, and slabs,
    # excluding Raj Singh, Sanjota, and Chaithra (18 active RMs, ₹6,90,000 total target).
    _upsert_period(
        period_code="2026-11-H1",
        period_name="November 2026 First Half",
        start_dt=date(2026, 11, 1),
        end_dt=date(2026, 11, 15),
        month_str="2026-11",
        year_val=2026,
        period_type="FIRST_HALF",
        team_specs=[
            {
                "team": team_goutham,
                "leader": goutham_emp,
                "team_name": "Team Goutham",
                "members": ["Akhila G", "Bavitha", "Gyananjay", "Joys"],
                "aggregate_target": 120000.0,
                "tl_incentive": 12500.0,
                "eligibility_pct": 100.0,
            },
            {
                "team": team_arun,
                "leader": arun_emp,
                "team_name": "Team Arun",
                "members": ["Mounika Rudraraju", "kaveri Gogoi", "Kuncha Pavani", "Dheeraj Yadav"],
                "aggregate_target": 120000.0,
                "tl_incentive": 12500.0,
                "eligibility_pct": 100.0,
            },
            {
                "team": team_kesava,
                "leader": kesava_emp,
                "team_name": "Team Kesava",
                "members": ["Kalyan Kumar Reddy", "Likitha", "Lukmanul Hateem M A", "Vinod Kumar", "Midabalam Manasa"],
                "aggregate_target": 225000.0,
                "tl_incentive": 12500.0,
                "eligibility_pct": 100.0,
            },
            {
                "team": team_madhav,
                "leader": madhava_emp,
                "team_name": "Team Madhav",
                "members": ["Chethan P", "Pritish Kumar Jena", "Vinod", "Pavan Tavarageri", "Ankit Prajapati"],
                "aggregate_target": 225000.0,
                "tl_incentive": 12500.0,
                "eligibility_pct": 100.0,
            },
        ],
        individual_targets=[
            ("Chethan P", 55000.0),
            ("Akhila G", 30000.0),
            ("Likitha", 55000.0),
            ("Kuncha Pavani", 30000.0),
            ("Ankit Prajapati", 30000.0),
            ("kaveri Gogoi", 30000.0),
            ("Kalyan Kumar Reddy", 55000.0),
            ("Pritish Kumar Jena", 55000.0),
            ("Gyananjay", 30000.0),
            ("Bavitha", 30000.0),
            ("Vinod Kumar", 30000.0),
            ("Joys", 30000.0),
            ("Lukmanul Hateem M A", 55000.0),
            ("Mounika Rudraraju", 30000.0),
            ("Vinod", 55000.0),
            ("Pavan Tavarageri", 30000.0),
            ("Dheeraj Yadav", 30000.0),
            ("Midabalam Manasa", 30000.0),
        ],
        rm_slabs=[
            {"label": "₹55,000 Target -> ₹8,000", "assigned_target": 55000.0, "threshold": 100.0, "incentive": 8000.0, "condition": "EXACT_TARGET_PCT", "method": "FIXED_SLAB", "priority": 2},
            {"label": "₹30,000 Target -> ₹4,500", "assigned_target": 30000.0, "threshold": 100.0, "incentive": 4500.0, "condition": "EXACT_TARGET_PCT", "method": "FIXED_SLAB", "priority": 1},
        ],
        tl_slabs=[
            {"label": "100% Team Target -> ₹12,500", "threshold": 100.0, "incentive": 12500.0, "condition": "TEAM_TARGET_PCT", "method": "FIXED_SLAB", "priority": 1},
        ],
    )

    # --- D. November 2026 Second Half (Nov 16–30, 2026) ---
    # 17 Employees across 4 Teams (Goutham: ₹1.40L, Arun: ₹1.40L, Keshav: ₹2.15L, Madhav: ₹3.60L = ₹8.55L)
    # RM Slabs: ₹35k -> ₹6k, ₹55k -> ₹10k, ₹90k -> ₹20k
    # TL Slab: 100% of Aggregate Team Target -> ₹20,000
    _upsert_period(
        period_code="2026-11-H2",
        period_name="November 2026 Second Half",
        start_dt=date(2026, 11, 16),
        end_dt=date(2026, 11, 30),
        month_str="2026-11",
        year_val=2026,
        period_type="SECOND_HALF",
        team_specs=[
            {
                "team": team_goutham,
                "leader": goutham_emp,
                "team_name": "Team Goutham",
                "members": ["Akhila G", "Gyananjay", "Bavitha", "Joys"],
                "aggregate_target": 140000.0,
                "tl_incentive": 20000.0,
                "eligibility_pct": 100.0,
            },
            {
                "team": team_arun,
                "leader": arun_emp,
                "team_name": "Team Arun",
                "members": ["kaveri Gogoi", "Dheeraj Yadav", "Kuncha Pavani", "Mounika Rudraraju"],
                "aggregate_target": 140000.0,
                "tl_incentive": 20000.0,
                "eligibility_pct": 100.0,
            },
            {
                "team": team_kesava,
                "leader": kesava_emp,
                "team_name": "Team Keshav",
                "members": ["Ankit Prajapati", "Vinod", "Vinod Kumar", "Lukmanul Hateem M A", "Midabalam Manasa"],
                "aggregate_target": 215000.0,
                "tl_incentive": 20000.0,
                "eligibility_pct": 100.0,
            },
            {
                "team": team_madhav,
                "leader": madhava_emp,
                "team_name": "Team Madhav",
                "members": ["Pritish Kumar Jena", "Kalyan Kumar Reddy", "Chethan P", "Likitha"],
                "aggregate_target": 360000.0,
                "tl_incentive": 20000.0,
                "eligibility_pct": 100.0,
            },
        ],
        individual_targets=[
            # Team Goutham (4 * 35,000 = 1,40,000)
            ("Akhila G", 35000.0),
            ("Gyananjay", 35000.0),
            ("Bavitha", 35000.0),
            ("Joys", 35000.0),
            # Team Arun (4 * 35,000 = 1,40,000)
            ("kaveri Gogoi", 35000.0),
            ("Dheeraj Yadav", 35000.0),
            ("Kuncha Pavani", 35000.0),
            ("Mounika Rudraraju", 35000.0),
            # Team Keshav (35k + 55k + 35k + 55k + 35k = 2,15,000)
            ("Ankit Prajapati", 35000.0),
            ("Vinod", 55000.0),
            ("Vinod Kumar", 35000.0),
            ("Lukmanul Hateem M A", 55000.0),
            ("Midabalam Manasa", 35000.0),
            # Team Madhav (4 * 90,000 = 3,60,000)
            ("Pritish Kumar Jena", 90000.0),
            ("Kalyan Kumar Reddy", 90000.0),
            ("Chethan P", 90000.0),
            ("Likitha", 90000.0),
        ],
        rm_slabs=[
            {"label": "₹90,000 Target -> ₹20,000", "assigned_target": 90000.0, "threshold": 100.0, "incentive": 20000.0, "condition": "EXACT_TARGET_PCT", "method": "FIXED_SLAB", "priority": 3},
            {"label": "₹55,000 Target -> ₹10,000", "assigned_target": 55000.0, "threshold": 100.0, "incentive": 10000.0, "condition": "EXACT_TARGET_PCT", "method": "FIXED_SLAB", "priority": 2},
            {"label": "₹35,000 Target -> ₹6,000", "assigned_target": 35000.0, "threshold": 100.0, "incentive": 6000.0, "condition": "EXACT_TARGET_PCT", "method": "FIXED_SLAB", "priority": 1},
        ],
        tl_slabs=[
            {"label": "100% Team Target -> ₹20,000", "threshold": 100.0, "incentive": 20000.0, "condition": "TEAM_TARGET_PCT", "method": "FIXED_SLAB", "priority": 1},
        ],
    )

    db.commit()
    return summary
