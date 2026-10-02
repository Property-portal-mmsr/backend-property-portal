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
    IncentiveSlab,
    TeamLeaderIncentiveTrackerItem
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Incentive calculation
# ---------------------------------------------------------------------------

def calculate_incentive(
    revenue: float,
    target: float = 0.0,
    month_str: str = "",
    is_team_leader: bool = False,
    team_revenue: float = 0.0,
    team_target: float = 0.0,
) -> float:
    """
    Individual RM incentive slabs (default for non-September):
      >= 3,00,000 -> 1,00,000
      >= 2,00,000 ->   35,000
      >= 1,00,000 ->   20,000
      <  1,00,000 ->        0

    Team Leader incentive slabs (based on team revenue):
      >= 7,00,000 -> 50,000
      >= 6,00,000 -> 30,000
      >= team_target -> 15,000
      <  team_target ->      0

    September 2026 had special slabs (kept for historical accuracy).
    """
def _calculate_incentive_sep(
    revenue: float,
    target: float,
    is_team_leader: bool,
    team_revenue: float,
    team_target: float,
) -> float:
    # Existing September logic unchanged
    if is_team_leader:
        if team_revenue >= 700_000:
            return 50_000.0
        elif team_revenue >= 600_000:
            return 30_000.0
        elif team_target > 0 and team_revenue >= team_target:
            return 15_000.0
        else:
            return 0.0
    else:
        if revenue >= 200_000:
            return 30_000.0
        elif revenue >= 150_000:
            return 18_000.0
        elif target > 0 and revenue >= target:
            return 12_000.0
        else:
            return 0.0

def _calculate_incentive_oct(
    revenue: float,
    target: float,
    is_team_leader: bool,
    team_revenue: float,
    team_target: float,
) -> float:
    # New October logic
    if is_team_leader:
        ach_pct = (team_revenue / team_target * 100) if team_target > 0 else 0
        if ach_pct >= 150.0:
            return 60_000.0
        elif ach_pct >= 125.0:
            return 35_000.0
        elif ach_pct >= 100.0:
            return 15_000.0
        return 0.0
    else:
        ach_pct = (revenue / target * 100) if target > 0 else 0
        if target >= 120_000:
            # Slab A
            if ach_pct >= 200.0:
                return 40_000.0
            elif ach_pct >= 125.0:
                return 18_000.0
            elif ach_pct >= 100.0:
                return 12_000.0
            return 0.0
        elif target >= 55_000:
            # Slab B
            if ach_pct >= 130.0:
                return 10_000.0
            elif ach_pct >= 100.0:
                return 5_000.0
            return 0.0
        return 0.0

def _calculate_incentive_default(
    revenue: float,
    target: float,
    is_team_leader: bool,
    team_revenue: float,
    team_target: float,
) -> float:
    # Default fallback slabs (used if month is not configured)
    if is_team_leader:
        if team_revenue >= 700_000:
            return 50_000.0
        elif team_revenue >= 600_000:
            return 30_000.0
        elif team_target > 0 and team_revenue >= team_target:
            return 15_000.0
        return 0.0
    else:
        if revenue >= target and target > 0:
            return 12_000.0
        return 0.0

INCENTIVE_STRATEGIES = {
    '2026-09': _calculate_incentive_sep,
    '2026-10': _calculate_incentive_oct,
}

def calculate_incentive(
    revenue: float,
    target: float = 0.0,
    month_str: str = "",
    is_team_leader: bool = False,
    team_revenue: float = 0.0,
    team_target: float = 0.0,
) -> float:
    """
    Routes incentive calculation to the specific month strategy.
    """
    strategy = INCENTIVE_STRATEGIES.get(month_str, _calculate_incentive_default)
    return strategy(
        revenue=revenue,
        target=target,
        is_team_leader=is_team_leader,
        team_revenue=team_revenue,
        team_target=team_target
    )




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


