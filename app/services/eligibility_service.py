"""
Employee Eligibility & Effective-Dated Employment Status Service.

Rules:
- Never deletes employee records or historical associations.
- Evaluates employee eligibility strictly from effective-dated employment records
  (`employee_employment_history` + `employees.joining_date`, `employment_end_date`, `deactivation_effective_date`).
- Inactive employees are excluded from active dropdowns, prevented from new team/target assignments,
  and excluded from all performance/target/incentive calculations on or after their effective deactivation date.
- Historical reporting prior to an employee's employment_end_date remains 100% preserved.
"""

import json
from datetime import date, datetime
from typing import Dict, List, Optional, Set
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.period_config import (
    EmployeeEmploymentHistory,
    ConfigurationAuditHistory,
    PeriodEmployeeExclusion,
)


def _parse_iso_date(val: Optional[str]) -> Optional[date]:
    if not val:
        return None
    try:
        return date.fromisoformat(str(val).strip()[:10])
    except ValueError:
        return None


class EligibilityService:
    @staticmethod
    def build_history_map(
        db: Session,
    ) -> Dict[int, List[EmployeeEmploymentHistory]]:
        rows = (
            db.query(EmployeeEmploymentHistory)
            .order_by(EmployeeEmploymentHistory.effective_date.asc(), EmployeeEmploymentHistory.id.asc())
            .all()
        )
        hist_map: Dict[int, List[EmployeeEmploymentHistory]] = {}
        for r in rows:
            hist_map.setdefault(r.employee_id, []).append(r)
        return hist_map

    @staticmethod
    def get_effective_bounds(
        emp: Employee,
        history_rows: Optional[List[EmployeeEmploymentHistory]] = None,
    ) -> tuple[Optional[date], Optional[date], Optional[date]]:
        """
        Returns (start_date, end_date, reactivation_date) for an employee.
        """
        start_dt = _parse_iso_date(getattr(emp, "joining_date", None))
        end_dt = _parse_iso_date(getattr(emp, "employment_end_date", None))
        deact_dt = _parse_iso_date(getattr(emp, "deactivation_effective_date", None))
        react_dt: Optional[date] = None

        if history_rows:
            for h in history_rows:
                if h.employment_start_date and (start_dt is None or h.employment_start_date < start_dt):
                    start_dt = h.employment_start_date
                if (h.employment_status or "").upper() == "INACTIVE":
                    if h.employment_end_date:
                        end_dt = h.employment_end_date
                    if h.effective_date:
                        deact_dt = h.effective_date
                    react_dt = None
                elif (h.employment_status or "").upper() == "ACTIVE" and deact_dt and h.effective_date > deact_dt:
                    # Reactivated by authorised admin after previous deactivation
                    react_dt = h.effective_date
                    end_dt = h.employment_end_date
                    deact_dt = None

        if end_dt is None and deact_dt is not None:
            from datetime import timedelta
            end_dt = deact_dt - timedelta(days=1)

        return start_dt, end_dt, react_dt

    @staticmethod
    def build_period_exclusion_map(
        db: Session,
    ) -> Dict[int, Set[int]]:
        """
        Returns a mapping of period_id -> set of employee_ids excluded from that period.
        """
        rows = db.query(PeriodEmployeeExclusion).all()
        excl_map: Dict[int, Set[int]] = {}
        for r in rows:
            excl_map.setdefault(r.period_id, set()).add(r.employee_id)
        return excl_map

    @staticmethod
    def is_employee_excluded_from_period(
        emp_id: Optional[int],
        period_id: Optional[int],
        exclusion_map: Optional[Dict[int, Set[int]]] = None,
    ) -> bool:
        if emp_id is None or period_id is None or not exclusion_map:
            return False
        return emp_id in exclusion_map.get(period_id, set())

    @staticmethod
    def is_employee_active_on_date(
        emp: Optional[Employee],
        check_date: date,
        history_map: Optional[Dict[int, List[EmployeeEmploymentHistory]]] = None,
        period_id: Optional[int] = None,
        exclusion_map: Optional[Dict[int, Set[int]]] = None,
    ) -> bool:
        """
        Checks if `emp` was actively employed on `check_date` and not excluded from `period_id`.
        """
        if not emp:
            return False

        if EligibilityService.is_employee_excluded_from_period(emp.id, period_id, exclusion_map):
            return False

        emp_status_upper = (emp.status or "ACTIVE").upper()
        if emp_status_upper in ("DELETED", "TERMINATED"):
            return False

        hist_rows = history_map.get(emp.id) if history_map else None
        start_dt, end_dt, react_dt = EligibilityService.get_effective_bounds(emp, hist_rows)

        if start_dt and check_date < start_dt:
            return False

        if end_dt and check_date > end_dt:
            if react_dt and check_date >= react_dt:
                return True
            return False

        # If employee is marked INACTIVE without an explicit end_date/history, they are inactive
        if emp_status_upper != "ACTIVE" and end_dt is None and not hist_rows:
            return False

        return True

    @staticmethod
    def is_employee_eligible_for_period(
        emp: Optional[Employee],
        period_start: date,
        period_end: date,
        history_map: Optional[Dict[int, List[EmployeeEmploymentHistory]]] = None,
        period_id: Optional[int] = None,
        exclusion_map: Optional[Dict[int, Set[int]]] = None,
    ) -> bool:
        """
        Checks if `emp` is eligible to participate in the performance period [period_start, period_end].
        An employee is eligible if:
        - They are not explicitly excluded from `period_id` via `period_employee_exclusions`
        - They joined on or before `period_end`
        - Their employment did not end before `period_start` (i.e. not deactivated on or before `period_start`)
        """
        if not emp:
            return False

        if EligibilityService.is_employee_excluded_from_period(emp.id, period_id, exclusion_map):
            return False

        emp_status_upper = (emp.status or "ACTIVE").upper()
        if emp_status_upper in ("DELETED", "TERMINATED"):
            return False

        hist_rows = history_map.get(emp.id) if history_map else None
        start_dt, end_dt, react_dt = EligibilityService.get_effective_bounds(emp, hist_rows)

        if start_dt and start_dt > period_end:
            return False

        if end_dt and end_dt < period_start:
            if react_dt and react_dt <= period_end:
                return True
            return False

        if emp_status_upper != "ACTIVE" and end_dt is None and not hist_rows:
            return False

        return True

    @staticmethod
    def is_currently_active(emp: Optional[Employee]) -> bool:
        """
        Checks if an employee is currently active for dropdowns and new assignments.
        """
        if not emp:
            return False
        if (emp.status or "").upper() != "ACTIVE":
            return False
        end_dt = _parse_iso_date(getattr(emp, "employment_end_date", None))
        deact_dt = _parse_iso_date(getattr(emp, "deactivation_effective_date", None))
        today = date.today()
        if deact_dt and deact_dt <= today:
            return False
        if end_dt and end_dt < today:
            return False
        return True

    @staticmethod
    def assert_employee_eligible_for_assignment(
        db: Session,
        emp: Optional[Employee],
        period_start: date,
        period_end: date,
        history_map: Optional[Dict[int, List[EmployeeEmploymentHistory]]] = None,
        period_id: Optional[int] = None,
        exclusion_map: Optional[Dict[int, Set[int]]] = None,
    ) -> None:
        if not emp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found",
            )
        if not EligibilityService.is_employee_eligible_for_period(
            emp, period_start, period_end, history_map,
            period_id=period_id, exclusion_map=exclusion_map,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Employee '{emp.name}' is INACTIVE for period {period_start} to {period_end} "
                    f"(employment_end_date={emp.employment_end_date}, status={emp.status}) "
                    "and cannot be assigned to teams or targets."
                ),
            )

    @staticmethod
    def change_employee_employment_status(
        db: Session,
        emp: Employee,
        new_status: str,
        effective_date: date,
        employment_end_date: Optional[date] = None,
        reason: Optional[str] = None,
        changed_by: str = "Admin",
    ) -> Employee:
        """
        Deactivates or reactivates an employee using effective-dated employment history
        without deleting any employee or historical records.
        """
        normalized_status = new_status.strip().upper()
        if normalized_status not in ("ACTIVE", "INACTIVE"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employment status must be ACTIVE or INACTIVE",
            )

        prev_state = {
            "status": emp.status,
            "employment_end_date": emp.employment_end_date,
            "deactivation_effective_date": emp.deactivation_effective_date,
        }

        start_dt = _parse_iso_date(emp.joining_date) or date(2024, 1, 1)

        if normalized_status == "INACTIVE":
            from datetime import timedelta
            eff_end = employment_end_date or (effective_date - timedelta(days=1))
            emp.status = "INACTIVE"
            emp.employment_end_date = eff_end.isoformat()
            emp.deactivation_effective_date = effective_date.isoformat()

            db.add(
                EmployeeEmploymentHistory(
                    employee_id=emp.id,
                    employment_start_date=start_dt,
                    employment_end_date=eff_end,
                    employment_status="INACTIVE",
                    effective_date=effective_date,
                    reason=reason or f"Deactivated effective {effective_date.isoformat()}",
                    changed_by=changed_by,
                )
            )
        else:
            # Controlled Reactivation by authorised administrator
            reactivation_meta = json.dumps({
                "previous_end_date": emp.employment_end_date,
                "previous_deactivation_date": emp.deactivation_effective_date,
                "reactivated_effective_date": effective_date.isoformat(),
                "reactivated_by": changed_by,
                "reason": reason,
            })
            emp.status = "ACTIVE"
            emp.employment_end_date = None
            emp.deactivation_effective_date = None

            db.add(
                EmployeeEmploymentHistory(
                    employee_id=emp.id,
                    employment_start_date=start_dt,
                    employment_end_date=None,
                    employment_status="ACTIVE",
                    effective_date=effective_date,
                    reactivation_history=reactivation_meta,
                    reason=reason or f"Reactivated effective {effective_date.isoformat()}",
                    changed_by=changed_by,
                )
            )

        db.add(
            ConfigurationAuditHistory(
                entity_type="EmployeeStatus",
                entity_id=str(emp.id),
                previous_value=json.dumps(prev_state),
                new_value=json.dumps({
                    "status": emp.status,
                    "employment_end_date": emp.employment_end_date,
                    "deactivation_effective_date": emp.deactivation_effective_date,
                }),
                changed_by=changed_by,
                change_timestamp=datetime.utcnow(),
                reason=reason or f"Changed status to {normalized_status} effective {effective_date.isoformat()}",
            )
        )

        db.commit()
        db.refresh(emp)
        return emp

