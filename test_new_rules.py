import sys
import datetime
sys.path.append("/Users/maheswaranm/backend-property-portal")
from app.database.database import SessionLocal
from app.services.analytics_service import build_dashboard
from app.models.employee import Employee

db = SessionLocal()

def run_tests():
    ankit = db.query(Employee).filter(Employee.name == "Ankit Prajapati").first()
    pavan = db.query(Employee).filter(Employee.name == "Pavan Tavarageri").first()
    
    old_ankit_date = ankit.joining_date if ankit else None
    old_pavan_date = pavan.joining_date if pavan else None
    
    if ankit:
        ankit.joining_date = "2026-10-01"
    if pavan:
        pavan.joining_date = "2026-10-01"
    db.commit()
    
    try:
        print("Testing April 2026 exclusions...")
        dash_apr = build_dashboard(db, month="2026-04")
        assert not any(rm.rm_name == "Ankit Prajapati" for rm in dash_apr.performance_table), "Ankit should be excluded in April"
        assert not any(rm.rm_name == "Pavan Tavarageri" for rm in dash_apr.performance_table), "Pavan should be excluded in April"
        print("Test 1 Passed")

        print("Testing August 2026 exclusions...")
        dash_aug = build_dashboard(db, month="2026-08")
        assert not any(rm.rm_name == "Ankit Prajapati" for rm in dash_aug.performance_table), "Ankit should be excluded in August"
        assert not any(rm.rm_name == "Pavan Tavarageri" for rm in dash_aug.performance_table), "Pavan should be excluded in August"
        print("Test 2 Passed")

        print("Testing September 2026 exclusions...")
        dash_sep = build_dashboard(db, month="2026-09")
        assert not any(rm.rm_name == "Ankit Prajapati" for rm in dash_sep.performance_table), "Ankit should be excluded in September"
        assert not any(rm.rm_name == "Pavan Tavarageri" for rm in dash_sep.performance_table), "Pavan should be excluded in September"
        print("Test 3 Passed")

        print("Testing October 2026 inclusions...")
        dash_oct = build_dashboard(db, month="2026-10")
        oct_sanjota_members = [m.name for t in dash_oct.team_leader_tracker if t.team_leader_name == "Sanjota" for m in t.team_members]
        has_ankit = "Ankit Prajapati" in oct_sanjota_members
        has_pavan = "Pavan Tavarageri" in oct_sanjota_members
        assert has_ankit, "Ankit should be included in October"
        assert has_pavan, "Pavan should be included in October"
        print("Test 4 Passed")

        print("Testing Overall Target...")
        assert dash_sep.kpis.overall_target == 1315000.0, f"Sep Overall Target was {dash_sep.kpis.overall_target}, expected 1315000.0"
        print("Test 5 Passed")
        
        assert dash_oct.kpis.overall_target == 1215000.0, f"Oct Overall Target was {dash_oct.kpis.overall_target}, expected 1215000.0"
        print("Test 6 Passed")

        print("Testing Team Member count...")
        sep_sanjota_members = [m.name for t in dash_sep.team_leader_tracker if t.team_leader_name == "Sanjota" for m in t.team_members]
        assert "Ankit Prajapati" not in sep_sanjota_members, "Ankit should not be in Sanjota's team in Sep"
        assert "Pavan Tavarageri" not in sep_sanjota_members, "Pavan should not be in Sanjota's team in Sep"
        print("Test 7 Passed")

        assert "Ankit Prajapati" in oct_sanjota_members, "Ankit should be in Sanjota's team in Oct"
        assert "Pavan Tavarageri" in oct_sanjota_members, "Pavan should be in Sanjota's team in Oct"
        print("Test 8 Passed")

        print("Testing available months...")
        dash_unfiltered = build_dashboard(db)
        frozen = {"2026-04", "2026-05", "2026-06", "2026-07", "2026-08"}
        assert not any(m in frozen for m in dash_unfiltered.available_months), "Frozen months are shown"
        assert "2026-09" in dash_unfiltered.available_months, "Sep 2026 is missing"
        assert "2026-10" in dash_unfiltered.available_months, "Oct 2026 is missing"
        print("Test 12 Passed")

        print("Testing All Months accumulation...")
        assert dash_unfiltered.kpis.overall_target == 1215000.0, f"All time target was {dash_unfiltered.kpis.overall_target}"
        print("Test 13 Passed")

        print("All tests successfully ran!")
    finally:
        if ankit:
            ankit.joining_date = old_ankit_date
        if pavan:
            pavan.joining_date = old_pavan_date
        db.commit()
        print("Restored DB dates")

if __name__ == "__main__":
    run_tests()
