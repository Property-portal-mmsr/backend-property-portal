"""
Reusable, Database-Driven Target, Revenue, Team & Incentive Calculation Service.

All targets, team assignments, Team Leader assignments, RM incentive slabs,
and Team Leader incentive rules are loaded dynamically from MySQL:
- PeriodConfiguration
- PeriodTeamAssignment
- PeriodTargetConfiguration
- PeriodIncentiveConfiguration
- PeriodTeamTargetConfiguration
- EmployeeEmploymentHistory (via EligibilityService)

Zero employee names, IDs, dates, targets, or incentive slabs are hardcoded here.
"""

from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.period_config import (
    PeriodConfiguration,
    PeriodTeamAssignment,
    PeriodTargetConfiguration,
    PeriodIncentiveConfiguration,
    PeriodTeamTargetConfiguration,
    PerformanceCalculationRecord,
    EmployeeEmploymentHistory,
)
from app.schemas.analytics import (
    KPIResponse,
    LeaderboardItem,
    PerformanceTableItem,
    TeamLeaderIncentiveTrackerItem,
    TeamMemberMini,
    IncentiveSlab,
    PeriodOptionItem,
    PeriodBreakdownItem,
)
from app.services.eligibility_service import EligibilityService
from app.services.google_sheet_service import SheetRecord


def calculate_achievement_pct(revenue: float, target: float) -> float:
    if target <= 0:
        return 0.0
    return round((revenue / target) * 100.0, 2)


def calculate_status(achievement_pct: float) -> str:
    if achievement_pct >= 100.0:
        return "Target Achieved"
    elif achievement_pct >= 50.0:
        return "In Progress"
    return "Needs Improvement"


def evaluate_rm_incentive_from_slabs(
    assigned_target: float,
    eligible_revenue: float,
    rm_slabs: List[PeriodIncentiveConfiguration],
) -> Tuple[float, Optional[str]]:
    """
    Evaluates an individual RM's incentive and applicable slab label from database-configured slabs.
    Rules:
    - Do not stack multiple slabs unless explicitly configured.
    - Do not apply an EXACT_TARGET_PCT slab to an employee with a different assigned target.
    - Evaluates slabs in descending priority order.
    """
    if assigned_target <= 0 and not any(s.eligibility_conditions == "ABSOLUTE_REVENUE" for s in rm_slabs):
        return 0.0, None

    ach_pct = (eligible_revenue / assigned_target * 100.0) if assigned_target > 0 else 0.0
    active_slabs = [s for s in rm_slabs if s.active_status and (s.incentive_type or "").upper() == "RM"]
    active_slabs.sort(key=lambda s: (s.priority, s.incentive_amount), reverse=True)

    matched_target_slab_label: Optional[str] = None

    for slab in active_slabs:
        cond = (slab.eligibility_conditions or "EXACT_TARGET_PCT").upper()
        label = slab.slab_label or f"₹{int(slab.assigned_target_amount or 0):,} -> ₹{int(slab.incentive_amount):,}"

        if cond == "EXACT_TARGET_PCT":
            if slab.assigned_target_amount is None:
                continue
            if abs(assigned_target - slab.assigned_target_amount) > 0.01:
                continue
            matched_target_slab_label = label
            # Must achieve threshold % (e.g. 100%) and revenue >= assigned_target (when threshold is 100%)
            required_rev = slab.assigned_target_amount * (slab.achievement_threshold / 100.0)
            if eligible_revenue + 1e-6 >= required_rev and ach_pct + 1e-6 >= slab.achievement_threshold:
                return float(slab.incentive_amount), label
            return 0.0, label

        elif cond == "MIN_TARGET_PCT":
            if slab.min_assigned_target is not None and assigned_target < slab.min_assigned_target:
                continue
            if slab.max_assigned_target is not None and assigned_target > slab.max_assigned_target:
                continue
            if matched_target_slab_label is None:
                matched_target_slab_label = label
            if ach_pct + 1e-6 >= slab.achievement_threshold:
                return float(slab.incentive_amount), label

        elif cond == "ABSOLUTE_REVENUE":
            if eligible_revenue >= slab.achievement_threshold:
                return float(slab.incentive_amount), label

        elif cond == "ANY_TARGET_PCT":
            if matched_target_slab_label is None and assigned_target > 0:
                matched_target_slab_label = label
            if assigned_target > 0 and ach_pct + 1e-6 >= slab.achievement_threshold and eligible_revenue >= assigned_target:
                return float(slab.incentive_amount), label

    return 0.0, matched_target_slab_label