def _is_employee_eligible(emp: Optional[Employee], month_str: str) -> bool:
    """
    Check if the employee had joined by the end of the selected reporting month.
    If joining_date is after the end of the month, they are excluded.
    """
    if not emp:
        return False
    if not emp.joining_date:
        return True  # If no joining date is set, assume they are eligible
        
    try:
        y, m = map(int, month_str.split('-'))
        import calendar
        last_day = calendar.monthrange(y, m)[1]
        period_end_date = f"{y:04d}-{m:02d}-{last_day:02d}"
        
        # String comparison works for YYYY-MM-DD
        return emp.joining_date <= period_end_date
    except Exception:
        return True


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

_MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

def _month_str_to_name(month_str: str) -> str:
    """Convert 'YYYY-MM' to full month name, e.g. '2026-08' -> 'August'."""
    try:
        _, m = map(int, month_str.split('-'))
        return _MONTH_NAMES[m]
    except (ValueError, IndexError):
        return ""


def _get_targets_for_month(db: Session, active_employees: List[Employee], month_str: str) -> Dict[int, float]:
    try:
        y, _ = map(int, month_str.split('-'))
    except ValueError:
        return {}

    month_name = _month_str_to_name(month_str)
    if not month_name:
        return {}

    if not active_employees:
        return {}

    targets = db.query(EmployeeMonthlyTarget).filter(
        EmployeeMonthlyTarget.month == month_name,
        EmployeeMonthlyTarget.year == y,
        EmployeeMonthlyTarget.employee_id.in_([e.id for e in active_employees])
    ).all()

    target_map = {}
    duplicates = []
    for t in targets:
        if t.employee_id in target_map:
            duplicates.append(t.employee_id)
        else:
            target_map[t.employee_id] = t.target
            
    if duplicates:
        logger.warning(f"Duplicate EmployeeMonthlyTarget records found for employees {duplicates} in {month_name} {y}")

    final_targets = {}
    for e in active_employees:
        # DO NOT fallback to e.monthly_target. If no target for the month, it is 0.0
        final_targets[e.id] = target_map.get(e.id, 0.0)
    return final_targets


