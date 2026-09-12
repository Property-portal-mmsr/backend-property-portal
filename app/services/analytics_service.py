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
    Incentive slabs:
      >= 3,00,000 -> 1,00,000
      >= 2,00,000 ->   35,000
      >= 1,00,000 ->   20,000
      <  1,00,000 ->        0
    """
    if month_str.endswith("-09"):
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
    else:
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

    target_map = {t.employee_id: t.target for t in targets}

    final_targets = {}
    for e in active_employees:
        final_targets[e.id] = target_map.get(e.id, e.monthly_target or 0.0)
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

    filtered_employees = active_employees
    if rm_name:
        rm_lower = rm_name.strip().lower()
        filtered_employees = [
            emp for emp in active_employees
            if rm_lower in emp.name.lower()
        ]

    all_months_targets: Dict[str, Dict[int, float]] = {}
    if month:
        # Specific month selected → single-month target (existing behaviour)
        overall_target = sum(current_targets.get(emp.id, 0.0) for emp in filtered_employees)
        unique_months_in_filtered = {month}
        all_months_targets[month] = current_targets
    else:
        # All Time or custom date range → sum targets for every unique month
        # that has at least one record in the *filtered* dataset.
        unique_months_in_filtered: set[str] = {
            _record_month(rec) for rec, _ in filtered
        }

        overall_target = 0.0
        for m_str in unique_months_in_filtered:
            m_targets = _get_targets_for_month(db, active_employees, m_str)
            all_months_targets[m_str] = m_targets
            overall_target += sum(m_targets.get(emp.id, 0.0) for emp in filtered_employees)

    # Pre-calculate monthly revenue for each RM for incentive calculations
    rm_monthly_revenue: Dict[Tuple[str, str], float] = defaultdict(float)
    for rec, emp in filtered:
        key = emp.name if emp and emp.name else rec.rm_name.strip().title()
        rm_monthly_revenue[(key, _record_month(rec))] += rec.revenue

    # "Active RMs" means how many active employees are in the emp table (matching filters)
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

    # 9b. Previous Month Daily Revenue — same day-by-day for prev_month
    prev_daily_map: Dict[str, float] = defaultdict(float)
    for rec, emp in enriched:
        if _record_month(rec) != prev_month_str:
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
        
        is_tl = any(
            e.reporting_manager and _names_match(rm_name_norm, e.reporting_manager) 
            for e in active_employees
        )
        if not is_tl:
            return False, 0.0, 0.0, 0.0, 0
            
        team_members = [
            e for e in active_employees 
            if e.reporting_manager and _names_match(rm_name_norm, e.reporting_manager)
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
                    team_revenue += r.revenue
                    team_beds += r.key_count
                    
        return True, team_revenue, team_target, team_beds, len(team_members)

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

    # 13. Team Leader Incentive Tracker
    team_leader_tracker: List[TeamLeaderIncentiveTrackerItem] = []
    
    for emp in active_employees:
        is_tl, t_rev, t_tgt, t_beds, t_size = _get_team_stats(emp, current_month_str, m_targets_map=current_targets)
        if is_tl and current_month_str.endswith("-09"):
            base_target = t_tgt
            base_incentive = 15000.0
            slab_6l_target = 600000.0
            slab_6l_incentive = 30000.0
            slab_7l_target = 700000.0
            slab_7l_incentive = 50000.0
            
            slabs = [
                IncentiveSlab(target=base_target, incentive=base_incentive, achieved=(t_rev >= base_target)),
                IncentiveSlab(target=slab_6l_target, incentive=slab_6l_incentive, achieved=(t_rev >= slab_6l_target)),
                IncentiveSlab(target=slab_7l_target, incentive=slab_7l_incentive, achieved=(t_rev >= slab_7l_target)),
            ]
            
            if t_rev >= slab_7l_target:
                current_slab = slab_7l_target
                next_incentive = None
                next_slab_target = None
                revenue_remaining = None
                incentive_amount = slab_7l_incentive
                potential_incentive = slab_7l_incentive
            elif t_rev >= slab_6l_target:
                current_slab = slab_6l_target
                next_incentive = slab_7l_incentive
                next_slab_target = slab_7l_target
                revenue_remaining = slab_7l_target - t_rev
                incentive_amount = slab_6l_incentive
                potential_incentive = slab_7l_incentive
            elif t_rev >= base_target:
                current_slab = base_target
                next_incentive = slab_6l_incentive
                next_slab_target = slab_6l_target
                revenue_remaining = slab_6l_target - t_rev
                incentive_amount = base_incentive
                potential_incentive = slab_6l_incentive
            else:
                current_slab = None
                next_incentive = base_incentive
                next_slab_target = base_target
                revenue_remaining = base_target - t_rev
                incentive_amount = 0.0
                potential_incentive = base_incentive

            # Compile team members list
            rm_name_norm = _normalize_name(emp.name)
            team_members_list = [
                e for e in active_employees 
                if e.reporting_manager and _names_match(rm_name_norm, e.reporting_manager)
            ]
                
            team_member_stats = []
            for m_emp in team_members_list:
                m_rev = 0.0
                m_beds = 0.0
                m_name_norm = _normalize_name(m_emp.name)
                for sheet_rm_name, rev in rm_revenue.items():
                    if _names_match(m_name_norm, sheet_rm_name):
                        m_rev += rev
                        m_beds += rm_key_count.get(sheet_rm_name, 0)
                
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

            progress_percentage = min(100.0, (t_rev / next_slab_target * 100)) if next_slab_target and next_slab_target > 0 else 100.0
            
            team_leader_tracker.append(TeamLeaderIncentiveTrackerItem(
                team_leader_name=emp.name,
                team_size=t_size,
                team_beds=t_beds,
                team_revenue=t_rev,
                team_target=t_tgt,
                achievement_pct=calculate_achievement_pct(t_rev, t_tgt),
                slabs=slabs,
                current_slab=current_slab,
                next_slab_target=next_slab_target,
                revenue_remaining=revenue_remaining,
                potential_incentive=potential_incentive,
                incentive=incentive_amount,
                team_members=team_member_stats,
                beds_sold=t_beds,
                progress_percentage=progress_percentage
            ))
            
    team_leader_tracker.sort(key=lambda x: x.team_revenue, reverse=True)

    return DashboardResponse(
        kpis=kpis,
        monthly_revenue=monthly_revenue,
        daily_revenue=daily_revenue,
        prev_daily_revenue=prev_daily_revenue,
        prev_current_month=prev_current,
        leaderboard=leaderboard,
        performance_table=performance_rows,
        team_leader_tracker=team_leader_tracker,
        available_months=all_months,
        available_rms=all_rms,
    )