def evaluate_tl_incentive_from_slabs(
    team_target: float,
    team_revenue: float,
    team_cfg: Optional[PeriodTeamTargetConfiguration],
    tl_slabs: List[PeriodIncentiveConfiguration],
) -> Tuple[float, str, List[IncentiveSlab], Optional[float], Optional[float], Optional[float], Optional[float], float]:
    """
    Evaluates Team Leader incentive, eligibility status, and slab progression from database configuration.
    Returns:
      (incentive_amount, eligibility_status, slabs, current_slab, next_slab_target,
       revenue_remaining, potential_incentive, progress_percentage)
    """
    ach_pct = (team_revenue / team_target * 100.0) if team_target > 0 else 0.0
    active_tl_slabs = [s for s in tl_slabs if s.active_status and (s.incentive_type or "").upper() == "TEAM_LEADER"]
    active_tl_slabs.sort(key=lambda s: s.priority, reverse=False)

    # Case 1: Single slab or team_cfg-driven 100% threshold (e.g. Nov First Half ₹12,500, Nov Second Half ₹20,000)
    if len(active_tl_slabs) <= 1 and team_cfg is not None:
        elig_pct = team_cfg.eligibility_percentage if team_cfg.eligibility_percentage > 0 else 100.0
        inc_amt = team_cfg.team_leader_incentive
        if active_tl_slabs:
            elig_pct = active_tl_slabs[0].achievement_threshold or elig_pct
            inc_amt = active_tl_slabs[0].incentive_amount or inc_amt

        target_for_elig = team_target * (elig_pct / 100.0)
        achieved = team_target > 0 and (ach_pct + 1e-6 >= elig_pct) and (team_revenue + 1e-6 >= target_for_elig)

        slab_list = [
            IncentiveSlab(
                target=target_for_elig,
                incentive=inc_amt,
                achieved=achieved,
                label=f"{int(elig_pct)}% Team Target -> ₹{int(inc_amt):,}",
            )
        ]
        if achieved:
            return (
                float(inc_amt),
                "Eligible",
                slab_list,
                target_for_elig,
                None,
                0.0,
                float(inc_amt),
                100.0,
            )
        else:
            rem = max(0.0, target_for_elig - team_revenue)
            prog = min(100.0, (team_revenue / target_for_elig * 100.0)) if target_for_elig > 0 else 0.0
            return (
                0.0,
                "Not Eligible",
                slab_list,
                None,
                target_for_elig,
                rem,
                float(inc_amt),
                round(prog, 2),
            )

    # Case 2: Multi-tier TL slabs (e.g. September or October)
    slab_items: List[IncentiveSlab] = []
    for s in active_tl_slabs:
        cond = (s.eligibility_conditions or "TEAM_TARGET_PCT").upper()
        if cond == "ABSOLUTE_REVENUE":
            s_tgt = float(s.achievement_threshold)
            s_ach = team_revenue >= s_tgt
        else:
            s_tgt = round(team_target * (s.achievement_threshold / 100.0), 2) if team_target > 0 else 0.0
            s_ach = team_target > 0 and (ach_pct + 1e-6 >= s.achievement_threshold) and (team_revenue + 1e-6 >= s_tgt)
        slab_items.append(
            IncentiveSlab(
                target=s_tgt,
                incentive=float(s.incentive_amount),
                achieved=s_ach,
                label=s.slab_label,
            )
        )

    earned = 0.0
    current_slab: Optional[float] = None
    next_slab_target: Optional[float] = None
    potential_incentive: Optional[float] = slab_items[0].incentive if slab_items else 0.0

    for idx, item in enumerate(slab_items):
        if item.achieved:
            earned = item.incentive
            current_slab = item.target
            if idx + 1 < len(slab_items):
                next_slab_target = slab_items[idx + 1].target
                potential_incentive = slab_items[idx + 1].incentive
            else:
                next_slab_target = None
                potential_incentive = item.incentive
        else:
            if next_slab_target is None and current_slab is None:
                next_slab_target = item.target
                potential_incentive = item.incentive
            break

    revenue_remaining = max(0.0, next_slab_target - team_revenue) if next_slab_target is not None else None
    progress_pct = (
        min(100.0, (team_revenue / next_slab_target * 100.0))
        if next_slab_target and next_slab_target > 0
        else (100.0 if earned > 0 else 0.0)
    )
    elig_status = "Eligible" if earned > 0 else "Not Eligible"

    return (
        earned,
        elig_status,
        slab_items,
        current_slab,
        next_slab_target,
        revenue_remaining,
        potential_incentive,
        round(progress_pct, 2),
    )


