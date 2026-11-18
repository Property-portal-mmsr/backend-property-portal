"""
Period Configuration, Team Assignment, Target Allocation, and Incentive Slab
Management Service for the CRM Administration Interface.
"""

import json
from datetime import date, datetime
from typing import Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.team import Team
from app.models.period_config import (
    PeriodConfiguration,
    EmployeeEmploymentHistory,
    PeriodTeamAssignment,
    PeriodTargetConfiguration,
    PeriodIncentiveConfiguration,
    PeriodTeamTargetConfiguration,
    ConfigurationAuditHistory,
)
from app.schemas.period_config import (
    PeriodSummaryBrief,
    PeriodConfigurationDetailResponse,
    PeriodConfigurationCreateRequest,
    PeriodConfigurationBulkSaveRequest,
    TeamAssignmentResponse,
    TargetAllocationResponse,
    IncentiveSlabResponse,
    TeamTargetConfigResponse,
    ConfigurationAuditHistoryResponse,
    EmployeeEmploymentHistoryResponse,
)
from app.services.eligibility_service import EligibilityService


class PeriodConfigService:
    @staticmethod
    def list_periods(
        db: Session,
        month: Optional[str] = None,
        year: Optional[int] = None,
    ) -> List[PeriodSummaryBrief]:
        q = db.query(PeriodConfiguration)
        if month:
            q = q.filter(PeriodConfiguration.month == month)
        if year:
            q = q.filter(PeriodConfiguration.year == year)
        periods = q.order_by(PeriodConfiguration.start_date.desc(), PeriodConfiguration.id.desc()).all()

        result: List[PeriodSummaryBrief] = []
        for p in periods:
            targets = (
                db.query(PeriodTargetConfiguration)
                .filter(PeriodTargetConfiguration.period_id == p.id)
                .all()
            )
            teams = (
                db.query(PeriodTeamTargetConfiguration)
                .filter(PeriodTeamTargetConfiguration.period_id == p.id)
                .all()
            )
            active_emp_count = sum(1 for t in targets if t.assigned_target_amount > 0)
            total_tgt = sum(t.assigned_target_amount for t in targets)
            result.append(
                PeriodSummaryBrief(
                    id=p.id,
                    period_code=p.period_code,
                    period_name=p.period_name,
                    start_date=p.start_date,
                    end_date=p.end_date,
                    month=p.month,
                    year=p.year,
                    period_type=p.period_type,
                    configuration_status=p.configuration_status,
                    approval_status=p.approval_status,
                    version=p.version,
                    active_employee_count=active_emp_count,
                    total_target=total_tgt,
                    team_count=len(teams),
                )
            )
        return result

    @staticmethod
    def get_period_detail(
        db: Session,
        period_id: int,
    ) -> PeriodConfigurationDetailResponse:
        period = db.query(PeriodConfiguration).filter(PeriodConfiguration.id == period_id).first()
        if not period:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Period configuration not found")

        all_emps = {e.id: e for e in db.query(Employee).all()}
        all_teams = {t.id: t for t in db.query(Team).all()}
        hist_map = EligibilityService.build_history_map(db)

        assignments = (
            db.query(PeriodTeamAssignment)
            .filter(PeriodTeamAssignment.period_id == period.id)
            .all()
        )
        targets = (
            db.query(PeriodTargetConfiguration)
            .filter(PeriodTargetConfiguration.period_id == period.id)
            .all()
        )
        slabs = (
            db.query(PeriodIncentiveConfiguration)
            .filter(PeriodIncentiveConfiguration.period_id == period.id)
            .order_by(PeriodIncentiveConfiguration.incentive_type.asc(), PeriodIncentiveConfiguration.priority.desc())
            .all()
        )
        team_targets = (
            db.query(PeriodTeamTargetConfiguration)
            .filter(PeriodTeamTargetConfiguration.period_id == period.id)
            .all()
        )

        emp_team_map: Dict[int, PeriodTeamAssignment] = {a.employee_id: a for a in assignments}
        emp_target_map: Dict[int, float] = {t.employee_id: t.assigned_target_amount for t in targets}

        assignment_responses: List[TeamAssignmentResponse] = []
        for a in assignments:
            emp = all_emps.get(a.employee_id)
            leader = all_emps.get(a.team_leader_id)
            team = all_teams.get(a.team_id)
            is_elig = EligibilityService.is_employee_eligible_for_period(
                emp, period.start_date, period.end_date, hist_map
            )
            assignment_responses.append(
                TeamAssignmentResponse(
                    id=a.id,
                    period_id=period.id,
                    employee_id=a.employee_id,
                    employee_name=emp.name if emp else f"Employee #{a.employee_id}",
                    employee_status="Active" if is_elig else "Inactive",
                    team_id=a.team_id,
                    team_name=a.team_name or (team.name if team else f"Team #{a.team_id}"),
                    team_leader_id=a.team_leader_id,
                    team_leader_name=leader.name if leader else f"Leader #{a.team_leader_id}",
                    effective_start_date=a.effective_start_date,
                    effective_end_date=a.effective_end_date,
                )
            )
        assignment_responses.sort(key=lambda x: (x.team_name, x.employee_name))

        target_responses: List[TargetAllocationResponse] = []
        for t in targets:
            emp = all_emps.get(t.employee_id)
            assign = emp_team_map.get(t.employee_id)
            leader = all_emps.get(assign.team_leader_id) if assign else None
            is_elig = EligibilityService.is_employee_eligible_for_period(
                emp, period.start_date, period.end_date, hist_map
            )
            target_responses.append(
                TargetAllocationResponse(
                    id=t.id,
                    period_id=period.id,
                    employee_id=t.employee_id,
                    employee_name=emp.name if emp else f"Employee #{t.employee_id}",
                    employee_status="Active" if is_elig else "Inactive",
                    team_name=assign.team_name if assign else None,
                    team_leader_name=leader.name if leader else None,
                    assigned_target_amount=t.assigned_target_amount,
                    target_type=t.target_type,
                    approval_status=t.approval_status,
                )
            )
        target_responses.sort(key=lambda x: (x.team_name or "ZZZ", x.employee_name))

        slab_responses: List[IncentiveSlabResponse] = [
            IncentiveSlabResponse(
                id=s.id,
                period_id=s.period_id,
                incentive_type=s.incentive_type,
                slab_label=s.slab_label,
                assigned_target_amount=s.assigned_target_amount,
                min_assigned_target=s.min_assigned_target,
                max_assigned_target=s.max_assigned_target,
                achievement_threshold=s.achievement_threshold,
                incentive_amount=s.incentive_amount,
                eligibility_conditions=s.eligibility_conditions,
                calculation_method=s.calculation_method,
                priority=s.priority,
                active_status=s.active_status,
            )
            for s in slabs
        ]

        team_target_responses: List[TeamTargetConfigResponse] = []
        for tt in team_targets:
            leader = all_emps.get(tt.team_leader_id)
            team = all_teams.get(tt.team_id)
            members_in_team = [a for a in assignments if a.team_id == tt.team_id]
            computed_sum = sum(emp_target_map.get(a.employee_id, 0.0) for a in members_in_team)
            team_target_responses.append(
                TeamTargetConfigResponse(
                    id=tt.id,
                    period_id=period.id,
                    team_id=tt.team_id,
                    team_name=tt.team_name or (team.name if team else f"Team #{tt.team_id}"),
                    team_leader_id=tt.team_leader_id,
                    team_leader_name=leader.name if leader else f"Leader #{tt.team_leader_id}",
                    member_count=len(members_in_team),
                    aggregate_target=tt.aggregate_target,
                    computed_member_target_sum=computed_sum,
                    team_leader_incentive=tt.team_leader_incentive,
                    eligibility_percentage=tt.eligibility_percentage,
                )
            )

        total_ind_target = sum(t.assigned_target_amount for t in targets)
        total_team_target = sum(tt.aggregate_target for tt in team_targets)
        active_assigned_count = len([t for t in targets if t.assigned_target_amount > 0])

        return PeriodConfigurationDetailResponse(
            id=period.id,
            period_code=period.period_code,
            period_name=period.period_name,
            start_date=period.start_date,
            end_date=period.end_date,
            month=period.month,
            year=period.year,
            period_type=period.period_type,
            configuration_status=period.configuration_status,
            approval_status=period.approval_status,
            version=period.version,
            created_by=period.created_by,
            created_date=period.created_date,
            modified_date=period.modified_date,
            team_assignments=assignment_responses,
            target_allocations=target_responses,
            incentive_slabs=slab_responses,
            team_target_configs=team_target_responses,
            total_individual_target=total_ind_target,
            total_team_aggregate_target=total_team_target,
            targets_valid=abs(total_ind_target - total_team_target) < 1.0 or len(team_targets) == 0,
            active_assigned_employees_count=active_assigned_count,
        )

    @staticmethod
    def create_period(
        db: Session,
        req: PeriodConfigurationCreateRequest,
        changed_by: str = "Admin",
    ) -> PeriodConfigurationDetailResponse:
        if req.end_date < req.start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date cannot be earlier than start date",
            )

        code = req.period_code or f"{req.month}-{req.start_date.day:02d}-{req.end_date.day:02d}"
        existing = db.query(PeriodConfiguration).filter(PeriodConfiguration.period_code == code).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Period with code '{code}' already exists",
            )

        period = PeriodConfiguration(
            period_code=code,
            period_name=req.period_name,
            start_date=req.start_date,
            end_date=req.end_date,
            month=req.month,
            year=req.year,
            period_type=req.period_type,
            configuration_status="DRAFT",
            approval_status="DRAFT",
            version=1,
            created_by=changed_by,
        )
        db.add(period)
        db.flush()

        # Optional cloning from an existing period (filtering out inactive employees for the new period)
        if req.clone_from_period_id:
            source = db.query(PeriodConfiguration).filter(PeriodConfiguration.id == req.clone_from_period_id).first()
            if source:
                all_emps = {e.id: e for e in db.query(Employee).all()}
                hist_map = EligibilityService.build_history_map(db)

                for a in source.team_assignments:
                    emp = all_emps.get(a.employee_id)
                    if EligibilityService.is_employee_eligible_for_period(emp, req.start_date, req.end_date, hist_map):
                        db.add(
                            PeriodTeamAssignment(
                                period_id=period.id,
                                employee_id=a.employee_id,
                                team_id=a.team_id,
                                team_leader_id=a.team_leader_id,
                                team_name=a.team_name,
                                effective_start_date=req.start_date,
                                effective_end_date=req.end_date,
                            )
                        )
                for t in source.target_configurations:
                    emp = all_emps.get(t.employee_id)
                    if EligibilityService.is_employee_eligible_for_period(emp, req.start_date, req.end_date, hist_map):
                        db.add(
                            PeriodTargetConfiguration(
                                period_id=period.id,
                                employee_id=t.employee_id,
                                assigned_target_amount=t.assigned_target_amount,
                                target_type=t.target_type,
                                approval_status="DRAFT",
                            )
                        )
                for s in source.incentive_configurations:
                    db.add(
                        PeriodIncentiveConfiguration(
                            period_id=period.id,
                            incentive_type=s.incentive_type,
                            slab_label=s.slab_label,
                            assigned_target_amount=s.assigned_target_amount,
                            min_assigned_target=s.min_assigned_target,
                            max_assigned_target=s.max_assigned_target,
                            achievement_threshold=s.achievement_threshold,
                            incentive_amount=s.incentive_amount,
                            eligibility_conditions=s.eligibility_conditions,
                            calculation_method=s.calculation_method,
                            priority=s.priority,
                            active_status=s.active_status,
                        )
                    )
                for tt in source.team_target_configurations:
                    db.add(
                        PeriodTeamTargetConfiguration(
                            period_id=period.id,
                            team_id=tt.team_id,
                            team_leader_id=tt.team_leader_id,
                            team_name=tt.team_name,
                            aggregate_target=tt.aggregate_target,
                            team_leader_incentive=tt.team_leader_incentive,
                            eligibility_percentage=tt.eligibility_percentage,
                        )
                    )

        db.add(
            ConfigurationAuditHistory(
                entity_type="PeriodConfiguration",
                entity_id=str(period.id),
                previous_value=None,
                new_value=json.dumps({
                    "period_code": period.period_code,
                    "period_name": period.period_name,
                    "start_date": period.start_date.isoformat(),
                    "end_date": period.end_date.isoformat(),
                }),
                changed_by=changed_by,
                change_timestamp=datetime.utcnow(),
                reason="Created new period configuration",
            )
        )
        db.commit()
        return PeriodConfigService.get_period_detail(db, period.id)

    @staticmethod
    def save_period_configuration(
        db: Session,
        period_id: int,
        req: PeriodConfigurationBulkSaveRequest,
        changed_by: str = "Admin",
    ) -> PeriodConfigurationDetailResponse:
        period = db.query(PeriodConfiguration).filter(PeriodConfiguration.id == period_id).first()
        if not period:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Period not found")

        if period.approval_status == "APPROVED":
            # Controlled versioning: require reopening or automatically version-bump with audit reason
            period.version = (period.version or 1) + 1
            period.approval_status = "REOPENED"

        all_emps = {e.id: e for e in db.query(Employee).all()}
        all_teams = {t.id: t for t in db.query(Team).all()}
        hist_map = EligibilityService.build_history_map(db)

        if req.period_name:
            period.period_name = req.period_name
        if req.start_date:
            period.start_date = req.start_date
        if req.end_date:
            period.end_date = req.end_date

        # Validate & update team assignments
        if req.team_assignments is not None:
            for item in req.team_assignments:
                emp = all_emps.get(item.employee_id)
                EligibilityService.assert_employee_eligible_for_assignment(
                    db, emp, period.start_date, period.end_date, hist_map
                )
                leader = all_emps.get(item.team_leader_id)
                EligibilityService.assert_employee_eligible_for_assignment(
                    db, leader, period.start_date, period.end_date, hist_map
                )

            db.query(PeriodTeamAssignment).filter(PeriodTeamAssignment.period_id == period.id).delete()
            for item in req.team_assignments:
                team_obj = all_teams.get(item.team_id)
                db.add(
                    PeriodTeamAssignment(
                        period_id=period.id,
                        employee_id=item.employee_id,
                        team_id=item.team_id,
                        team_leader_id=item.team_leader_id,
                        team_name=item.team_name or (team_obj.name if team_obj else f"Team #{item.team_id}"),
                        effective_start_date=item.effective_start_date or period.start_date,
                        effective_end_date=item.effective_end_date or period.end_date,
                    )
                )

        # Validate & update target allocations
        if req.target_allocations is not None:
            for item in req.target_allocations:
                if item.assigned_target_amount > 0:
                    emp = all_emps.get(item.employee_id)
                    EligibilityService.assert_employee_eligible_for_assignment(
                        db, emp, period.start_date, period.end_date, hist_map
                    )

            db.query(PeriodTargetConfiguration).filter(PeriodTargetConfiguration.period_id == period.id).delete()
            for item in req.target_allocations:
                if item.assigned_target_amount >= 0:
                    db.add(
                        PeriodTargetConfiguration(
                            period_id=period.id,
                            employee_id=item.employee_id,
                            assigned_target_amount=float(item.assigned_target_amount),
                            target_type=item.target_type or "INDIVIDUAL_RM",
                            approval_status=period.approval_status,
                        )
                    )

        # Update incentive slabs
        if req.incentive_slabs is not None:
            db.query(PeriodIncentiveConfiguration).filter(PeriodIncentiveConfiguration.period_id == period.id).delete()
            for idx, item in enumerate(req.incentive_slabs):
                db.add(
                    PeriodIncentiveConfiguration(
                        period_id=period.id,
                        incentive_type=item.incentive_type.upper(),
                        slab_label=item.slab_label,
                        assigned_target_amount=item.assigned_target_amount,
                        min_assigned_target=item.min_assigned_target,
                        max_assigned_target=item.max_assigned_target,
                        achievement_threshold=float(item.achievement_threshold),
                        incentive_amount=float(item.incentive_amount),
                        eligibility_conditions=item.eligibility_conditions or "EXACT_TARGET_PCT",
                        calculation_method=item.calculation_method or "FIXED_SLAB",
                        priority=item.priority or (idx + 1),
                        active_status=item.active_status,
                    )
                )

        db.flush()

        # Recompute or save team target configs
        current_assignments = (
            db.query(PeriodTeamAssignment).filter(PeriodTeamAssignment.period_id == period.id).all()
        )
        current_targets = {
            t.employee_id: t.assigned_target_amount
            for t in db.query(PeriodTargetConfiguration).filter(PeriodTargetConfiguration.period_id == period.id).all()
        }

        if req.team_target_configs is not None:
            db.query(PeriodTeamTargetConfiguration).filter(PeriodTeamTargetConfiguration.period_id == period.id).delete()
            for item in req.team_target_configs:
                leader = all_emps.get(item.team_leader_id)
                EligibilityService.assert_employee_eligible_for_assignment(
                    db, leader, period.start_date, period.end_date, hist_map
                )
                team_obj = all_teams.get(item.team_id)
                team_members = [a for a in current_assignments if a.team_id == item.team_id]
                computed_agg = sum(current_targets.get(a.employee_id, 0.0) for a in team_members)
                agg_val = item.aggregate_target if (item.aggregate_target is not None and item.aggregate_target > 0) else computed_agg
                db.add(
                    PeriodTeamTargetConfiguration(
                        period_id=period.id,
                        team_id=item.team_id,
                        team_leader_id=item.team_leader_id,
                        team_name=item.team_name or (team_obj.name if team_obj else f"Team #{item.team_id}"),
                        aggregate_target=float(agg_val),
                        team_leader_incentive=float(item.team_leader_incentive),
                        eligibility_percentage=float(item.eligibility_percentage),
                    )
                )
        elif req.target_allocations is not None or req.team_assignments is not None:
            # Automatically sync aggregate team targets when member assignments or targets change
            existing_tts = (
                db.query(PeriodTeamTargetConfiguration)
                .filter(PeriodTeamTargetConfiguration.period_id == period.id)
                .all()
            )
            for tt in existing_tts:
                team_members = [a for a in current_assignments if a.team_id == tt.team_id]
                tt.aggregate_target = sum(current_targets.get(a.employee_id, 0.0) for a in team_members)

        db.add(
            ConfigurationAuditHistory(
                entity_type="PeriodConfigurationUpdate",
                entity_id=str(period.id),
                previous_value=json.dumps({"version": period.version - 1}),
                new_value=json.dumps({
                    "version": period.version,
                    "approval_status": period.approval_status,
                }),
                changed_by=changed_by,
                change_timestamp=datetime.utcnow(),
                reason=req.reason or f"Updated configuration for {period.period_name}",
            )
        )
        db.commit()
        return PeriodConfigService.get_period_detail(db, period.id)

    @staticmethod
    def approve_and_publish_period(
        db: Session,
        period_id: int,
        reason: Optional[str] = None,
        changed_by: str = "Admin",
    ) -> PeriodConfigurationDetailResponse:
        period = db.query(PeriodConfiguration).filter(PeriodConfiguration.id == period_id).first()
        if not period:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Period not found")

        prev_status = {
            "configuration_status": period.configuration_status,
            "approval_status": period.approval_status,
            "version": period.version,
        }
        period.configuration_status = "ACTIVE"
        period.approval_status = "APPROVED"
        for t in period.target_configurations:
            t.approval_status = "APPROVED"

        db.add(
            ConfigurationAuditHistory(
                entity_type="PeriodApproval",
                entity_id=str(period.id),
                previous_value=json.dumps(prev_status),
                new_value=json.dumps({
                    "configuration_status": "ACTIVE",
                    "approval_status": "APPROVED",
                    "version": period.version,
                }),
                changed_by=changed_by,
                change_timestamp=datetime.utcnow(),
                reason=reason or f"Approved and published {period.period_name} (v{period.version})",
            )
        )
        db.commit()
        return PeriodConfigService.get_period_detail(db, period.id)

    @staticmethod
    def reopen_period(
        db: Session,
        period_id: int,
        reason: Optional[str] = None,
        changed_by: str = "Admin",
    ) -> PeriodConfigurationDetailResponse:
        period = db.query(PeriodConfiguration).filter(PeriodConfiguration.id == period_id).first()
        if not period:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Period not found")

        prev_status = {
            "approval_status": period.approval_status,
            "version": period.version,
        }
        period.approval_status = "REOPENED"
        period.version = (period.version or 1) + 1

        db.add(
            ConfigurationAuditHistory(
                entity_type="PeriodReopen",
                entity_id=str(period.id),
                previous_value=json.dumps(prev_status),
                new_value=json.dumps({
                    "approval_status": "REOPENED",
                    "version": period.version,
                }),
                changed_by=changed_by,
                change_timestamp=datetime.utcnow(),
                reason=reason or f"Reopened {period.period_name} for controlled editing (v{period.version})",
            )
        )
        db.commit()
        return PeriodConfigService.get_period_detail(db, period.id)

    @staticmethod
    def get_employees_for_period_admin(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        all_emps = db.query(Employee).order_by(Employee.name.asc()).all()
        hist_map = EligibilityService.build_history_map(db)
        p_start = start_date or date.today().replace(day=1)
        p_end = end_date or date.today()

        active_list = []
        inactive_list = []
        for e in all_emps:
            if (e.role or "").upper() == "GUEST" or (e.emp_id or "") == "MMSR00":
                continue
            is_elig = EligibilityService.is_employee_eligible_for_period(e, p_start, p_end, hist_map)
            item = {
                "id": e.id,
                "emp_id": e.emp_id,
                "name": e.name,
                "email": e.email,
                "designation": e.designation,
                "department": e.department,
                "reporting_manager": e.reporting_manager,
                "joining_date": e.joining_date,
                "employment_end_date": e.employment_end_date,
                "deactivation_effective_date": e.deactivation_effective_date,
                "status": "Active" if is_elig else "Inactive",
                "db_status": e.status,
                "is_team_leader": bool(e.is_team_leader),
            }
            if is_elig:
                active_list.append(item)
            else:
                inactive_list.append(item)

        teams = [
            {
                "id": t.id,
                "name": t.name,
                "leader_id": t.leader_id,
                "is_active": t.is_active,
            }
            for t in db.query(Team).order_by(Team.id.asc()).all()
        ]

        return {
            "active_employees": active_list,
            "inactive_employees": inactive_list,
            "teams": teams,
        }

    @staticmethod
    def list_audit_history(
        db: Session,
        limit: int = 100,
    ) -> List[ConfigurationAuditHistoryResponse]:
        rows = (
            db.query(ConfigurationAuditHistory)
            .order_by(ConfigurationAuditHistory.change_timestamp.desc(), ConfigurationAuditHistory.id.desc())
            .limit(limit)
            .all()
        )
        return [
            ConfigurationAuditHistoryResponse(
                id=r.id,
                entity_type=r.entity_type,
                entity_id=r.entity_id,
                previous_value=r.previous_value,
                new_value=r.new_value,
                changed_by=r.changed_by,
                change_timestamp=r.change_timestamp,
                reason=r.reason,
            )
            for r in rows
        ]

    @staticmethod
    def list_employment_history(
        db: Session,
        employee_id: Optional[int] = None,
    ) -> List[EmployeeEmploymentHistoryResponse]:
        all_emps = {e.id: e.name for e in db.query(Employee).all()}
        q = db.query(EmployeeEmploymentHistory)
        if employee_id:
            q = q.filter(EmployeeEmploymentHistory.employee_id == employee_id)
        rows = q.order_by(EmployeeEmploymentHistory.effective_date.desc(), EmployeeEmploymentHistory.id.desc()).all()
        return [
            EmployeeEmploymentHistoryResponse(
                id=r.id,
                employee_id=r.employee_id,
                employee_name=all_emps.get(r.employee_id),
                employment_start_date=r.employment_start_date,
                employment_end_date=r.employment_end_date,
                employment_status=r.employment_status,
                effective_date=r.effective_date,
                reactivation_history=r.reactivation_history,
                reason=r.reason,
                changed_by=r.changed_by,
                created_at=r.created_at,
            )
            for r in rows
        ]