def _target_for_emp(emp: Optional[Employee], targets_map: Dict[int, float], month_str: str) -> float:
    if not emp:
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
    
    # Apply historical-period rule: Ankit and Pavan joined in October 2026.
    # We patch their joining_date in memory (using IDs to avoid name checks) 
    # to ensure the existing eligibility logic correctly excludes them 
    # from historical performance calculations without modifying DB data.
    for e in active_employees:
        if e.id in [70, 71]:
            e.joining_date = "2026-10-01"
            
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
    
    # Hide frozen months from UI selector
    FROZEN_REPORTING_PERIODS = {"2026-04", "2026-05", "2026-06", "2026-07", "2026-08"}
    available_months = [m for m in all_months if m not in FROZEN_REPORTING_PERIODS]
    
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
        # Exclude revenue/beds if employee joined after this record's month
        rec_month = _record_month(rec)
        if emp and not _is_employee_eligible(emp, rec_month):
            continue
            
        key = emp.name if emp and emp.name else rec.rm_name.strip().title()
        rm_revenue[key] += rec.revenue
        rm_key_count[key] += rec.key_count
        if emp is not None:
            rm_employee[key] = emp

    # 7. KPI Cards
    total_revenue = sum(rm_revenue.values())
    total_beds = sum(rm_key_count.values())

    # Overall target = sum of monthly targets across all applicable months.
    #
    # When a specific month is selected:   use that month's targets only.
    # When "All Time" or a date range:     discover every unique month that
    #   appears in the filtered records, fetch targets for each, then sum.
    #   This prevents the old bug of always using only the reference month.
    #
    # Per-employee dedup: each employee contributes their target ONCE per
    # unique month — the target DB already stores one row per employee/month,
    # so fetching per month and summing is correct.

    # Determine which employees are actually relevant for this dashboard view:
    # 1. Employees who generated revenue in the filtered records
    revenue_emp_ids = {emp.id for emp in rm_employee.values() if emp}
    
    # 2. Employees who have an explicit EmployeeMonthlyTarget record for the current month
    from app.models.employee_monthly_target import EmployeeMonthlyTarget
    try:
        curr_y, curr_m = map(int, current_month_str.split('-'))
        import calendar
        month_name = calendar.month_name[curr_m]
        explicit_targets = db.query(EmployeeMonthlyTarget).filter(
            EmployeeMonthlyTarget.month == month_name,
            EmployeeMonthlyTarget.year == curr_y,
            EmployeeMonthlyTarget.target > 0
        ).all()
        explicit_emp_ids = {t.employee_id for t in explicit_targets}
    except Exception:
        explicit_emp_ids = set()
        
    relevant_emp_ids = revenue_emp_ids | explicit_emp_ids
    
    # Base our active RMs only on relevant employees
    filtered_employees = [e for e in active_employees if e.id in relevant_emp_ids]
    
    # Exclude employees who have not joined by the current_month_str
    filtered_employees = [e for e in filtered_employees if _is_employee_eligible(e, current_month_str)]
    
    if rm_name:
        rm_lower = rm_name.strip().lower()
        filtered_employees = [
            emp for emp in filtered_employees
            if rm_lower in emp.name.lower()
        ]

    all_months_targets: Dict[str, Dict[int, float]] = {}
    if month:
        # Specific month selected → single-month target (existing behaviour)
        overall_target = sum(current_targets.get(emp.id, 0.0) for emp in filtered_employees)
        unique_months_in_filtered = {month}
        all_months_targets[month] = current_targets
    else:
        # All Time or custom date range
        unique_months_in_filtered: set[str] = {
            _record_month(rec) for rec, _ in filtered
        }

        # DO NOT accumulate targets across months (prevent cumulative target bug).
        # Always use the current reporting period's targets for the overall target.
        overall_target = sum(current_targets.get(emp.id, 0.0) for emp in filtered_employees)
        
        for m_str in unique_months_in_filtered:
            m_targets = _get_targets_for_month(db, active_employees, m_str)
            all_months_targets[m_str] = m_targets

    # Pre-calculate monthly revenue for each RM for incentive calculations
    rm_monthly_revenue: Dict[Tuple[str, str], float] = defaultdict(float)
    for rec, emp in filtered:
        m_str = _record_month(rec)
        if emp and not _is_employee_eligible(emp, m_str):
            continue
        key = emp.name if emp and emp.name else rec.rm_name.strip().title()
        rm_monthly_revenue[(key, m_str)] += rec.revenue

    # "Active RMs" means how many active employees are eligible in the emp table (matching filters)
    applicable_rms = set(rm_revenue.keys())
    active_rms_count = len(filtered_employees)

    achievement_pct = calculate_achievement_pct(total_revenue, overall_target)

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
        m_str = _record_month(rec)
        if emp and not _is_employee_eligible(emp, m_str):
            continue
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
        if emp and not _is_employee_eligible(emp, current_month_str):
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

    # 9b. Previous Month Daily Revenue — same day-by-day for prev_month
    prev_daily_map: Dict[str, float] = defaultdict(float)
    for rec, emp in enriched:
        if _record_month(rec) != prev_month_str:
            continue
        if emp and not _is_employee_eligible(emp, prev_month_str):
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

    def _get_team_stats(rm_emp: Optional[Employee], m_str: str, m_targets_map: Optional[Dict[int, float]] = None) -> Tuple[bool, float, float, float, int]:
        if not rm_emp:
            return False, 0.0, 0.0, 0.0, 0
            
        rm_name_norm = _normalize_name(rm_emp.name)
        
        # Explicitly check if the user is configured as a Team Leader in the database
        is_tl = bool(rm_emp.is_team_leader)
        
        if not is_tl:
            return False, 0.0, 0.0, 0.0, 0
            
        team_members = [
            e for e in active_employees 
            if e.reporting_manager and _normalize_name(e.reporting_manager) == rm_name_norm
            and _is_employee_eligible(e, m_str)
        ]
        
        if m_targets_map is None:
            m_targets_map = current_targets if m_str == current_month_str else prev_targets
        team_target = sum(m_targets_map.get(e.id, 0.0) for e in team_members)
        
        team_revenue = 0.0
        team_beds = 0.0
        team_member_ids = {e.id for e in team_members}
        
        for r, e in enriched:
            if _record_month(r) == m_str:
                if e and e.id in team_member_ids:
                    # Eligibility is already checked because they are in team_members
                    team_revenue += r.revenue
                    team_beds += r.key_count
                    
        return True, team_revenue, team_target, team_beds, len(team_members)

    # 10. Previous vs Current Month Comparison
    def _build_month_comparison(m_str: str) -> Optional[MonthComparisonItem]:
        month_records = [
            (r, e) for r, e in enriched
            if _record_month(r) == m_str and (e is None or _is_employee_eligible(e, m_str))
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
        
        m_incentive = 0.0
        # Calculate sum of individual incentives for this month
        rms_in_month = set((e.name if e and e.name else r.rm_name.strip().title()) for r, e in month_records)
        for rm_n in rms_in_month:
            emp = rm_map.get(_normalize_name(rm_n))
            rev = sum(r.revenue for r, e in month_records if (e.name if e and e.name else r.rm_name.strip().title()) == rm_n)
            tgt = _target_for_emp(emp, m_targets_map, m_str)
            is_tl, t_rev, t_tgt, t_beds, _t_size = _get_team_stats(emp, m_str, m_targets_map=m_targets_map)
            
            m_incentive += calculate_incentive(
                revenue=rev,
                target=tgt,
                month_str=m_str,
                is_team_leader=is_tl,
                team_revenue=t_rev,
                team_target=t_tgt
            )
            
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

    latest_month_in_filter = max(unique_months_in_filtered) if unique_months_in_filtered else current_month_str

    # 11. Leaderboard — top 3 RMs by revenue from filtered data
    leaderboard_data: List[LeaderboardItem] = []
    for name, rev in rm_revenue.items():
        emp = rm_employee.get(name)
        beds = rm_key_count[name]
        
        total_target = 0.0
        total_incentive = 0.0
        is_tl_any = False
        
        for m_str in unique_months_in_filtered:
            m_targets = all_months_targets.get(m_str, {})
            m_target = _target_for_emp(emp, m_targets, m_str)
            total_target += m_target
            
            m_rev = rm_monthly_revenue.get((name, m_str), 0.0)
            
            is_tl, t_rev, t_tgt, t_beds, _t_size = _get_team_stats(emp, m_str, m_targets_map=m_targets)
            if is_tl:
                is_tl_any = True
                
            m_incentive = calculate_incentive(
                revenue=m_rev,
                target=m_target,
                month_str=m_str,
                is_team_leader=is_tl,
                team_revenue=t_rev,
                team_target=t_tgt
            )
            total_incentive += m_incentive
            
        display_rev = rev
        display_target = total_target
        display_beds = beds
        display_ach = calculate_achievement_pct(display_rev, display_target)
        display_remaining = max(0.0, display_target - display_rev)
        
        leaderboard_data.append(
            LeaderboardItem(
                rm_name=name,
                revenue=display_rev,
                beds_sold=display_beds,
                target=display_target,
                achievement_pct=display_ach,
                remaining_target=display_remaining,
                incentive=total_incentive,
                is_team_leader=is_tl_any
            )
        )

    leaderboard = sorted(leaderboard_data, key=lambda x: x.revenue, reverse=True)[:3]

    # 12. Performance Table — all active RMs with records
    performance_rows: List[PerformanceTableItem] = []
    for name, rev in rm_revenue.items():
        emp = rm_employee.get(name)
        beds = rm_key_count[name]
        
        total_target = 0.0
        total_incentive = 0.0
        is_tl_any = False
        latest_t_rev = 0.0
        latest_t_tgt = 0.0
        
        for m_str in unique_months_in_filtered:
            m_targets = all_months_targets.get(m_str, {})
            m_target = _target_for_emp(emp, m_targets, m_str)
            total_target += m_target
            
            m_rev = rm_monthly_revenue.get((name, m_str), 0.0)
            
            is_tl, t_rev, t_tgt, t_beds, _t_size = _get_team_stats(emp, m_str, m_targets_map=m_targets)
            if is_tl:
                is_tl_any = True
                if m_str == latest_month_in_filter:
                    latest_t_rev = t_rev
                    latest_t_tgt = t_tgt
                    
            m_incentive = calculate_incentive(
                revenue=m_rev,
                target=m_target,
                month_str=m_str,
                is_team_leader=is_tl,
                team_revenue=t_rev,
                team_target=t_tgt
            )
            total_incentive += m_incentive
            
        display_rev = rev
        display_target = total_target
        display_beds = beds
        display_ach = calculate_achievement_pct(display_rev, display_target)
        display_remaining = max(0.0, display_target - display_rev)
        status = calculate_status(display_ach)
        
        next_slab = None
        if is_tl_any:
            if latest_t_tgt > 0 and latest_t_rev < latest_t_tgt:
                next_slab = latest_t_tgt
            elif latest_t_rev < 600000.0:
                next_slab = 600000.0
            elif latest_t_rev < 700000.0:
                next_slab = 700000.0
                
        performance_rows.append(
            PerformanceTableItem(
                rm_name=name,
                beds_sold=display_beds,
                revenue=display_rev,
                monthly_target=display_target,
                achievement_pct=display_ach,
                remaining_target=display_remaining,
                incentive=total_incentive,
                status=status,
                is_team_leader=is_tl_any,
                next_slab=next_slab
            )
        )

    # Sort by revenue descending
    performance_rows.sort(key=lambda x: x.revenue, reverse=True)
    
    # 12b. Top RM Provisional Logic (October specific, without multiplier)
    if current_month_str == '2026-10':
        top_rm_count = 0
        for row in performance_rows:
            if not row.is_team_leader:
                top_rm_count += 1
                row.is_top_rm = True
                row.top_rm_status = f"Top {top_rm_count} (Provisional)"
                if top_rm_count >= 2:
                    break

    # 13. Team Leader Incentive Tracker
    #
    # FIX: Previously hardcoded to only work for September ("-09").
    # Now uses Team/TeamMember DB tables with period-based filtering.
    # All team members appear even with ₹0 revenue (LEFT JOIN logic).
    team_leader_tracker: List[TeamLeaderIncentiveTrackerItem] = []
    
    # Fetch active teams from DB for the current performance period
    from app.models.team import Team as TeamModel, TeamMember as TeamMemberModel
    from datetime import date as _date_type

    try:
        # Parse period boundaries from current_month_str (e.g. "2026-10")
        _y, _m = map(int, current_month_str.split('-'))
        import calendar
        period_start = _date_type(_y, _m, 1)
        _, last_day = calendar.monthrange(_y, _m)
        period_end = _date_type(_y, _m, last_day)
    except (ValueError, IndexError):
        period_start = date.today().replace(day=1)
        period_end = date.today()

    # Teams active for this month:
    #   active_from <= period_end AND (active_until IS NULL OR active_until >= period_start)
    active_teams = (
        db.query(TeamModel)
        .filter(
            TeamModel.is_active == True,
            TeamModel.active_from <= period_end,
        )
        .all()
    )
    # Additional Python filter for active_until
    active_teams = [
        t for t in active_teams
        if t.active_until is None or t.active_until >= period_start
    ]

    # Build a map: employee_id -> team_name for the RM Performance table
    emp_team_name_map: Dict[int, str] = {}
    
    for team_obj in active_teams:
        # Get team leader
        leader = team_obj.leader
        if not leader:
            continue

        # Get all team members from the team_members table
        # LEFT JOIN logic: get ALL assigned members, regardless of whether they have sales
        db_members = (
            db.query(TeamMemberModel)
            .filter(
                TeamMemberModel.team_id == team_obj.id,
            )
            .all()
        )
        # Filter by date: member is active during this period
        db_members = [
            tm for tm in db_members
            if (tm.start_date is None or tm.start_date <= period_end) and
               (tm.end_date is None or tm.end_date >= period_start)
        ]
        
        # Resolve actual Employee objects for the members
        active_employees_map = {e.id: e for e in active_employees}
        
        # Filter: Employee must be eligible (joined before or during selected month)
        member_emp_ids = set()
        team_members_list = []
        for tm in db_members:
            e = active_employees_map.get(tm.employee_id)
            if e and _is_employee_eligible(e, current_month_str):
                member_emp_ids.add(e.id)
                team_members_list.append(e)
                
        # Populate emp_team_name_map for RM Performance table
        for e in team_members_list:
            emp_team_name_map[e.id] = team_obj.name
        
        t_size = len(team_members_list)
        
        # Calculate team target from monthly targets
        team_target = sum(current_targets.get(e.id, 0.0) for e in team_members_list)
        
        # Calculate team revenue/beds from sheet data for this month ONLY
        team_revenue = 0.0
        team_beds = 0.0
        for r, e in enriched:
            if _record_month(r) == current_month_str:
                if e and e.id in member_emp_ids:
                    team_revenue += r.revenue
                    team_beds += r.key_count
        
        # Incentive slabs — dynamic based on month
        if current_month_str == '2026-10':
            slab_1_target = team_target
            slab_1_incentive = 15000.0
            slab_2_target = team_target * 1.25 if team_target > 0 else 0
            slab_2_incentive = 35000.0
            slab_3_target = team_target * 1.50 if team_target > 0 else 0
            slab_3_incentive = 60000.0
            
            slabs = [
                IncentiveSlab(target=slab_1_target, incentive=slab_1_incentive, achieved=(team_revenue >= slab_1_target) if slab_1_target > 0 else False),
                IncentiveSlab(target=slab_2_target, incentive=slab_2_incentive, achieved=(team_revenue >= slab_2_target) if slab_2_target > 0 else False),
                IncentiveSlab(target=slab_3_target, incentive=slab_3_incentive, achieved=(team_revenue >= slab_3_target) if slab_3_target > 0 else False),
            ]
            
            if team_revenue >= slab_3_target and slab_3_target > 0:
                current_slab = slab_3_target
                next_slab_target = None
                revenue_remaining = None
                incentive_amount = slab_3_incentive
                potential_incentive = slab_3_incentive
            elif team_revenue >= slab_2_target and slab_2_target > 0:
                current_slab = slab_2_target
                next_slab_target = slab_3_target
                revenue_remaining = slab_3_target - team_revenue
                incentive_amount = slab_2_incentive
                potential_incentive = slab_3_incentive
            elif team_revenue >= slab_1_target and slab_1_target > 0:
                current_slab = slab_1_target
                next_slab_target = slab_2_target
                revenue_remaining = slab_2_target - team_revenue
                incentive_amount = slab_1_incentive
                potential_incentive = slab_2_incentive
            else:
                current_slab = None
                next_slab_target = slab_1_target
                revenue_remaining = slab_1_target - team_revenue
                incentive_amount = 0.0
                potential_incentive = slab_1_incentive
        else:
            base_target = team_target
            base_incentive = 15000.0
            slab_6l_target = 600000.0
            slab_6l_incentive = 30000.0
            slab_7l_target = 700000.0
            slab_7l_incentive = 50000.0
            
            slabs = [
                IncentiveSlab(target=base_target, incentive=base_incentive, achieved=(team_revenue >= base_target) if base_target > 0 else False),
                IncentiveSlab(target=slab_6l_target, incentive=slab_6l_incentive, achieved=(team_revenue >= slab_6l_target)),
                IncentiveSlab(target=slab_7l_target, incentive=slab_7l_incentive, achieved=(team_revenue >= slab_7l_target)),
            ]
            
            if team_revenue >= slab_7l_target:
                current_slab = slab_7l_target
                next_slab_target = None
                revenue_remaining = None
                incentive_amount = slab_7l_incentive
                potential_incentive = slab_7l_incentive
            elif team_revenue >= slab_6l_target:
                current_slab = slab_6l_target
                next_slab_target = slab_7l_target
                revenue_remaining = slab_7l_target - team_revenue
                incentive_amount = slab_6l_incentive
                potential_incentive = slab_7l_incentive
            elif base_target > 0 and team_revenue >= base_target:
                current_slab = base_target
                next_slab_target = slab_6l_target
                revenue_remaining = slab_6l_target - team_revenue
                incentive_amount = base_incentive
                potential_incentive = slab_6l_incentive
            else:
                current_slab = None
                next_slab_target = base_target if base_target > 0 else slab_6l_target
                revenue_remaining = next_slab_target - team_revenue
                incentive_amount = 0.0
                potential_incentive = base_incentive
            potential_incentive = base_incentive
        
        # Compile team members list — LEFT JOIN: show ALL members even with ₹0
        team_member_stats = []
        for m_emp in team_members_list:
            m_rev = 0.0
            m_beds = 0.0
            m_name_norm = _normalize_name(m_emp.name)
            
            # Match member revenue from sheet data
            for sheet_rm_name, rev_val in rm_revenue.items():
                if _names_match(m_name_norm, sheet_rm_name):
                    # Only use revenue from the selected month
                    m_rev += rm_monthly_revenue.get((sheet_rm_name, current_month_str), 0.0)
                    # Beds from the same month
                    for r, e in enriched:
                        if _record_month(r) == current_month_str and e and e.id == m_emp.id:
                            m_beds += r.key_count
                    break  # Found match, stop searching
            
            m_tgt = _target_for_emp(m_emp, current_targets, current_month_str)
            m_ach = calculate_achievement_pct(m_rev, m_tgt)
            
            from app.schemas.analytics import TeamMemberMini
            team_member_stats.append(TeamMemberMini(
                name=m_emp.name,
                beds=m_beds,
                revenue=m_rev,
                target=m_tgt,
                status=calculate_status(m_ach)
            ))

        progress_percentage = min(100.0, (team_revenue / next_slab_target * 100)) if next_slab_target and next_slab_target > 0 else 100.0
        
        team_leader_tracker.append(TeamLeaderIncentiveTrackerItem(
            team_id=team_obj.id,
            team_name=team_obj.name,
            team_leader_name=leader.name,
            team_size=t_size,
            team_beds=team_beds,
            team_revenue=team_revenue,
            team_target=team_target,
            achievement_pct=calculate_achievement_pct(team_revenue, team_target),
            slabs=slabs,
            current_slab=current_slab,
            next_slab_target=next_slab_target,
            revenue_remaining=revenue_remaining,
            potential_incentive=potential_incentive,
            incentive=incentive_amount,
            team_members=team_member_stats,
            beds_sold=team_beds,
            progress_percentage=progress_percentage
        ))
            
    team_leader_tracker.sort(key=lambda x: x.team_revenue, reverse=True)

    # 14. Enrich Performance Table rows with team names
    for row in performance_rows:
        emp = rm_employee.get(row.rm_name)
        if emp and emp.id in emp_team_name_map:
            row.team_name = emp_team_name_map[emp.id]

    return DashboardResponse(
        kpis=kpis,
        monthly_revenue=monthly_revenue,
        daily_revenue=daily_revenue,
        prev_daily_revenue=prev_daily_revenue,
        prev_current_month=prev_current,
        leaderboard=leaderboard,
        performance_table=performance_rows,
        team_leader_tracker=team_leader_tracker,
        available_months=available_months,
        available_rms=all_rms,
    )