class CalculationService:
    @staticmethod
    def resolve_periods_for_query(
        db: Session,
        month: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        period_code: Optional[str] = None,
        period_id: Optional[int] = None,
    ) -> Tuple[List[PeriodConfiguration], List[PeriodOptionItem]]:
        """
        Finds the applicable PeriodConfiguration record(s) from MySQL for the given query filters,
        and also returns all available_periods for the relevant month.
        """
        all_active_periods = (
            db.query(PeriodConfiguration)
            .filter(PeriodConfiguration.configuration_status == "ACTIVE")
            .order_by(PeriodConfiguration.start_date.asc(), PeriodConfiguration.id.asc())
            .all()
        )

        # Determine month context for available_periods dropdown
        context_month = month
        if not context_month and start_date:
            context_month = start_date.strftime("%Y-%m")
        if not context_month and period_code:
            p_match = next((p for p in all_active_periods if p.period_code == period_code), None)
            if p_match:
                context_month = p_match.month
        if not context_month and period_id:
            p_match = next((p for p in all_active_periods if p.id == period_id), None)
            if p_match:
                context_month = p_match.month

        month_periods = [p for p in all_active_periods if p.month == context_month] if context_month else all_active_periods
        available_period_options = [
            PeriodOptionItem(
                id=p.id,
                period_code=p.period_code,
                period_name=p.period_name,
                start_date=p.start_date.isoformat(),
                end_date=p.end_date.isoformat(),
                month=p.month,
                period_type=p.period_type,
                approval_status=p.approval_status,
            )
            for p in month_periods
        ]

        if period_id is not None:
            matched = [p for p in all_active_periods if p.id == period_id]
            return matched, available_period_options

        if period_code:
            matched = [p for p in all_active_periods if p.period_code == period_code]
            return matched, available_period_options

        if start_date or end_date:
            q_start = start_date or date(2026, 9, 1)
            q_end = end_date or date(2026, 12, 31)
            overlapping = [
                p for p in all_active_periods
                if p.start_date <= q_end and p.end_date >= q_start
                and (not month or p.month == month)
            ]
            return overlapping, available_period_options

        if month:
            matched = [p for p in all_active_periods if p.month == month]
            return matched, available_period_options

        return [], available_period_options

    @staticmethod
    def compute_single_period(
        db: Session,
        period: PeriodConfiguration,
        enriched_records: List[Tuple[SheetRecord, Optional[Employee]]],
        all_employees_map: Dict[int, Employee],
        hist_map: Dict[int, List[EmployeeEmploymentHistory]],
        employee_id_filter: Optional[int] = None,
        rm_name_filter: Optional[str] = None,
        custom_start: Optional[date] = None,
        custom_end: Optional[date] = None,
        persist_snapshot: bool = True,
    ) -> PeriodBreakdownItem:
        """
        Computes KPIs, RM Performance Table, and Team Leader Tracker for a single PeriodConfiguration.
        """
        eff_start = max(period.start_date, custom_start) if custom_start else period.start_date
        eff_end = min(period.end_date, custom_end) if custom_end else period.end_date

        # Load DB configurations for this period
        assignments = (
            db.query(PeriodTeamAssignment)
            .filter(PeriodTeamAssignment.period_id == period.id)
            .order_by(PeriodTeamAssignment.id.asc())
            .all()
        )
        targets = (
            db.query(PeriodTargetConfiguration)
            .filter(PeriodTargetConfiguration.period_id == period.id)
            .all()
        )
        slabs = (
            db.query(PeriodIncentiveConfiguration)
            .filter(
                PeriodIncentiveConfiguration.period_id == period.id,
                PeriodIncentiveConfiguration.active_status == True,
            )
            .all()
        )
        team_target_cfgs = (
            db.query(PeriodTeamTargetConfiguration)
            .filter(PeriodTeamTargetConfiguration.period_id == period.id)
            .all()
        )

        # Filter out any employee who is NOT eligible for this period
        eligible_emp_ids = {
            emp_id
            for emp_id, emp in all_employees_map.items()
            if EligibilityService.is_employee_eligible_for_period(emp, period.start_date, period.end_date, hist_map)
        }

        target_map: Dict[int, float] = {
            t.employee_id: float(t.assigned_target_amount)
            for t in targets
            if t.employee_id in eligible_emp_ids
        }

        emp_assignment_map: Dict[int, PeriodTeamAssignment] = {
            a.employee_id: a
            for a in assignments
            if a.employee_id in eligible_emp_ids
        }

        leader_team_cfg_map: Dict[int, PeriodTeamTargetConfiguration] = {
            tt.team_leader_id: tt
            for tt in team_target_cfgs
            if tt.team_leader_id in eligible_emp_ids
        }

        # Filter revenue records falling inside [eff_start, eff_end] for eligible employees ONLY
        period_records: List[Tuple[SheetRecord, Employee]] = []
        for rec, emp in enriched_records:
            if rec.date < eff_start or rec.date > eff_end:
                continue
            if not emp or emp.id not in eligible_emp_ids:
                continue
            if not EligibilityService.is_employee_active_on_date(emp, rec.date, hist_map):
                continue
            period_records.append((rec, emp))

        # Aggregate revenue & beds per employee across the period (unfiltered by employee_id/rm_name first so team totals are accurate)
        emp_rev_all: Dict[int, float] = defaultdict(float)
        emp_beds_all: Dict[int, float] = defaultdict(float)
        for rec, emp in period_records:
            emp_rev_all[emp.id] += rec.revenue
            emp_beds_all[emp.id] += rec.key_count

        # 1. Compute Team Leader Tracker / Team Performance Table
        team_trackers: List[TeamLeaderIncentiveTrackerItem] = []
        leader_incentive_map: Dict[int, Tuple[float, Optional[str], float, float]] = {}

        for tt in team_target_cfgs:
            if tt.team_leader_id not in eligible_emp_ids:
                continue
            leader_emp = all_employees_map.get(tt.team_leader_id)
            if not leader_emp:
                continue

            team_assigns = [
                a for a in assignments
                if a.team_id == tt.team_id and a.employee_id in eligible_emp_ids
            ]
            member_ids = [a.employee_id for a in team_assigns]
            member_emps = [all_employees_map[m_id] for m_id in member_ids if m_id in all_employees_map]

            # Sum member targets (and ensure aggregate target reflects active eligible members)
            computed_member_target_sum = sum(target_map.get(m.id, 0.0) for m in member_emps)
            team_base_target = computed_member_target_sum if computed_member_target_sum > 0 else float(tt.aggregate_target)

            team_member_rev = sum(emp_rev_all.get(m.id, 0.0) for m in member_emps)
            team_member_beds = sum(emp_beds_all.get(m.id, 0.0) for m in member_emps)

            leader_in_members = leader_emp.id in member_ids
            leader_rev = emp_rev_all.get(leader_emp.id, 0.0)
            leader_beds = emp_beds_all.get(leader_emp.id, 0.0)

            if not leader_in_members:
                team_base_target += target_map.get(leader_emp.id, 0.0)
                overall_team_rev = team_member_rev + leader_rev
                overall_team_beds = team_member_beds + leader_beds
            else:
                overall_team_rev = team_member_rev
                overall_team_beds = team_member_beds

            team_ach_pct = calculate_achievement_pct(overall_team_rev, team_base_target)
            team_pending_rev = max(0.0, team_base_target - overall_team_rev)

            (
                tl_inc_amount,
                tl_elig_status,
                tl_slab_items,
                current_slab,
                next_slab_target,
                rev_remaining,
                potential_inc,
                prog_pct,
            ) = evaluate_tl_incentive_from_slabs(team_base_target, overall_team_rev, tt, slabs)

            tl_slab_label = tl_slab_items[0].label if len(tl_slab_items) == 1 else (
                f"₹{int(current_slab):,} Slab" if current_slab else (f"Target ₹{int(team_base_target):,}" if team_base_target > 0 else None)
            )
            leader_incentive_map[leader_emp.id] = (tl_inc_amount, tl_slab_label, overall_team_rev, team_base_target)

            # Build member mini rows
            member_minis: List[TeamMemberMini] = []
            for m_emp in member_emps:
                m_rev = emp_rev_all.get(m_emp.id, 0.0)
                m_beds = emp_beds_all.get(m_emp.id, 0.0)
                m_tgt = target_map.get(m_emp.id, 0.0)
                m_ach = calculate_achievement_pct(m_rev, m_tgt)
                m_inc, m_slab_lbl = evaluate_rm_incentive_from_slabs(m_tgt, m_rev, slabs)
                member_minis.append(
                    TeamMemberMini(
                        name=m_emp.name,
                        beds=m_beds,
                        revenue=m_rev,
                        target=m_tgt,
                        pending_revenue=max(0.0, m_tgt - m_rev),
                        achievement_pct=m_ach,
                        incentive_slab=m_slab_lbl,
                        incentive=m_inc,
                        status=calculate_status(m_ach),
                    )
                )

            team_trackers.append(
                TeamLeaderIncentiveTrackerItem(
                    team_id=tt.team_id,
                    team_name=tt.team_name or f"Team {leader_emp.name.split()[0]}",
                    team_leader_name=leader_emp.name,
                    team_size=len(member_emps),
                    team_beds=overall_team_beds,
                    team_revenue=overall_team_rev,
                    team_target=team_base_target,
                    pending_revenue=team_pending_rev,
                    achievement_pct=team_ach_pct,
                    eligibility_status=tl_elig_status,
                    slabs=tl_slab_items,
                    current_slab=current_slab,
                    next_slab_target=next_slab_target,
                    revenue_remaining=rev_remaining,
                    potential_incentive=potential_inc,
                    incentive=tl_inc_amount,
                    team_members=member_minis,
                    beds_sold=overall_team_beds,
                    progress_percentage=prog_pct,
                    team_leader_revenue=leader_rev,
                    team_member_revenue=team_member_rev,
                    team_leader_beds=leader_beds,
                    team_member_beds=team_member_beds,
                    leader_in_members=leader_in_members,
                    overall_team_revenue=overall_team_rev,
                )
            )

        team_trackers.sort(key=lambda x: x.team_revenue, reverse=True)

        # 2. Apply employee_id / rm_name filter for individual rows & KPIs
        def _emp_matches_filter(emp: Employee) -> bool:
            if employee_id_filter and emp.id != employee_id_filter:
                return False
            if rm_name_filter:
                q = rm_name_filter.strip().lower()
                en = (emp.name or "").lower()
                if q not in en and en not in q:
                    return False
            return True

        # Relevant employees for this period:
        # Anyone with an explicit target > 0, or assigned to a team in this period, or who generated revenue > 0
        relevant_emp_ids = (
            {emp_id for emp_id, tgt in target_map.items() if tgt > 0}
            | set(emp_assignment_map.keys())
            | {emp_id for emp_id, rev in emp_rev_all.items() if rev > 0}
        ) & eligible_emp_ids

        filtered_emp_ids = [
            emp_id for emp_id in relevant_emp_ids
            if _emp_matches_filter(all_employees_map[emp_id])
        ]

        include_zero_rev_rows = period.period_type in ("FIRST_HALF", "SECOND_HALF", "CUSTOM")

        perf_rows: List[PerformanceTableItem] = []
        total_rm_incentives = 0.0

        for emp_id in filtered_emp_ids:
            emp = all_employees_map[emp_id]
            rev = emp_rev_all.get(emp_id, 0.0)
            beds = emp_beds_all.get(emp_id, 0.0)
            tgt = target_map.get(emp_id, 0.0)
            is_tl = emp_id in leader_team_cfg_map

            assign = emp_assignment_map.get(emp_id)
            if assign:
                team_name = assign.team_name
                leader_emp = all_employees_map.get(assign.team_leader_id)
                team_leader_name = leader_emp.name if leader_emp else None
            elif is_tl:
                tt_cfg = leader_team_cfg_map[emp_id]
                team_name = tt_cfg.team_name
                team_leader_name = emp.name
            else:
                team_name = None
                team_leader_name = emp.reporting_manager or None

            if is_tl:
                tl_inc, tl_slab_lbl, t_rev, t_tgt = leader_incentive_map.get(emp_id, (0.0, None, 0.0, 0.0))
                inc_val = tl_inc
                slab_lbl = tl_slab_lbl
            else:
                inc_val, slab_lbl = evaluate_rm_incentive_from_slabs(tgt, rev, slabs)
                total_rm_incentives += inc_val

            # For historical FULL_MONTH periods (2026-09, 2026-10), preserve the exact performance_table filter (rev > 0)
            # For configured sub-month periods (First Half, Second Half), include all configured active employees
            if not include_zero_rev_rows and rev <= 0:
                continue

            ach_pct = calculate_achievement_pct(rev, tgt)
            rem_tgt = max(0.0, tgt - rev)
            status_str = calculate_status(ach_pct)

            next_slab = None
            if is_tl:
                _, _, t_rev, t_tgt = leader_incentive_map.get(emp_id, (0.0, None, 0.0, 0.0))
                if t_tgt > 0 and t_rev < t_tgt:
                    next_slab = t_tgt
                elif period.month == "2026-09":
                    if t_rev < 600000.0:
                        next_slab = 600000.0
                    elif t_rev < 700000.0:
                        next_slab = 700000.0

            perf_rows.append(
                PerformanceTableItem(
                    rm_name=emp.name,
                    beds_sold=beds,
                    revenue=rev,
                    monthly_target=tgt,
                    achievement_pct=ach_pct,
                    remaining_target=rem_tgt,
                    incentive=inc_val,
                    incentive_slab=slab_lbl,
                    status=status_str,
                    is_team_leader=is_tl,
                    next_slab=next_slab,
                    team_name=team_name,
                    team_leader_name=team_leader_name,
                )
            )

            # Save calculation snapshot when unfiltered
            if persist_snapshot and not employee_id_filter and not rm_name_filter:
                existing_rec = (
                    db.query(PerformanceCalculationRecord)
                    .filter(
                        PerformanceCalculationRecord.period_id == period.id,
                        PerformanceCalculationRecord.employee_id == emp.id,
                        PerformanceCalculationRecord.role_type == ("TEAM_LEADER" if is_tl else "RM"),
                    )
                    .first()
                )
                if existing_rec:
                    existing_rec.eligible_revenue = rev
                    existing_rec.assigned_target = tgt
                    existing_rec.achievement_percentage = ach_pct
                    existing_rec.applicable_incentive_slab = slab_lbl
                    existing_rec.calculated_incentive = inc_val
                    existing_rec.calculation_timestamp = datetime.utcnow()
                    existing_rec.configuration_version = period.version
                else:
                    db.add(
                        PerformanceCalculationRecord(
                            period_id=period.id,
                            employee_id=emp.id,
                            role_type="TEAM_LEADER" if is_tl else "RM",
                            eligible_revenue=rev,
                            assigned_target=tgt,
                            achievement_percentage=ach_pct,
                            applicable_incentive_slab=slab_lbl,
                            calculated_incentive=inc_val,
                            calculation_timestamp=datetime.utcnow(),
                            configuration_version=period.version,
                        )
                    )

        perf_rows.sort(key=lambda x: (x.revenue, x.monthly_target, x.rm_name), reverse=True)

        # Top RM provisional badge for October 2026
        if period.month == "2026-10":
            top_rm_count = 0
            for row in perf_rows:
                if not row.is_team_leader and row.revenue > 0:
                    top_rm_count += 1
                    row.is_top_rm = True
                    row.top_rm_status = f"Top {top_rm_count} (Provisional)"
                    if top_rm_count >= 2:
                        break

        if persist_snapshot and not employee_id_filter and not rm_name_filter:
            try:
                db.commit()
            except Exception:
                db.rollback()

        total_rev = sum(emp_rev_all.get(emp_id, 0.0) for emp_id in filtered_emp_ids)
        total_beds = sum(emp_beds_all.get(emp_id, 0.0) for emp_id in filtered_emp_ids)
        overall_tgt = sum(target_map.get(emp_id, 0.0) for emp_id in filtered_emp_ids)
        overall_ach = calculate_achievement_pct(total_rev, overall_tgt)
        total_tl_incentives = sum((t.incentive or 0.0) for t in team_trackers)

        kpis = KPIResponse(
            total_revenue=total_rev,
            beds_sold=total_beds,
            overall_target=overall_tgt,
            achievement_pct=overall_ach,
            active_rms=len(filtered_emp_ids),
            total_rm_incentives=total_rm_incentives,
            total_tl_incentives=total_tl_incentives,
            total_incentives=total_rm_incentives + total_tl_incentives,
        )

        return PeriodBreakdownItem(
            period_id=period.id,
            period_code=period.period_code,
            period_name=period.period_name,
            start_date=eff_start.isoformat(),
            end_date=eff_end.isoformat(),
            kpis=kpis,
            performance_table=perf_rows,
            team_leader_tracker=team_trackers,
        )

    @staticmethod
    def combine_period_breakdowns(
        breakdowns: List[PeriodBreakdownItem],
    ) -> Tuple[KPIResponse, List[PerformanceTableItem], List[TeamLeaderIncentiveTrackerItem]]:
        """
        Combines multiple independent period breakdowns (e.g. Nov First Half + Nov Second Half)
        without double-counting revenue or incentives and without cross-applying team assignments or slabs.
        """
        if len(breakdowns) == 1:
            b = breakdowns[0]
            return b.kpis, b.performance_table, b.team_leader_tracker

        total_rev = sum(b.kpis.total_revenue for b in breakdowns)
        total_beds = sum(b.kpis.beds_sold for b in breakdowns)
        overall_target = sum(b.kpis.overall_target for b in breakdowns)
        total_rm_inc = sum(b.kpis.total_rm_incentives for b in breakdowns)
        total_tl_inc = sum(b.kpis.total_tl_incentives for b in breakdowns)

        # Combine employee rows across periods
        emp_combined: Dict[str, dict] = {}
        for b in breakdowns:
            for row in b.performance_table:
                entry = emp_combined.get(row.rm_name)
                if not entry:
                    emp_combined[row.rm_name] = {
                        "rm_name": row.rm_name,
                        "beds_sold": row.beds_sold,
                        "revenue": row.revenue,
                        "monthly_target": row.monthly_target,
                        "incentive": row.incentive,
                        "slabs": [f"{b.period_name}: {row.incentive_slab}"] if row.incentive_slab else [],
                        "is_team_leader": row.is_team_leader,
                        "team_name": row.team_name,
                        "team_leader_name": row.team_leader_name,
                    }
                else:
                    entry["beds_sold"] += row.beds_sold
                    entry["revenue"] += row.revenue
                    entry["monthly_target"] += row.monthly_target
                    entry["incentive"] += row.incentive
                    if row.incentive_slab:
                        entry["slabs"].append(f"{b.period_name}: {row.incentive_slab}")
                    entry["is_team_leader"] = entry["is_team_leader"] or row.is_team_leader
                    # Prefer latest period's team assignment for current team display
                    if row.team_name:
                        entry["team_name"] = row.team_name
                    if row.team_leader_name:
                        entry["team_leader_name"] = row.team_leader_name

        combined_rows: List[PerformanceTableItem] = []
        for rm_name, d in emp_combined.items():
            ach_pct = calculate_achievement_pct(d["revenue"], d["monthly_target"])
            rem = max(0.0, d["monthly_target"] - d["revenue"])
            combined_rows.append(
                PerformanceTableItem(
                    rm_name=rm_name,
                    beds_sold=d["beds_sold"],
                    revenue=d["revenue"],
                    monthly_target=d["monthly_target"],
                    achievement_pct=ach_pct,
                    remaining_target=rem,
                    incentive=d["incentive"],
                    incentive_slab=" | ".join(d["slabs"]) if d["slabs"] else None,
                    status=calculate_status(ach_pct),
                    is_team_leader=d["is_team_leader"],
                    next_slab=None,
                    team_name=d["team_name"],
                    team_leader_name=d["team_leader_name"],
                )
            )
        combined_rows.sort(key=lambda x: (x.revenue, x.monthly_target, x.rm_name), reverse=True)

        # Combine Team Leader Trackers by team_id across periods
        team_combined: Dict[int, dict] = {}
        for b in breakdowns:
            for t in b.team_leader_tracker:
                existing = team_combined.get(t.team_id)
                if not existing:
                    team_combined[t.team_id] = {
                        "team_id": t.team_id,
                        "team_name": t.team_name,
                        "team_leader_name": t.team_leader_name,
                        "team_size": t.team_size,
                        "team_beds": t.team_beds,
                        "team_revenue": t.team_revenue,
                        "team_target": t.team_target,
                        "incentive": t.incentive or 0.0,
                        "potential_incentive": t.potential_incentive or 0.0,
                        "team_leader_revenue": t.team_leader_revenue,
                        "team_member_revenue": t.team_member_revenue,
                        "team_leader_beds": t.team_leader_beds,
                        "team_member_beds": t.team_member_beds,
                        "leader_in_members": t.leader_in_members,
                        "slabs": list(t.slabs),
                        "members_map": {
                            m.name: {
                                "name": m.name,
                                "beds": m.beds,
                                "revenue": m.revenue,
                                "target": m.target,
                                "incentive": m.incentive,
                                "incentive_slab": m.incentive_slab,
                            }
                            for m in t.team_members
                        },
                    }
                else:
                    existing["team_name"] = t.team_name
                    existing["team_leader_name"] = t.team_leader_name
                    existing["team_size"] = t.team_size
                    existing["team_beds"] += t.team_beds
                    existing["team_revenue"] += t.team_revenue
                    existing["team_target"] += t.team_target
                    existing["incentive"] += t.incentive or 0.0
                    existing["potential_incentive"] += t.potential_incentive or 0.0
                    existing["team_leader_revenue"] += t.team_leader_revenue
                    existing["team_member_revenue"] += t.team_member_revenue
                    existing["team_leader_beds"] += t.team_leader_beds
                    existing["team_member_beds"] += t.team_member_beds
                    existing["slabs"].extend(t.slabs)
                    for m in t.team_members:
                        if m.name not in existing["members_map"]:
                            existing["members_map"][m.name] = {
                                "name": m.name,
                                "beds": m.beds,
                                "revenue": m.revenue,
                                "target": m.target,
                                "incentive": m.incentive,
                                "incentive_slab": m.incentive_slab,
                            }
                        else:
                            mm = existing["members_map"][m.name]
                            mm["beds"] += m.beds
                            mm["revenue"] += m.revenue
                            mm["target"] += m.target
                            mm["incentive"] += m.incentive
                            if m.incentive_slab:
                                mm["incentive_slab"] = m.incentive_slab

        combined_trackers: List[TeamLeaderIncentiveTrackerItem] = []
        for t_id, td in team_combined.items():
            ach_pct = calculate_achievement_pct(td["team_revenue"], td["team_target"])
            pending = max(0.0, td["team_target"] - td["team_revenue"])
            elig_status = "Eligible" if td["incentive"] > 0 else "Not Eligible"
            member_list: List[TeamMemberMini] = []
            for m_name, md in td["members_map"].items():
                m_ach = calculate_achievement_pct(md["revenue"], md["target"])
                member_list.append(
                    TeamMemberMini(
                        name=m_name,
                        beds=md["beds"],
                        revenue=md["revenue"],
                        target=md["target"],
                        pending_revenue=max(0.0, md["target"] - md["revenue"]),
                        achievement_pct=m_ach,
                        incentive_slab=md["incentive_slab"],
                        incentive=md["incentive"],
                        status=calculate_status(m_ach),
                    )
                )
            combined_trackers.append(
                TeamLeaderIncentiveTrackerItem(
                    team_id=t_id,
                    team_name=td["team_name"],
                    team_leader_name=td["team_leader_name"],
                    team_size=len(member_list),
                    team_beds=td["team_beds"],
                    team_revenue=td["team_revenue"],
                    team_target=td["team_target"],
                    pending_revenue=pending,
                    achievement_pct=ach_pct,
                    eligibility_status=elig_status,
                    slabs=td["slabs"],
                    current_slab=td["team_target"] if td["incentive"] > 0 else None,
                    next_slab_target=None if td["incentive"] > 0 else td["team_target"],
                    revenue_remaining=0.0 if td["incentive"] > 0 else pending,
                    potential_incentive=td["potential_incentive"],
                    incentive=td["incentive"],
                    team_members=member_list,
                    beds_sold=td["team_beds"],
                    progress_percentage=min(100.0, ach_pct),
                    team_leader_revenue=td["team_leader_revenue"],
                    team_member_revenue=td["team_member_revenue"],
                    team_leader_beds=td["team_leader_beds"],
                    team_member_beds=td["team_member_beds"],
                    leader_in_members=td["leader_in_members"],
                    overall_team_revenue=td["team_revenue"],
                )
            )
        combined_trackers.sort(key=lambda x: x.team_revenue, reverse=True)

        combined_kpis = KPIResponse(
            total_revenue=total_rev,
            beds_sold=total_beds,
            overall_target=overall_target,
            achievement_pct=calculate_achievement_pct(total_rev, overall_target),
            active_rms=len(emp_combined),
            total_rm_incentives=total_rm_inc,
            total_tl_incentives=total_tl_inc,
            total_incentives=total_rm_inc + total_tl_inc,
        )

        return combined_kpis, combined_rows, combined_trackers

