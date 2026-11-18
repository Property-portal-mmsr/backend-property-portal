"""
Analytics Service — Database-Driven Business Logic for the Performance Dashboard.

All period definitions, employee eligibility dates, team assignments,
Team Leader assignments, individual targets, RM incentive slabs, and
Team Leader incentive rules are loaded dynamically from MySQL via:
- EligibilityService
- CalculationService
- PeriodConfigService
"""

import calendar
import difflib
import logging
import re
from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.employee_monthly_target import EmployeeMonthlyTarget
from app.models.period_config import (
    PeriodConfiguration,
    PeriodTeamAssignment,
    PeriodTeamTargetConfiguration,
)
from app.services.google_sheet_service import SheetRecord, fetch_sheet_records
from app.services.eligibility_service import EligibilityService
from app.services.calculation_service import (
    CalculationService,
    calculate_achievement_pct,
    calculate_status,
)
from app.schemas.analytics import (
    DailyRevenueItem,
    DailyRevenueEmployeeItem,
    DailyRevenueDrilldownResponse,
    DashboardResponse,
    KPIResponse,
    LeaderboardItem,
    MonthComparisonItem,
    MonthlyRevenueItem,
    PerformanceTableItem,
    PrevCurrentMonthResponse,
    TeamLeaderIncentiveTrackerItem,
    TeamPerformanceChartItem,
    EmployeeFilterOption,
    PeriodBreakdownItem,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# RM Name fuzzy matching (for joining Google Sheet rows to DB Employee records)
# ---------------------------------------------------------------------------

def _normalize_name(name: str) -> str:
    return " ".join(name.lower().split())


def _names_match(sheet_name: str, db_name: str) -> bool:
    sn = _normalize_name(sheet_name)
    dn = _normalize_name(db_name)

    if sn == dn:
        return True
    if sn in dn or dn in sn:
        return True

    s_words = sn.split()
    d_words = dn.split()
    if not d_words or not s_words:
        return False

    longest_d = max(d_words, key=len)
    if len(longest_d) >= 4:
        matches = difflib.get_close_matches(longest_d, s_words, n=1, cutoff=0.8)
        if matches:
            return True

    return False


def _build_rm_map(employees: List[Employee]) -> Dict[str, Employee]:
    return {_normalize_name(e.name): e for e in employees if e.name}


def _resolve_rm(sheet_rm: str, rm_map: Dict[str, Employee]) -> Optional[Employee]:
    sn = _normalize_name(sheet_rm)
    best_emp = None
    best_rank = None
    for db_name_norm, emp in rm_map.items():
        if not _names_match(sn, db_name_norm):
            continue
        if sn == db_name_norm:
            rank = (3, len(db_name_norm))
        elif db_name_norm in sn:
            rank = (2, len(db_name_norm))
        elif sn in db_name_norm:
            rank = (1, -abs(len(db_name_norm) - len(sn)))
        else:
            rank = (0, -abs(len(db_name_norm) - len(sn)))
        if best_rank is None or rank > best_rank:
            best_rank = rank
            best_emp = emp
    return best_emp


def _record_month(r: SheetRecord) -> str:
    return r.date.strftime("%Y-%m")


def is_eligible_dropdown_designation(designation: Optional[str]) -> bool:
    """
    Matches employee designations for the Performance Analytics filter dropdown:
    - Founder
    - Senior Relationship Manager
    - R.M / Relationship Manager
    - City Sales & Ops Manager
    - City Manager
    """
    if not designation:
        return False
    norm = re.sub(r"[.\-_]", " ", designation.lower())
    norm = re.sub(r"&", " and ", norm)
    norm = re.sub(r"\b(mgr|mngr)\b", "manager", norm)
    norm = re.sub(r"\b(sr)\b", "senior", norm)
    norm = re.sub(r"\b(ops|oper)\b", "operations", norm)
    norm = re.sub(r"\br\s+m\b", "rm", norm)
    norm = re.sub(r"\s+", " ", norm).strip()

    return norm in (
        "founder",
        "senior relationship manager",
        "senior rm",
        "rm",
        "relationship manager",
        "city sales and operations manager",
        "city sales operations manager",
        "city manager",
    )


def _build_leaderboard_from_rows(rows: List[PerformanceTableItem]) -> List[LeaderboardItem]:
    eligible_for_lb = [r for r in rows if r.revenue > 0]
    sorted_lb = sorted(
        eligible_for_lb,
        key=lambda x: (x.achievement_pct, x.revenue),
        reverse=True,
    )
    leaderboard: List[LeaderboardItem] = []
    current_rank = 0
    prev_ach = None
    for item in sorted_lb:
        if prev_ach is None or item.achievement_pct != prev_ach:
            current_rank += 1
            prev_ach = item.achievement_pct
        if current_rank > 3:
            break
        leaderboard.append(
            LeaderboardItem(
                rm_name=item.rm_name,
                revenue=item.revenue,
                beds_sold=item.beds_sold,
                target=item.monthly_target,
                achievement_pct=item.achievement_pct,
                remaining_target=item.remaining_target,
                incentive=item.incentive,
                is_team_leader=item.is_team_leader,
            )
        )
    return leaderboard


def build_dashboard(
    db: Session,
    month: Optional[str] = None,
    rm_name: Optional[str] = None,
    employee_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    period_code: Optional[str] = None,
    period_id: Optional[int] = None,
) -> DashboardResponse:
    """
    Master function: fetches sheet data, joins with Employee DB using effective-dated
    eligibility and database-driven PeriodConfiguration records, and computes all dashboard sections.
    """
    # 1. Fetch raw sheet records
    raw_records = fetch_sheet_records()

    # 2. Fetch all employees from DB (including historical/inactive employees so historical months work via effective dates)
    all_db_employees: List[Employee] = db.query(Employee).all()
    all_employees_map: Dict[int, Employee] = {e.id: e for e in all_db_employees}
    hist_map = EligibilityService.build_history_map(db)

    rm_map = _build_rm_map(all_db_employees)

    # 3. Enrich sheet records with matched Employee
    enriched: List[Tuple[SheetRecord, Optional[Employee]]] = []
    for rec in raw_records:
        emp = _resolve_rm(rec.rm_name, rm_map)
        enriched.append((rec, emp))

    # 4. Collect available months (including months from PeriodConfiguration and sheet records)
    sheet_months = {_record_month(r) for r, _ in enriched}
    db_period_months = {
        p.month
        for p in db.query(PeriodConfiguration)
        .filter(PeriodConfiguration.configuration_status == "ACTIVE")
        .all()
    }
    all_months = sorted(sheet_months | db_period_months, reverse=True)
    FROZEN_REPORTING_PERIODS = {"2026-04", "2026-05", "2026-06", "2026-07", "2026-08"}
    available_months = [m for m in all_months if m >= "2026-09" and m not in FROZEN_REPORTING_PERIODS]

    # 5. Active RM Dropdown Filter:
    # Only currently active employees (excludes Raj Singh and Sanjota who are INACTIVE effective 2026-11-01)
    currently_active_employees = [
        e for e in all_db_employees
        if EligibilityService.is_currently_active(e)
        and is_eligible_dropdown_designation(e.designation)
    ]
    currently_active_employees.sort(key=lambda x: (x.name or "").lower())
    available_employee_options: List[EmployeeFilterOption] = [
        EmployeeFilterOption(id=e.id, name=e.name)
        for e in currently_active_employees
        if e.id is not None and e.name
    ]

    # 6. Determine reference month context
    if month:
        try:
            reference_date = datetime.strptime(month + "-01", "%Y-%m-%d").date()
        except ValueError:
            reference_date = date.today().replace(day=1)
    elif start_date:
        reference_date = start_date.replace(day=1)
    elif period_code:
        p_obj = db.query(PeriodConfiguration).filter(PeriodConfiguration.period_code == period_code).first()
        reference_date = p_obj.start_date.replace(day=1) if p_obj else date.today().replace(day=1)
    elif period_id:
        p_obj = db.query(PeriodConfiguration).filter(PeriodConfiguration.id == period_id).first()
        reference_date = p_obj.start_date.replace(day=1) if p_obj else date.today().replace(day=1)
    else:
        reference_date = date.today().replace(day=1)

    current_month_str = reference_date.strftime("%Y-%m")
    if reference_date.month == 1:
        prev_month_date = reference_date.replace(year=reference_date.year - 1, month=12)
    else:
        prev_month_date = reference_date.replace(month=reference_date.month - 1)
    prev_month_str = prev_month_date.strftime("%Y-%m")

    # 7. Resolve applicable PeriodConfiguration(s) from MySQL
    matched_periods, available_periods = CalculationService.resolve_periods_for_query(
        db=db,
        month=month,
        start_date=start_date,
        end_date=end_date,
        period_code=period_code,
        period_id=period_id,
    )

    # If "All Months" (no month, start_date, end_date, period_code, period_id), resolve periods for current_month_str for target/tracker
    if not matched_periods and not month and not start_date and not end_date and not period_code and not period_id:
        matched_periods, available_periods = CalculationService.resolve_periods_for_query(
            db=db,
            month=current_month_str,
        )

    period_breakdowns: List[PeriodBreakdownItem] = []
    if matched_periods:
        for p in matched_periods:
            b_item = CalculationService.compute_single_period(
                db=db,
                period=p,
                enriched_records=enriched,
                all_employees_map=all_employees_map,
                hist_map=hist_map,
                employee_id_filter=employee_id,
                rm_name_filter=rm_name,
                custom_start=start_date,
                custom_end=end_date,
                persist_snapshot=(start_date is None and end_date is None),
            )
            period_breakdowns.append(b_item)

        kpis, performance_rows, team_leader_tracker = CalculationService.combine_period_breakdowns(
            period_breakdowns
        )
    else:
        # Generic fallback for any future/unconfigured month (e.g. December 2026 before period creation)
        # Uses EmployeeMonthlyTarget and effective-dated EligibilityService (still excluding inactive employees!)
        y_val, m_val = map(int, current_month_str.split("-"))
        _, last_day = calendar.monthrange(y_val, m_val)
        p_start = start_date or date(y_val, m_val, 1)
        p_end = end_date or date(y_val, m_val, last_day)
        month_name = calendar.month_name[m_val]

        elig_ids = {
            e_id
            for e_id, emp in all_employees_map.items()
            if EligibilityService.is_employee_eligible_for_period(emp, p_start, p_end, hist_map)
        }

        mt_rows = (
            db.query(EmployeeMonthlyTarget)
            .filter(
                EmployeeMonthlyTarget.month == month_name,
                EmployeeMonthlyTarget.year == y_val,
            )
            .all()
        )
        tgt_map = {t.employee_id: float(t.target) for t in mt_rows if t.employee_id in elig_ids}

        emp_rev: Dict[int, float] = defaultdict(float)
        emp_beds: Dict[int, float] = defaultdict(float)
        for rec, emp in enriched:
            if rec.date < p_start or rec.date > p_end:
                continue
            if not emp or emp.id not in elig_ids:
                continue
            if not EligibilityService.is_employee_active_on_date(emp, rec.date, hist_map):
                continue
            if employee_id and emp.id != employee_id:
                continue
            if rm_name and rm_name.lower() not in (emp.name or "").lower():
                continue
            emp_rev[emp.id] += rec.revenue
            emp_beds[emp.id] += rec.key_count

        rel_ids = ({eid for eid, t in tgt_map.items() if t > 0} | {eid for eid, r in emp_rev.items() if r > 0}) & elig_ids
        if employee_id:
            rel_ids = {eid for eid in rel_ids if eid == employee_id}
        if rm_name:
            rel_ids = {eid for eid in rel_ids if rm_name.lower() in (all_employees_map[eid].name or "").lower()}

        tot_rev = sum(emp_rev.get(eid, 0.0) for eid in rel_ids)
        tot_beds = sum(emp_beds.get(eid, 0.0) for eid in rel_ids)
        tot_tgt = sum(tgt_map.get(eid, 0.0) for eid in rel_ids)

        performance_rows = []
        for eid in rel_ids:
            rev = emp_rev.get(eid, 0.0)
            if rev <= 0:
                continue
            emp = all_employees_map[eid]
            tgt = tgt_map.get(eid, 0.0)
            ach = calculate_achievement_pct(rev, tgt)
            performance_rows.append(
                PerformanceTableItem(
                    rm_name=emp.name,
                    beds_sold=emp_beds.get(eid, 0.0),
                    revenue=rev,
                    monthly_target=tgt,
                    achievement_pct=ach,
                    remaining_target=max(0.0, tgt - rev),
                    incentive=0.0,
                    status=calculate_status(ach),
                    is_team_leader=bool(emp.is_team_leader),
                    team_leader_name=emp.reporting_manager,
                )
            )
        performance_rows.sort(key=lambda x: x.revenue, reverse=True)
        team_leader_tracker = []
        kpis = KPIResponse(
            total_revenue=tot_rev,
            beds_sold=tot_beds,
            overall_target=tot_tgt,
            achievement_pct=calculate_achievement_pct(tot_rev, tot_tgt),
            active_rms=len(rel_ids),
            total_rm_incentives=0.0,
            total_tl_incentives=0.0,
            total_incentives=0.0,
        )

    # 8. If "All Months" view (month is None and no date/period filter), aggregate revenue & beds across all eligible months
    if not month and not start_date and not end_date and not period_code and not period_id:
        all_periods = (
            db.query(PeriodConfiguration)
            .filter(PeriodConfiguration.configuration_status == "ACTIVE")
            .order_by(PeriodConfiguration.start_date.asc())
            .all()
        )
        all_b_items = [
            CalculationService.compute_single_period(
                db=db,
                period=p,
                enriched_records=enriched,
                all_employees_map=all_employees_map,
                hist_map=hist_map,
                employee_id_filter=employee_id,
                rm_name_filter=rm_name,
                persist_snapshot=False,
            )
            for p in all_periods
        ]
        if all_b_items:
            all_kpis, all_rows, _ = CalculationService.combine_period_breakdowns(all_b_items)
            # Keep non-cumulative current period overall_target as required by test 13
            kpis = KPIResponse(
                total_revenue=all_kpis.total_revenue,
                beds_sold=all_kpis.beds_sold,
                overall_target=kpis.overall_target,
                achievement_pct=calculate_achievement_pct(all_kpis.total_revenue, kpis.overall_target),
                active_rms=kpis.active_rms,
                total_rm_incentives=all_kpis.total_rm_incentives,
                total_tl_incentives=all_kpis.total_tl_incentives,
                total_incentives=all_kpis.total_incentives,
            )
            performance_rows = [r for r in all_rows if r.revenue > 0]

    # 9. Monthly Revenue Chart (all months, respecting effective-dated employee eligibility)
    monthly_map: Dict[str, float] = defaultdict(float)
    for rec, emp in enriched:
        if emp and not EligibilityService.is_employee_active_on_date(emp, rec.date, hist_map):
            continue
        if employee_id and (not emp or emp.id != employee_id):
            continue
        if rm_name:
            rm_lower = rm_name.strip().lower()
            name_to_check = emp.name.lower() if emp and emp.name else rec.rm_name.lower()
            if rm_lower not in name_to_check and name_to_check not in rm_lower:
                continue
        monthly_map[_record_month(rec)] += rec.revenue

    monthly_revenue = [
        MonthlyRevenueItem(month=m, revenue=r)
        for m, r in sorted(monthly_map.items())
    ]

    # Determine active period day-of-month bounds when a specific period or date range is selected
    period_start_day: Optional[int] = None
    period_end_day: Optional[int] = None
    if (period_code or period_id) and len(matched_periods) == 1:
        period_start_day = matched_periods[0].start_date.day
        period_end_day = matched_periods[0].end_date.day
    elif start_date or end_date:
        if start_date and start_date.strftime("%Y-%m") == current_month_str:
            period_start_day = start_date.day
        if end_date and end_date.strftime("%Y-%m") == current_month_str:
            period_end_day = end_date.day

    # 10. Daily Revenue Chart (for current/selected month or period)
    daily_map: Dict[str, float] = defaultdict(float)
    for rec, emp in enriched:
        if _record_month(rec) != current_month_str:
            continue
        if start_date and rec.date < start_date:
            continue
        if end_date and rec.date > end_date:
            continue
        if (period_code or period_id) and len(matched_periods) == 1:
            if rec.date < matched_periods[0].start_date or rec.date > matched_periods[0].end_date:
                continue
        if period_start_day is not None and rec.date.day < period_start_day:
            continue
        if period_end_day is not None and rec.date.day > period_end_day:
            continue
        if emp and not EligibilityService.is_employee_active_on_date(emp, rec.date, hist_map):
            continue
        if employee_id and (not emp or emp.id != employee_id):
            continue
        if rm_name:
            rm_lower = rm_name.strip().lower()
            name_to_check = emp.name.lower() if emp and emp.name else rec.rm_name.lower()
            if rm_lower not in name_to_check and name_to_check not in rm_lower:
                continue
        daily_map[rec.date.strftime("%Y-%m-%d")] += rec.revenue

    daily_revenue = [
        DailyRevenueItem(date=d, revenue=r)
        for d, r in sorted(daily_map.items())
    ]

    # 10b. Previous Month Daily Revenue (filtered to corresponding period day-of-month range if selected)
    prev_daily_map: Dict[str, float] = defaultdict(float)
    for rec, emp in enriched:
        if _record_month(rec) != prev_month_str:
            continue
        if period_start_day is not None and rec.date.day < period_start_day:
            continue
        if period_end_day is not None and rec.date.day > period_end_day:
            continue
        if emp and not EligibilityService.is_employee_active_on_date(emp, rec.date, hist_map):
            continue
        if employee_id and (not emp or emp.id != employee_id):
            continue
        if rm_name:
            rm_lower = rm_name.strip().lower()
            name_to_check = emp.name.lower() if emp and emp.name else rec.rm_name.lower()
            if rm_lower not in name_to_check and name_to_check not in rm_lower:
                continue
        prev_daily_map[rec.date.strftime("%Y-%m-%d")] += rec.revenue

    prev_daily_revenue = [
        DailyRevenueItem(date=d, revenue=r)
        for d, r in sorted(prev_daily_map.items())
    ]

    # 11. Previous vs Current Month Comparison
    def _build_month_comparison(m_str: str) -> Optional[MonthComparisonItem]:
        m_periods, _ = CalculationService.resolve_periods_for_query(db=db, month=m_str)
        if not m_periods:
            return None
        b_list = [
            CalculationService.compute_single_period(
                db=db,
                period=p,
                enriched_records=enriched,
                all_employees_map=all_employees_map,
                hist_map=hist_map,
                employee_id_filter=employee_id,
                rm_name_filter=rm_name,
                persist_snapshot=False,
            )
            for p in m_periods
        ]
        m_kpis, _, _ = CalculationService.combine_period_breakdowns(b_list)
        if m_kpis.total_revenue <= 0 and m_kpis.beds_sold <= 0:
            return None
        return MonthComparisonItem(
            month=m_str,
            revenue=m_kpis.total_revenue,
            beds_sold=m_kpis.beds_sold,
            achievement_pct=m_kpis.achievement_pct,
            incentive=m_kpis.total_incentives,
        )

    prev_current = PrevCurrentMonthResponse(
        previous=_build_month_comparison(prev_month_str),
        current=_build_month_comparison(current_month_str),
    )

    # 12. Leaderboard
    leaderboard = _build_leaderboard_from_rows(performance_rows)

    # 13. Team Performance Chart
    team_performance_chart = [
        TeamPerformanceChartItem(
            team_name=t.team_name,
            revenue=t.team_revenue,
            beds=t.team_beds,
            team_leader_revenue=t.team_leader_revenue,
            team_member_revenue=t.team_member_revenue,
            overall_team_revenue=t.team_revenue,
        )
        for t in team_leader_tracker
    ]

    selected_code = period_code
    if not selected_code and len(matched_periods) == 1:
        selected_code = matched_periods[0].period_code

    return DashboardResponse(
        kpis=kpis,
        monthly_revenue=monthly_revenue,
        daily_revenue=daily_revenue,
        prev_daily_revenue=prev_daily_revenue,
        prev_current_month=prev_current,
        leaderboard=leaderboard,
        performance_table=performance_rows,
        team_leader_tracker=team_leader_tracker,
        team_performance=team_performance_chart,
        available_months=available_months,
        available_rms=available_employee_options,
        available_employees=available_employee_options,
        available_periods=available_periods,
        selected_period_code=selected_code,
        period_breakdowns=period_breakdowns,
    )


def build_daily_revenue_drilldown(
    db: Session,
    target_date: date,
    month: Optional[str] = None,
    period_code: Optional[str] = None,
    period_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    rm_name: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> DailyRevenueDrilldownResponse:
    """
    Computes the employee-wise revenue breakdown for a single selected date (`target_date`).
    Enforces period compatibility and effective-dated employee eligibility.
    """
    if month and month != "All Months" and target_date.strftime("%Y-%m") != month:
        raise ValueError(
            f"Selected date {target_date.isoformat()} does not belong to selected month {month}"
        )

    if start_date and target_date < start_date:
        raise ValueError(
            f"Selected date {target_date.isoformat()} is earlier than start date {start_date.isoformat()}"
        )

    if end_date and target_date > end_date:
        raise ValueError(
            f"Selected date {target_date.isoformat()} is later than end date {end_date.isoformat()}"
        )

    # Validate against explicitly selected period (First Half vs Second Half)
    explicit_period: Optional[PeriodConfiguration] = None
    if period_id is not None:
        explicit_period = (
            db.query(PeriodConfiguration).filter(PeriodConfiguration.id == period_id).first()
        )
    elif period_code:
        explicit_period = (
            db.query(PeriodConfiguration)
            .filter(PeriodConfiguration.period_code == period_code)
            .first()
        )

    if explicit_period is not None:
        if target_date < explicit_period.start_date or target_date > explicit_period.end_date:
            raise ValueError(
                f"Date {target_date.isoformat()} is outside the selected period "
                f"'{explicit_period.period_name}' ({explicit_period.start_date.isoformat()} to {explicit_period.end_date.isoformat()})"
            )

    # Resolve the PeriodConfiguration covering `target_date` for team & leader attribution
    date_period = explicit_period or (
        db.query(PeriodConfiguration)
        .filter(
            PeriodConfiguration.configuration_status == "ACTIVE",
            PeriodConfiguration.start_date <= target_date,
            PeriodConfiguration.end_date >= target_date,
        )
        .order_by(PeriodConfiguration.id.desc())
        .first()
    )

    all_db_employees: List[Employee] = db.query(Employee).all()
    all_employees_map: Dict[int, Employee] = {e.id: e for e in all_db_employees}
    hist_map = EligibilityService.build_history_map(db)
    rm_map = _build_rm_map(all_db_employees)

    emp_team_map: Dict[int, Tuple[str, str]] = {}
    if date_period is not None:
        assignments = (
            db.query(PeriodTeamAssignment)
            .filter(PeriodTeamAssignment.period_id == date_period.id)
            .all()
        )
        for a in assignments:
            leader_emp = all_employees_map.get(a.team_leader_id)
            leader_name = leader_emp.name if leader_emp and leader_emp.name else "—"
            t_name = a.team_name or (f"Team {leader_name.split()[0]}" if leader_name != "—" else "—")
            emp_team_map[a.employee_id] = (t_name, leader_name)

        team_cfgs = (
            db.query(PeriodTeamTargetConfiguration)
            .filter(PeriodTeamTargetConfiguration.period_id == date_period.id)
            .all()
        )
        for tc in team_cfgs:
            if tc.team_leader_id not in emp_team_map:
                leader_emp = all_employees_map.get(tc.team_leader_id)
                leader_name = leader_emp.name if leader_emp and leader_emp.name else "—"
                emp_team_map[tc.team_leader_id] = (tc.team_name or f"Team {leader_name.split()[0]}", leader_name)

    raw_records = fetch_sheet_records()

    # Group strictly by target_date and active eligible employee
    grouped: Dict[int, dict] = {}
    for rec in raw_records:
        if rec.date != target_date:
            continue
        if rec.revenue <= 0:
            continue

        emp = _resolve_rm(rec.rm_name, rm_map)
        if not emp:
            continue

        if date_period is not None:
            if not EligibilityService.is_employee_eligible_for_period(
                emp, date_period.start_date, date_period.end_date, hist_map
            ):
                continue
        if not EligibilityService.is_employee_active_on_date(emp, target_date, hist_map):
            continue

        if employee_id and emp.id != employee_id:
            continue
        if rm_name:
            rm_lower = rm_name.strip().lower()
            name_to_check = (emp.name or "").lower()
            if rm_lower not in name_to_check and name_to_check not in rm_lower:
                continue

        team_name, leader_name = emp_team_map.get(
            emp.id,
            ("—", emp.reporting_manager or "—"),
        )

        if emp.id not in grouped:
            grouped[emp.id] = {
                "employee_id": emp.id,
                "employee_name": emp.name,
                "team_name": team_name,
                "team_leader_name": leader_name,
                "transaction_count": 1,
                "beds_sold": float(rec.key_count or 0.0),
                "revenue": float(rec.revenue or 0.0),
            }
        else:
            grouped[emp.id]["transaction_count"] += 1
            grouped[emp.id]["beds_sold"] += float(rec.key_count or 0.0)
            grouped[emp.id]["revenue"] += float(rec.revenue or 0.0)

    employee_items = [
        DailyRevenueEmployeeItem(**vals)
        for vals in grouped.values()
    ]
    employee_items.sort(
        key=lambda x: (x.revenue, x.transaction_count, x.employee_name.lower()),
        reverse=True,
    )

    total_revenue = sum(item.revenue for item in employee_items)
    total_transactions = sum(item.transaction_count for item in employee_items)

    return DailyRevenueDrilldownResponse(
        selected_date=target_date.isoformat(),
        period_code=date_period.period_code if date_period else period_code,
        period_name=date_period.period_name if date_period else None,
        total_revenue=total_revenue,
        employee_count=len(employee_items),
        total_transactions=total_transactions,
        employees=employee_items,
    )

