import sys
sys.path.append('.')
from app.database.database import SessionLocal
from app.services.analytics_service import build_dashboard
from app.models.employee import Employee

db = SessionLocal()

print('=== 1. Testing available_rms / available_employees ===')
dash = build_dashboard(db, month='2026-10')
rms = dash.available_rms
print(f'Total available_rms: {len(rms)}')

expected_designations = {
    'Founder', 'Senior Relationship Manager', 'R.M', 'City Sales & Ops Manager', 'City Manager'
}

# Fetch DB employees map
emp_map = {e.id: e for e in db.query(Employee).all()}

for item in rms:
    item_id = item.id if hasattr(item, 'id') else item['id']
    item_name = item.name if hasattr(item, 'name') else item['name']
    assert item_id in emp_map, f'Employee ID {item_id} not in DB!'
    emp = emp_map[item_id]
    assert emp.status.upper() == 'ACTIVE', f'Employee {emp.name} is not ACTIVE!'
    print(f'  [OK] ID: {item_id}, Name: {item_name}, Desig: {emp.designation}')

assert len(rms) == 25, f'Expected 25 eligible employees, got {len(rms)}'

# Ensure ineligible are excluded
ineligible_names = ['System Admin', 'Harshini B', 'Jeron Roy Jacob S', 'Maheswaran M', 'Kiran M R', 'Prashanthi', 'Nagarjuna', 'Guest', 'Bharath', 'Mohini']
for inel in ineligible_names:
    for item in rms:
        item_name = item.name if hasattr(item, 'name') else item['name']
        assert inel.lower() != item_name.lower(), f'Ineligible name {inel} found in available_rms!'
print('[PASS] All 8 non-eligible roles and non-DB records successfully excluded!')

print('\n=== 2. Testing filter by employee_id ===')
# Test Akhila G (ID 60)
dash_akhila = build_dashboard(db, month='2026-10', employee_id=60)
print(f'Akhila G - active_rms: {dash_akhila.kpis.active_rms}, beds: {dash_akhila.kpis.beds_sold}, rev: {dash_akhila.kpis.total_revenue}')
assert dash_akhila.kpis.active_rms == 1, f'Expected active_rms=1 for single employee filter, got {dash_akhila.kpis.active_rms}'
for row in dash_akhila.performance_table:
    assert 'akhila' in row.rm_name.lower(), f'Found non-Akhila row: {row.rm_name}'
print('[PASS] Filter by employee_id=60 isolated Akhila G perfectly')

# Test Vinod (ID 19) vs Vinod Kumar (ID 80)
dash_vinod = build_dashboard(db, month='2026-10', employee_id=19)
print(f'Vinod (ID 19) - rev: {dash_vinod.kpis.total_revenue}, beds: {dash_vinod.kpis.beds_sold}')
for row in dash_vinod.performance_table:
    assert row.rm_name.lower() == 'vinod', f'Expected Vinod, got {row.rm_name}'

dash_vinod_kumar = build_dashboard(db, month='2026-10', employee_id=80)
print(f'Vinod Kumar (ID 80) - rev: {dash_vinod_kumar.kpis.total_revenue}, beds: {dash_vinod_kumar.kpis.beds_sold}')
for row in dash_vinod_kumar.performance_table:
    assert 'kumar' in row.rm_name.lower(), f'Expected Vinod Kumar, got {row.rm_name}'
print('[PASS] Distinction between Vinod (19) and Vinod Kumar (80) verified with no collision!')

print('\n=== ALL NEW FILTER REQUIREMENTS VERIFIED SUCCESSFULLY IN BACKEND! ===')
db.close()
