import sys
sys.path.append(".")
from app.database.database import SessionLocal
from app.services.analytics_service import build_dashboard

db = SessionLocal()

def validate_all():
    print("Testing October 2026...")
    dash_oct = build_dashboard(db, month="2026-10")

    # RM Performance table revenue filter check
    for rm in dash_oct.performance_table:
        assert rm.revenue > 0, f"Found RM {rm.rm_name} with revenue <= 0: {rm.revenue}"
    print("[PASS] RM Performance Table: All RMs have Eligible Revenue > 0")

    # Check Kesava & Arun team additions in October 2026
    oct_kesava = next(t for t in dash_oct.team_leader_tracker if "Kesava" in t.team_leader_name)
    oct_kesava_member_names = [m.name.lower() for m in oct_kesava.team_members]
    assert any("manasa" in n for n in oct_kesava_member_names), "Manasa missing in Kesava Oct team"
    assert any("pavani" in n for n in oct_kesava_member_names), "Pavani missing in Kesava Oct team"
    assert any("vinod" in n for n in oct_kesava_member_names), "Vinod missing in Kesava Oct team"
    print("[PASS] Kesava team has Manasa, Pavani, Vinod Kumar in October 2026")

    oct_arun = next(t for t in dash_oct.team_leader_tracker if "Arun" in t.team_leader_name)
    oct_arun_member_names = [m.name.lower() for m in oct_arun.team_members]
    assert any("raj singh" in n for n in oct_arun_member_names), "Raj Singh missing in Arun Oct team"
    assert any("dheeraj" in n for n in oct_arun_member_names), "Dheeraj missing in Arun Oct team"
    print("[PASS] Arun team has Raj Singh, Dheeraj Yadav in October 2026")

    print("\nTesting September 2026 (Historical)...")
    dash_sep = build_dashboard(db, month="2026-09")

    sep_kesava = next(t for t in dash_sep.team_leader_tracker if "Kesava" in t.team_leader_name)
    sep_kesava_member_names = [m.name.lower() for m in sep_kesava.team_members]
    assert not any("manasa" in n for n in sep_kesava_member_names), "Manasa incorrectly in Kesava Sep team"
    assert not any("pavani" in n for n in sep_kesava_member_names), "Pavani incorrectly in Kesava Sep team"
    print("[PASS] Historical September team structure unchanged for Kesava")

    sep_arun = next((t for t in dash_sep.team_leader_tracker if "Arun" in t.team_leader_name), None)
    if sep_arun:
        sep_arun_member_names = [m.name.lower() for m in sep_arun.team_members]
        assert not any("raj singh" in n for n in sep_arun_member_names), "Raj Singh incorrectly in Arun Sep team"
        assert not any("dheeraj" in n for n in sep_arun_member_names), "Dheeraj incorrectly in Arun Sep team"
    print("[PASS] Historical September team structure unchanged for Arun")

    # Abhishek in Sanjota, Pratima in Kesava in Sep
    sep_sanjota = next(t for t in dash_sep.team_leader_tracker if "Sanjota" in t.team_leader_name)
    assert any("abhishek" in m.name.lower() for m in sep_sanjota.team_members), "Abhishek missing in Sep Sanjota"
    assert any("pratima" in m.name.lower() for m in sep_kesava.team_members), "Pratima missing in Sep Kesava"
    print("[PASS] Historical September Abhishek/Pratima assignments preserved")

    # Team Revenue and Achievement checks
    for t in dash_oct.team_leader_tracker:
        expected_overall_rev = t.team_member_revenue + (0 if t.leader_in_members else t.team_leader_revenue)
        assert abs(t.team_revenue - expected_overall_rev) < 1e-4, f"Team revenue mismatch for {t.team_leader_name}: got {t.team_revenue}, expected {expected_overall_rev}"
        expected_ach = (t.team_revenue / t.team_target * 100) if t.team_target > 0 else 0
        assert abs(t.achievement_pct - expected_ach) < 0.1, f"Achievement mismatch for {t.team_leader_name}: got {t.achievement_pct}, expected {expected_ach}"
    print("[PASS] Overall Team Revenue and Team Achievement % correctly calculated for all teams")

    print("\nALL 9 VALIDATION CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    validate_all()
