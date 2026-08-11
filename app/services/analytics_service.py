"""
Analytics Service — All backend business logic for the Performance Dashboard.

Rules:
- Data comes from Google Sheet (Date, RM Name, Key Count, Revenue only).
- Targets come ONLY from the Employee table (monthly_target column).
- Only ACTIVE employees are included in calculations.
- RM Name matching is case-insensitive fuzzy partial match (sheet name may differ from DB).
- Incentive slabs:
    Revenue >= 3,00,000  -> incentive = 1,00,000
    Revenue >= 2,00,000  -> incentive =   35,000
    Revenue >= 1,00,000  -> incentive =   20,000
    Revenue <  1,00,000  -> incentive =        0
- Achievement status:
    >= 100% -> "Target Achieved"
    >= 50%  -> "In Progress"
    < 50%   -> "Needs Improvement"
"""

import logging
from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.employee_monthly_target import EmployeeMonthlyTarget
from app.services.google_sheet_service import SheetRecord, fetch_sheet_records
from app.schemas.analytics import (
    DailyRevenueItem,
    DashboardResponse,
    KPIResponse,
    LeaderboardItem,
    MonthComparisonItem,
    MonthlyRevenueItem,
    PerformanceTableItem,
    PrevCurrentMonthResponse,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Incentive calculation
# ---------------------------------------------------------------------------

def calculate_incentive(revenue: float) -> float:
    """
    Incentive slabs:
      >= 3,00,000 -> 1,00,000
      >= 2,00,000 ->   35,000
      >= 1,00,000 ->   20,000
      <  1,00,000 ->        0
    """
    if revenue >= 300_000:
        return 100_000.0
    elif revenue >= 200_000:
        return 35_000.0
    elif revenue >= 100_000:
        return 20_000.0
    else:
        return 0.0


# ---------------------------------------------------------------------------
# Achievement % and status
# ---------------------------------------------------------------------------

def calculate_achievement_pct(revenue: float, target: float) -> float:
    if target <= 0:
        return 0.0
    return round((revenue / target) * 100, 2)


def calculate_status(achievement_pct: float) -> str:
    if achievement_pct >= 100:
        return "Target Achieved"
    elif achievement_pct >= 50:
        return "In Progress"
    else:
        return "Needs Improvement"


# ---------------------------------------------------------------------------
# RM Name fuzzy matching
# ---------------------------------------------------------------------------

def _normalize_name(name: str) -> str:
    """Lowercase, strip, collapse whitespace."""
    return " ".join(name.lower().split())


def _names_match(sheet_name: str, db_name: str) -> bool:
    """
    Case-insensitive fuzzy partial match.
    True if either name contains the other, or if they share a common
    significant token (first name or last name word).
    Sheet examples: "Chethan", "chethan", "Chethan P", "S Victor Daniel"
    DB examples: "Chethan P", "Victor Daniel", "Pritish Kumar Jena"
    """
    sn = _normalize_name(sheet_name)
    dn = _normalize_name(db_name)

    if sn == dn:
        return True
    if sn in dn or dn in sn:
        return True

    import difflib
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
    """
    Build a lookup dict: normalized_db_name -> Employee
    for all active employees.
    """
    return {_normalize_name(e.name): e for e in employees if e.name}


def _resolve_rm(sheet_rm: str, rm_map: Dict[str, Employee]) -> Optional[Employee]:
    """
    Given a sheet RM name, find the matching active Employee using fuzzy match.
    Returns None if no match found.
    """
    sn = _normalize_name(sheet_rm)
    for db_name_norm, emp in rm_map.items():
        if _names_match(sn, db_name_norm):
            return emp
    return None


# ---------------------------------------------------------------------------
# Filtering helpers
# ---------------------------------------------------------------------------

def _record_month(r: SheetRecord) -> str:
    return r.date.strftime("%Y-%m")


def _apply_filters(
    records: List[SheetRecord],
    month: Optional[str],
    rm_name: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
) -> List[SheetRecord]:
    filtered = records
    if month:
        filtered = [r for r in filtered if _record_month(r) == month]
    if start_date:
        filtered = [r for r in filtered if r.date >= start_date]
    if end_date:
        filtered = [r for r in filtered if r.date <= end_date]
    if rm_name:
        rm_lower = rm_name.strip().lower()
        filtered = [
            r for r in filtered
            if rm_lower in r.rm_name.lower() or r.rm_name.lower() in rm_lower
        ]
    return filtered


# ---------------------------------------------------------------------------
# Target fetching helper
# ---------------------------------------------------------------------------

def _get_targets_for_month(db: Session, active_employees: List[Employee], month_str: str) -> Dict[int, float]:
    try:
        y, m = map(int, month_str.split('-'))
    except ValueError:
        return {}
    
    if not active_employees:
        return {}
        
    targets = db.query(EmployeeMonthlyTarget).filter(
        EmployeeMonthlyTarget.month == m,
        EmployeeMonthlyTarget.year == y,
        EmployeeMonthlyTarget.employee_id.in_([e.id for e in active_employees])
    ).all()
    
    target_map = {t.employee_id: t.target for t in targets}
    
    # Apply fallback: 1,00,000 for August, 0 for rest
    final_targets = {}
    for e in active_employees:
        if e.id in target_map:
            final_targets[e.id] = target_map[e.id]
        else:
            final_targets[e.id] = 100000.0 if m == 8 else 0.0
    return final_targets


def _target_for_emp(emp: Optional[Employee], targets_map: Dict[int, float], month_str: str) -> float:
    if not emp:
        try:
            m = int(month_str.split('-')[1])
            return 100000.0 if m == 8 else 0.0
        except:
            return 0.0
    return targets_map.get(emp.id, 0.0)


# ---------------------------------------------------------------------------
# Main analytics function
# ---------------------------------------------------------------------------

def build_dashboard(
    db: Session,
    month: Optional[str] = None,
    rm_name: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> DashboardResponse:
    """
    Master function: fetches sheet data, joins with employee DB,
    applies filters, and computes all dashboard sections.
    """

    # 1. Fetch raw sheet records (always fresh)
    raw_records = fetch_sheet_records()

    # 2. Fetch all active employees from DB
    active_employees: List[Employee] = (
        db.query(Employee).filter(Employee.status.ilike("ACTIVE")).all()
    )
    rm_map = _build_rm_map(active_employees)

    # 3. Resolve RM for each record & build enriched records
    #    Each enriched record: (SheetRecord, matched_employee | None)
    enriched: List[Tuple[SheetRecord, Optional[Employee]]] = []
    for rec in raw_records:
        emp = _resolve_rm(rec.rm_name, rm_map)
        enriched.append((rec, emp))

    # 4. Collect available filter options (BEFORE applying filters)
    all_months = sorted(
        {_record_month(r) for r, _ in enriched}, reverse=True
    )
    all_rms = sorted(
        {(emp.name if emp and emp.name else rec.rm_name.strip().title()) for rec, emp in enriched}
    )

    # Determine "current month" context for prev/current comparison
    # If month filter is applied, use that as current; else use today
    if month:
        try:
            reference_date = datetime.strptime(month + "-01", "%Y-%m-%d").date()
        except ValueError:
            reference_date = date.today().replace(day=1)
    else:
        reference_date = date.today().replace(day=1)

    current_month_str = reference_date.strftime("%Y-%m")
    # Previous month
    if reference_date.month == 1:
        prev_month_date = reference_date.replace(year=reference_date.year - 1, month=12)
    else:
        prev_month_date = reference_date.replace(month=reference_date.month - 1)
    prev_month_str = prev_month_date.strftime("%Y-%m")

    # Fetch targets for current and previous month
    current_targets = _get_targets_for_month(db, active_employees, current_month_str)
    prev_targets = _get_targets_for_month(db, active_employees, prev_month_str)

    # 5. Apply all filters to enriched records
    def _match_filters(rec: SheetRecord, emp: Employee) -> bool:
        if month and _record_month(rec) != month:
            return False
        if start_date and rec.date < start_date:
            return False
        if end_date and rec.date > end_date:
            return False
        if rm_name:
            rm_lower = rm_name.strip().lower()
            name_to_check = emp.name.lower() if emp and emp.name else rec.rm_name.lower()
            if rm_lower not in name_to_check and name_to_check not in rm_lower:
                return False
        return True

    filtered = [(r, e) for r, e in enriched if _match_filters(r, e)]

    # 6. Aggregate per RM for the filtered dataset
    rm_revenue: Dict[str, float] = defaultdict(float)
    rm_key_count: Dict[str, float] = defaultdict(float)
    rm_employee: Dict[str, Employee] = {}

    for rec, emp in filtered:
        key = emp.name if emp and emp.name else rec.rm_name.strip().title()
        rm_revenue[key] += rec.revenue
        rm_key_count[key] += rec.key_count
        if emp is not None:
            rm_employee[key] = emp

    # 7. KPI Cards
    total_revenue = sum(rm_revenue.values())
    total_beds = sum(rm_key_count.values())

    # Overall target = sum of monthly targets of applicable active RMs with records
    applicable_rms = set(rm_revenue.keys())
    overall_target = sum(
        _target_for_emp(rm_employee.get(name), current_targets, current_month_str)
        for name in applicable_rms
    )
    achievement_pct = calculate_achievement_pct(total_revenue, overall_target)
    active_rms_count = len(applicable_rms)

    kpis = KPIResponse(
        total_revenue=total_revenue,
        beds_sold=total_beds,
        overall_target=overall_target,
        achievement_pct=achievement_pct,
        active_rms=active_rms_count,
    )

    # 8. Monthly Revenue — group all (no additional filter) by month
    monthly_map: Dict[str, float] = defaultdict(float)
    for rec, emp in enriched:
        # Apply rm_name filter if set, but NOT month/date filters
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

    # 9. Daily Revenue — only for the current/selected month
    daily_map: Dict[str, float] = defaultdict(float)
    for rec, emp in enriched:
        if _record_month(rec) != current_month_str:
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

    # 10. Previous vs Current Month Comparison
    def _build_month_comparison(m_str: str) -> Optional[MonthComparisonItem]:
        month_records = [
            (r, e) for r, e in enriched
            if _record_month(r) == m_str
        ]
        if rm_name:
            rm_lower = rm_name.strip().lower()
            month_records = [
                (r, e) for r, e in month_records
                if rm_lower in (e.name.lower() if e and e.name else r.rm_name.lower()) or 
                   (e.name.lower() if e and e.name else r.rm_name.lower()) in rm_lower
            ]
        if not month_records:
            return None
        m_revenue = sum(r.revenue for r, _ in month_records)
        m_beds = sum(r.key_count for r, _ in month_records)
        # target for the month: sum targets of all RMs appearing in that month
        m_rms_names = set((e.name if e and e.name else r.rm_name.strip().title()) for r, e in month_records)
        m_targets_map = current_targets if m_str == current_month_str else prev_targets
        m_target = sum(
            _target_for_emp(rm_map.get(_normalize_name(n)), m_targets_map, m_str)
            for n in m_rms_names
        )
        m_achievement = calculate_achievement_pct(m_revenue, m_target)
        m_incentive = calculate_incentive(m_revenue)
        return MonthComparisonItem(
            month=m_str,
            revenue=m_revenue,
            beds_sold=m_beds,
            achievement_pct=m_achievement,
            incentive=m_incentive,
        )

    prev_comparison = _build_month_comparison(prev_month_str)
    curr_comparison = _build_month_comparison(current_month_str)
    prev_current = PrevCurrentMonthResponse(
        previous=prev_comparison,
        current=curr_comparison,
    )

    # 11. Leaderboard — top 3 RMs by revenue from filtered data
    leaderboard_data: List[LeaderboardItem] = []
    for name, rev in rm_revenue.items():
        emp = rm_employee.get(name)
        target = _target_for_emp(emp, current_targets, current_month_str)
        beds = rm_key_count[name]
        ach = calculate_achievement_pct(rev, target)
        remaining = max(0.0, target - rev)
        incentive = calculate_incentive(rev)
        leaderboard_data.append(
            LeaderboardItem(
                rm_name=name,
                revenue=rev,
                beds_sold=beds,
                target=target,
                achievement_pct=ach,
                remaining_target=remaining,
                incentive=incentive,
            )
        )

    leaderboard = sorted(leaderboard_data, key=lambda x: x.revenue, reverse=True)[:3]

    # 12. Performance Table — all active RMs with records
    performance_rows: List[PerformanceTableItem] = []
    for name, rev in rm_revenue.items():
        emp = rm_employee.get(name)
        target = _target_for_emp(emp, current_targets, current_month_str)
        beds = rm_key_count[name]
        ach = calculate_achievement_pct(rev, target)
        remaining = max(0.0, target - rev)
        incentive = calculate_incentive(rev)
        status = calculate_status(ach)
        performance_rows.append(
            PerformanceTableItem(
                rm_name=name,
                beds_sold=beds,
                revenue=rev,
                monthly_target=target,
                achievement_pct=ach,
                remaining_target=remaining,
                incentive=incentive,
                status=status,
            )
        )

    # Sort by revenue descending
    performance_rows.sort(key=lambda x: x.revenue, reverse=True)

    return DashboardResponse(
        kpis=kpis,
        monthly_revenue=monthly_revenue,
        daily_revenue=daily_revenue,
        prev_current_month=prev_current,
        leaderboard=leaderboard,
        performance_table=performance_rows,
        available_months=all_months,
        available_rms=all_rms,
    )
