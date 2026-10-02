import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.append("/Users/maheswaranm/backend-property-portal")

from app.database.database import SessionLocal
from app.models.employee_monthly_target import EmployeeMonthlyTarget
from app.models.employee import Employee
from app.services.analytics_service import build_dashboard

db = SessionLocal()

# 1. Schema check
print("EmployeeMonthlyTarget columns:")
for col in EmployeeMonthlyTarget.__table__.columns:
    print(col.name, col.type)

# 2. Existing Sep 2026 targets
sep_targets = db.query(EmployeeMonthlyTarget).filter(
    EmployeeMonthlyTarget.month == "September",
    EmployeeMonthlyTarget.year == 2026
).all()

print("\nSeptember 2026 targets:")
sep_sum = 0
for t in sep_targets:
    print(f"Emp ID: {t.employee_id}, Target: {t.target}")
    sep_sum += t.target
print("Sep DB Sum:", sep_sum)

# 3. Existing Oct 2026 targets
oct_targets = db.query(EmployeeMonthlyTarget).filter(
    EmployeeMonthlyTarget.month == "October",
    EmployeeMonthlyTarget.year == 2026
).all()

print("\nOctober 2026 targets:")
oct_sum = 0
for t in oct_targets:
    print(f"Emp ID: {t.employee_id}, Target: {t.target}")
    oct_sum += t.target
print("Oct DB Sum:", oct_sum)

# Check for duplicates
print("\nChecking duplicates:")
for month, year, targets in [("September", 2026, sep_targets), ("October", 2026, oct_targets)]:
    emp_counts = {}
    for t in targets:
        emp_counts[t.employee_id] = emp_counts.get(t.employee_id, 0) + 1
    dups = {emp: count for emp, count in emp_counts.items() if count > 1}
    if dups:
        print(f"Duplicates in {month} {year}: {dups}")
    else:
        print(f"No duplicates in {month} {year}")

# Current Overall Target Calculation
print("\nDashboard overall_target:")
sep_dash = build_dashboard(db, month="2026-09")
print("Sep API overall_target:", sep_dash.kpis.overall_target)

oct_dash = build_dashboard(db, month="2026-10")
print("Oct API overall_target:", oct_dash.kpis.overall_target)
