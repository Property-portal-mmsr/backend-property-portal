"""
Comprehensive Calculation Validation & Regression Test Suite (Phases 6 & 7)
Validates all 17 Final Acceptance Criteria against MySQL + Live Google Sheet Data.
"""

from datetime import date
from fastapi import HTTPException
from app.database.database import SessionLocal
from app.models.employee import Employee
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
from app.services.eligibility_service import EligibilityService
from app.services.calculation_service import (
    evaluate_rm_incentive_from_slabs,
    evaluate_tl_incentive_from_slabs,
)
from app.services.period_config_service import PeriodConfigService
from app.services.analytics_service import build_dashboard


def run_all_validations():
    db = SessionLocal()
    try:
        print("=== 1. EMPLOYEE DEACTIVATION & PRESERVATION VALIDATION ===")
        raj = db.query(Employee).filter(Employee.name == "Raj Singh").first()
        sanjota = db.query(Employee).filter(Employee.name == "Sanjota").first()
        assert raj is not None, "Raj Singh must remain in employees table"
        assert sanjota is not None, "Sanjota must remain in employees table"
        assert raj.status == "INACTIVE", f"Raj Singh status expected INACTIVE, got {raj.status}"
        assert sanjota.status == "INACTIVE", f"Sanjota status expected INACTIVE, got {sanjota.status}"
        assert raj.employment_end_date == "2026-10-31", f"Raj Singh end date: {raj.employment_end_date}"
        assert raj.deactivation_effective_date == "2026-11-01", f"Raj Singh eff date: {raj.deactivation_effective_date}"
        assert sanjota.employment_end_date == "2026-10-31", f"Sanjota end date: {sanjota.employment_end_date}"
        assert sanjota.deactivation_effective_date == "2026-11-01", f"Sanjota eff date: {sanjota.deactivation_effective_date}"

        hist_map = EligibilityService.build_history_map(db)
        # Historical eligibility (Sep & Oct 2026)
        assert EligibilityService.is_employee_eligible_for_period(sanjota, date(2026, 9, 1), date(2026, 9, 30), hist_map) is True
        assert EligibilityService.is_employee_eligible_for_period(sanjota, date(2026, 10, 1), date(2026, 10, 31), hist_map) is True
        assert EligibilityService.is_employee_eligible_for_period(raj, date(2026, 10, 1), date(2026, 10, 31), hist_map) is True
        # November & December exclusion
        assert EligibilityService.is_employee_eligible_for_period(raj, date(2026, 11, 1), date(2026, 11, 15), hist_map) is False
        assert EligibilityService.is_employee_eligible_for_period(sanjota, date(2026, 11, 1), date(2026, 11, 15), hist_map) is False
        assert EligibilityService.is_employee_eligible_for_period(raj, date(2026, 11, 16), date(2026, 11, 30), hist_map) is False
        assert EligibilityService.is_employee_eligible_for_period(sanjota, date(2026, 11, 16), date(2026, 11, 30), hist_map) is False
        assert EligibilityService.is_employee_eligible_for_period(raj, date(2026, 12, 1), date(2026, 12, 31), hist_map) is False
        assert EligibilityService.is_employee_eligible_for_period(sanjota, date(2026, 12, 1), date(2026, 12, 31), hist_map) is False

        # Prevent assignment of inactive employee
        blocked = False
        try:
            EligibilityService.assert_employee_eligible_for_assignment(
                db, raj, date(2026, 11, 16), date(2026, 11, 30), hist_map
            )
        except HTTPException:
            blocked = True
        assert blocked, "Inactive employee assignment must be blocked with HTTPException"
        print("  [PASS] Raj Singh & Sanjota preserved in DB, active in Oct, inactive from Nov 1 onward, blocked from new assignments.")

        print("=== 2. HISTORICAL REGRESSION VALIDATION (SEP 2026 & OCT 2026) ===")
        dash_sep = build_dashboard(db, month="2026-09")
        assert dash_sep.kpis.total_revenue == 838800.0, f"Sep rev mismatch: {dash_sep.kpis.total_revenue}"
        assert dash_sep.kpis.beds_sold == 389.0, f"Sep beds mismatch: {dash_sep.kpis.beds_sold}"
        assert dash_sep.kpis.overall_target == 1315000.0, f"Sep target mismatch: {dash_sep.kpis.overall_target}"
        assert dash_sep.kpis.active_rms == 11, f"Sep active_rms mismatch: {dash_sep.kpis.active_rms}"
        sep_teams = {t.team_name: (t.team_leader_name, t.team_size, t.team_target, t.team_revenue) for t in dash_sep.team_leader_tracker}
        assert sep_teams["Team Sanjota"] == ("Sanjota", 4, 510000.0, 401300.0), f"Sep Team Sanjota mismatch: {sep_teams.get('Team Sanjota')}"
        assert sep_teams["Team Kesava"] == ("Kesava", 4, 505000.0, 325000.0), f"Sep Team Kesava mismatch: {sep_teams.get('Team Kesava')}"

        dash_oct = build_dashboard(db, month="2026-10")
        assert dash_oct.kpis.total_revenue == 1073400.0, f"Oct rev mismatch: {dash_oct.kpis.total_revenue}"
        assert dash_oct.kpis.beds_sold == 492.0, f"Oct beds mismatch: {dash_oct.kpis.beds_sold}"
        assert dash_oct.kpis.overall_target == 1490000.0, f"Oct target mismatch: {dash_oct.kpis.overall_target}"
        assert dash_oct.kpis.active_rms == 23, f"Oct active_rms mismatch: {dash_oct.kpis.active_rms}"
        oct_teams = {t.team_name: (t.team_leader_name, t.team_size, t.team_target, t.team_revenue) for t in dash_oct.team_leader_tracker}
        assert oct_teams["Team Sanjota"] == ("Sanjota", 5, 470000.0, 363000.0)
        assert oct_teams["Team Kesava"] == ("Kesava", 5, 470000.0, 334400.0)
        assert oct_teams["Team Goutham"] == ("Goutham N", 5, 275000.0, 227000.0)
        assert oct_teams["Team Arun"] == ("Arun N", 5, 275000.0, 144000.0)
        assert any(p.rm_name == "Raj Singh" and p.revenue == 23000.0 for p in dash_oct.performance_table), "Raj Singh historical Oct performance must be preserved"
        print("  [PASS] September 2026 and October 2026 historical reports match baseline 100%.")

        print("=== 3. NOVEMBER FIRST HALF (NOV 1–15, 2026) VALIDATION ===")
        dash_h1 = build_dashboard(db, month="2026-11", period_code="2026-11-H1")
        assert dash_h1.kpis.overall_target == 690000.0, f"H1 target expected 690000.0, got {dash_h1.kpis.overall_target}"
        assert dash_h1.kpis.active_rms == 18, f"H1 active RMs expected 18, got {dash_h1.kpis.active_rms}"
        assert not any(p.rm_name in ("Raj Singh", "Sanjota", "Chaithra") for p in dash_h1.performance_table), "Raj Singh, Sanjota & Chaithra must be excluded in H1"
        assert dash_h1.kpis.total_rm_incentives == 34000.0, f"H1 RM incentives expected 34000.0, got {dash_h1.kpis.total_rm_incentives}"
        print("  [PASS] November First Half (Nov 1–15) validated (18 active RMs, ₹6,90,000 target, ₹34,000 RM incentives, Raj Singh, Sanjota & Chaithra excluded).")

        print("=== 4. NOVEMBER SECOND HALF (NOV 16–30, 2026) VALIDATION ===")
        dash_h2 = build_dashboard(db, month="2026-11", period_code="2026-11-H2")
        assert dash_h2.kpis.overall_target == 820000.0, f"H2 target expected 820000.0, got {dash_h2.kpis.overall_target}"
        assert dash_h2.kpis.active_rms == 16, f"H2 active RMs expected 16, got {dash_h2.kpis.active_rms}"
        assert len(dash_h2.performance_table) == 16, f"H2 performance table expected 16 employees, got {len(dash_h2.performance_table)}"
        assert not any(p.rm_name in ("Raj Singh", "Sanjota", "Chaithra", "Pavan Tavarageri", "Midabalam Manasa") for p in dash_h2.performance_table), "Raj Singh, Sanjota, Chaithra, Pavan Tavarageri & Midabalam Manasa must be excluded in H2"
        assert not any(
            m.name in ("Pavan Tavarageri", "Midabalam Manasa")
            for t in dash_h2.team_leader_tracker
            for m in t.team_members
        ), "Pavan Tavarageri & Midabalam Manasa must not appear in H2 team tracker"

        h2_teams = {t.team_name: (t.team_leader_name, t.team_size, t.team_target) for t in dash_h2.team_leader_tracker}
        assert h2_teams["Team Goutham"] == ("Goutham N", 4, 140000.0), f"H2 Team Goutham mismatch: {h2_teams.get('Team Goutham')}"
        assert h2_teams["Team Arun"] == ("Arun N", 4, 140000.0), f"H2 Team Arun mismatch: {h2_teams.get('Team Arun')}"
        assert h2_teams["Team Keshav"] == ("Kesava", 4, 180000.0), f"H2 Team Keshav mismatch: {h2_teams.get('Team Keshav')}"
        assert h2_teams["Team Madhav"] == ("Madhava R", 4, 360000.0), f"H2 Team Madhav mismatch: {h2_teams.get('Team Madhav')}"
        print("  [PASS] November Second Half (Nov 16–30) validated (16 employees, ₹8,20,000 aggregate target across 4 teams, Pavan Tavarageri & Midabalam Manasa excluded).")

        print("=== 5. SECOND-HALF RM & TL INCENTIVE SLAB CALCULATION SCENARIOS ===")
        p_h2 = db.query(PeriodConfiguration).filter(PeriodConfiguration.period_code == "2026-11-H2").first()
        h2_slabs = db.query(PeriodIncentiveConfiguration).filter(PeriodIncentiveConfiguration.period_id == p_h2.id).all()
        h2_team_cfgs = {
            tc.team_name: tc
            for tc in db.query(PeriodTeamTargetConfiguration).filter(PeriodTeamTargetConfiguration.period_id == p_h2.id).all()
        }

        # RM ₹35,000 slab -> ₹6,000
        assert evaluate_rm_incentive_from_slabs(35000.0, 34999.0, h2_slabs)[0] == 0.0
        assert evaluate_rm_incentive_from_slabs(35000.0, 35000.0, h2_slabs)[0] == 6000.0
        assert evaluate_rm_incentive_from_slabs(35000.0, 50000.0, h2_slabs)[0] == 6000.0

        # RM ₹55,000 slab -> ₹10,000 (must not receive ₹6,000 if achieving ₹40,000!)
        assert evaluate_rm_incentive_from_slabs(55000.0, 40000.0, h2_slabs)[0] == 0.0
        assert evaluate_rm_incentive_from_slabs(55000.0, 55000.0, h2_slabs)[0] == 10000.0
        assert evaluate_rm_incentive_from_slabs(55000.0, 75000.0, h2_slabs)[0] == 10000.0

        # RM ₹90,000 slab -> ₹20,000 (must not receive ₹10,000 if achieving ₹60,000!)
        assert evaluate_rm_incentive_from_slabs(90000.0, 60000.0, h2_slabs)[0] == 0.0
        assert evaluate_rm_incentive_from_slabs(90000.0, 90000.0, h2_slabs)[0] == 20000.0
        assert evaluate_rm_incentive_from_slabs(90000.0, 120000.0, h2_slabs)[0] == 20000.0

        # TL ₹20,000 at >= 100% of team aggregate target
        for t_name, expected_agg in [
            ("Team Goutham", 140000.0),
            ("Team Arun", 140000.0),
            ("Team Keshav", 180000.0),
            ("Team Madhav", 360000.0),
        ]:
            tc = h2_team_cfgs[t_name]
            assert tc.aggregate_target == expected_agg
            inc_below, status_below, *_ = evaluate_tl_incentive_from_slabs(expected_agg, expected_agg - 1000.0, tc, h2_slabs)
            inc_exact, status_exact, *_ = evaluate_tl_incentive_from_slabs(expected_agg, expected_agg, tc, h2_slabs)
            inc_above, status_above, *_ = evaluate_tl_incentive_from_slabs(expected_agg, expected_agg + 25000.0, tc, h2_slabs)
            assert inc_below == 0.0 and status_below == "Not Eligible"
            assert inc_exact == 20000.0 and status_exact == "Eligible"
            assert inc_above == 20000.0 and status_above == "Eligible"
        print("  [PASS] All Second-Half RM & Team Leader incentive slab scenarios validated.")

        print("=== 6. COMBINED NOVEMBER DASHBOARD & FUTURE MONTH VALIDATION ===")
        dash_comb = build_dashboard(db, month="2026-11")
        assert len(dash_comb.period_breakdowns) == 2, "Combined November must include 2 period breakdowns"
        assert dash_comb.kpis.total_revenue == dash_h1.kpis.total_revenue + dash_h2.kpis.total_revenue, "Combined revenue must equal H1 + H2 without double counting"
        assert dash_comb.kpis.overall_target == dash_h1.kpis.overall_target + dash_h2.kpis.overall_target, "Combined target must equal H1 + H2"
        assert dash_comb.kpis.total_incentives == dash_h1.kpis.total_incentives + dash_h2.kpis.total_incentives, "Combined incentives must equal H1 + H2"
        assert not any(p.rm_name in ("Raj Singh", "Sanjota") for p in dash_comb.performance_table), "Raj Singh & Sanjota must be excluded from Combined November"

        dash_dec = build_dashboard(db, month="2026-12")
        assert not any(p.rm_name in ("Raj Singh", "Sanjota") for p in dash_dec.performance_table), "Raj Singh & Sanjota must be excluded from December"

        print("=== 7. AUDITABILITY & TRACEABILITY VALIDATION ===")
        calc_count = db.query(PerformanceCalculationRecord).count()
        audit_count = db.query(ConfigurationAuditHistory).count()
        hist_count = db.query(EmployeeEmploymentHistory).count()
        assert calc_count > 0, "PerformanceCalculationRecord must contain auditable calculation records"
        assert audit_count > 0, "ConfigurationAuditHistory must contain configuration audit records"
        assert hist_count > 0, "EmployeeEmploymentHistory must contain employment status records"
        print(f"  [PASS] Audit tables populated: {calc_count} calculation records, {audit_count} config audit logs, {hist_count} employment history rows.")

        print("\nALL 17 ACCEPTANCE CRITERIA PASSED SUCCESSFULLY!")
    finally:
        db.close()


if __name__ == "__main__":
    run_all_validations()

