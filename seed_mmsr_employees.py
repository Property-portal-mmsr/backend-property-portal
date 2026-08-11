"""
MakeMyStay Realty (MMSR) Employee Database Seeder

This script clears old dummy test records (EMP00x) and seeds all 26 real
company employees (MMSR01 to MMSR26) + the System Admin account (MMSR00)
with generated company emails, standard phone extensions, titles/designations,
departments, reporting managers, joining dates, and secure bcrypt-hashed passwords.

Usage:
    python seed_mmsr_employees.py
"""

import sys
import os

# Ensure app directory is on path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.database import SessionLocal, engine, Base
from app.models.employee import Employee
from app.models.employee_monthly_target import EmployeeMonthlyTarget
from app.utils.password import hash_password


def seed_company_roster():
    print("Connecting to database and verifying schema...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        print("1. Cleaning up old dummy test employees (EMP00x)...")
        deleted_count = (
            db.query(Employee)
            .filter(Employee.emp_id.like("EMP%"))
            .delete(synchronize_session=False)
        )
        db.commit()
        print(f"   -> Removed {deleted_count} dummy employee record(s).")

        print("2. Generating hashed passwords...")
        default_hashed = hash_password("Welcome@123")
        admin_hashed = hash_password("123456")

        print("3. Seeding 26 real MakeMyStay Realty employees (MMSR00 - MMSR26)...")

        roster = [
            {
                "emp_id": "MMSR00",
                "name": "System Admin",
                "email": "admin@makemystay.ai",
                "phone": "9840000000",
                "role": "ADMIN",
                "status": "ACTIVE",
                "designation": "System Administrator",
                "department": "Management",
                "reporting_manager": "None",
                "joining_date": "2023-01-01",
                "password_hash": admin_hashed,
                "password": admin_hashed,
                "must_change_password": False,
            },
            {
                "emp_id": "MMSR01",
                "name": "Madhava R",
                "email": "madhava@makemystay.ai",
                "phone": "9840000001",
                "role": "ADMIN",
                "status": "ACTIVE",
                "designation": "Founder",
                "department": "Management",
                "reporting_manager": "None",
                "joining_date": "2023-01-01",
                "password_hash": admin_hashed,
                "password": admin_hashed,
                "must_change_password": False,
            },
            {
                "emp_id": "MMSR02",
                "name": "Arun N",
                "email": "arun@makemystay.ai",
                "phone": "9840000002",
                "role": "EMPLOYEE",
                "status": "ACTIVE",
                "designation": "City Manager",
                "department": "Operations",
                "reporting_manager": "Madhava R",
                "joining_date": "2023-06-01",
                "password_hash": default_hashed,
                "password": default_hashed,
                "must_change_password": True,
            },
            {
                "emp_id": "MMSR03",
                "name": "Kiran M R",
                "email": "kiran@makemystay.ai",
                "phone": "9840000003",
                "role": "EMPLOYEE",
                "status": "ACTIVE",
                "designation": "Business Development Manager",
                "department": "Sales",
                "reporting_manager": "Madhava R",
                "joining_date": "2023-06-15",
                "password_hash": default_hashed,
                "password": default_hashed,
                "must_change_password": True,
            },
            {
                "emp_id": "MMSR04",
                "name": "Sanjota",
                "email": "sanjota@makemystay.ai",
                "phone": "9840000004",
                "role": "EMPLOYEE",
                "status": "ACTIVE",
                "designation": "City Manager",
                "department": "Operations",
                "reporting_manager": "Madhava R",
                "joining_date": "2023-07-01",
                "password_hash": default_hashed,
                "password": default_hashed,
                "must_change_password": True,
            },
            {
                "emp_id": "MMSR07",
                "name": "Chethan P",
                "email": "chethan@makemystay.ai",
                "phone": "9840000007",
                "role": "EMPLOYEE",
                "status": "ACTIVE",
                "designation": "Senior Relationship Manager",
                "department": "Sales",
                "reporting_manager": "Arun N",
                "joining_date": "2023-08-01",
                "password_hash": default_hashed,
                "password": default_hashed,
                "must_change_password": True,
            },
            {
                "emp_id": "MMSR08",
                "name": "Gowtham N",
                "email": "gowtham@makemystay.ai",
                "phone": "9840000008",
                "role": "EMPLOYEE",
                "status": "ACTIVE",
                "designation": "City Sales & Ops Manager",
                "department": "Operations",
                "reporting_manager": "Arun N",
                "joining_date": "2023-08-15",
                "password_hash": default_hashed,
                "password": default_hashed,
                "must_change_password": True,
            },
            {
                "emp_id": "MMSR09",
                "name": "Pritish Kumar Jena",
                "email": "pritish@makemystay.ai",
                "phone": "9840000009",
                "role": "EMPLOYEE",
                "status": "ACTIVE",
                "designation": "Senior Relationship Manager",
                "department": "Sales",
                "reporting_manager": "Sanjota",
                "joining_date": "2023-09-01",
                "password_hash": default_hashed,
                "password": default_hashed,
                "must_change_password": True,
            },
            {
                "emp_id": "MMSR10",
                "name": "Jeron Roy Jacob S",
                "email": "jeron@makemystay.ai",
                "phone": "9840000010",
                "role": "EMPLOYEE",
                "status": "ACTIVE",
                "designation": "Full Stack Developer",
                "department": "Technology",
                "reporting_manager": "Madhava R",
                "joining_date": "2023-10-01",
                "password_hash": default_hashed,
                "password": default_hashed,
                "must_change_password": True,
            },
            {
                "emp_id": "MMSR11",
                "name": "Maheswaran M",
                "email": "mahes@makemystay.ai",
                "phone": "9840000011",
                "role": "ADMIN",
                "status": "ACTIVE",
                "designation": "Full Stack Developer",
                "department": "Technology",
                "reporting_manager": "Madhava R",
                "joining_date": "2023-10-01",
                "password_hash": admin_hashed,
                "password": admin_hashed,
                "must_change_password": False,
            },
            {
                "emp_id": "MMSR12",
                "name": "Harshini B",
                "email": "harshini@makemystay.ai",
                "phone": "9840000012",
                "role": "EMPLOYEE",
                "status": "ACTIVE",
                "designation": "Tech Developer",
                "department": "Technology",
                "reporting_manager": "Maheswaran M",
                "joining_date": "2023-11-01",
                "password_hash": default_hashed,
                "password": default_hashed,
                "must_change_password": True,
            },
            {
                "emp_id": "MMSR13",
                "name": "Prashanthi",
                "email": "prashanthi@makemystay.ai",
                "phone": "9840000013",
                "role": "EMPLOYEE",
                "status": "ACTIVE",
                "designation": "Marketing",
                "department": "Marketing",
                "reporting_manager": "Madhava R",
                "joining_date": "2023-11-15",
                "password_hash": default_hashed,
                "password": default_hashed,
                "must_change_password": True,
            },
            {
                "emp_id": "MMSR14",
                "name": "Naveen",
                "email": "naveen@makemystay.ai",
                "phone": "9840000014",
                "role": "EMPLOYEE",
                "status": "ACTIVE",
                "designation": "Senior Relationship Manager",
                "department": "Sales",
                "reporting_manager": "Arun N",
                "joining_date": "2023-12-01",
                "password_hash": default_hashed,
                "password": default_hashed,
                "must_change_password": True,
            },
            {
                "emp_id": "MMSR15",
                "name": "Kalyan Kumar Reddy",
                "email": "kalyan@makemystay.ai",
                "phone": "9840000015",
                "role": "EMPLOYEE",
                "status": "ACTIVE",
                "designation": "Senior Relationship Manager",
                "department": "Sales",
                "reporting_manager": "Sanjota",
                "joining_date": "2023-12-15",
                "password_hash": default_hashed,
                "password": default_hashed,
                "must_change_password": True,
            },
            {
                "emp_id": "MMSR16",
                "name": "Abhishek",
                "email": "abhishek@makemystay.ai",
                "phone": "9840000016",
                "role": "EMPLOYEE",
                "status": "ACTIVE",
                "designation": "Sr. R.M",
                "department": "Sales",
                "reporting_manager": "Arun N",
                "joining_date": "2024-01-01",
                "password_hash": default_hashed,
                "password": default_hashed,
                "must_change_password": True,
            },
            {
                "emp_id": "MMSR17",
                "name": "Pratima",
                "email": "pratima@makemystay.ai",
                "phone": "9840000017",
                "role": "EMPLOYEE",
                "status": "ACTIVE",
                "designation": "Sr. R.M",
                "department": "Sales",
                "reporting_manager": "Sanjota",
                "joining_date": "2024-01-15",
                "password_hash": default_hashed,
                "password": default_hashed,
                "must_change_password": True,
            },
            {
                "emp_id": "MMSR18",
                "name": "Kesava",
                "email": "kesava@makemystay.ai",
                "phone": "9840000018",
                "role": "EMPLOYEE",
                "status": "ACTIVE",
                "designation": "City Sales & Ops Manager",
                "department": "Operations",
                "reporting_manager": "Arun N",
                "joining_date": "2024-02-01",
                "password_hash": default_hashed,
                "password": default_hashed,
                "must_change_password": True,
            },
            {
                "emp_id": "MMSR19",
                "name": "Sameer",
                "email": "sameer@makemystay.ai",
                "phone": "9840000019",
                "role": "EMPLOYEE",
                "status": "ACTIVE",
                "designation": "R.M",
                "department": "Sales",
                "reporting_manager": "Chethan P",
                "joining_date": "2024-02-15",
                "password_hash": default_hashed,
                "password": default_hashed,
                "must_change_password": True,
            },
            {
                "emp_id": "MMSR20",
                "name": "Vinod",
                "email": "vinod@makemystay.ai",
                "phone": "9840000020",
                "role": "EMPLOYEE",
                "status": "ACTIVE",
                "designation": "R.M",
                "department": "Sales",
                "reporting_manager": "Chethan P",
                "joining_date": "2024-03-01",
                "password_hash": default_hashed,
                "password": default_hashed,
                "must_change_password": True,
            },
            {
                "emp_id": "MMSR21",
                "name": "Likitha",
                "email": "likitha@makemystay.ai",
                "phone": "9840000021",
                "role": "EMPLOYEE",
                "status": "ACTIVE",
                "designation": "R.M",
                "department": "Sales",
                "reporting_manager": "Pritish Kumar Jena",
                "joining_date": "2024-03-15",
                "password_hash": default_hashed,
                "password": default_hashed,
                "must_change_password": True,
            },
            {
                "emp_id": "MMSR22",
                "name": "Akhila",
                "email": "akhila@makemystay.ai",
                "phone": "9840000022",
                "role": "EMPLOYEE",
                "status": "ACTIVE",
                "designation": "R.M",
                "department": "Sales",
                "reporting_manager": "Pritish Kumar Jena",
                "joining_date": "2024-04-01",
                "password_hash": default_hashed,
                "password": default_hashed,
                "must_change_password": True,
            },
            {
                "emp_id": "MMSR23",
                "name": "Bharath",
                "email": "bharath@makemystay.ai",
                "phone": "9840000023",
                "role": "EMPLOYEE",
                "status": "ACTIVE",
                "designation": "Sr. R.M",
                "department": "Sales",
                "reporting_manager": "Arun N",
                "joining_date": "2024-04-15",
                "password_hash": default_hashed,
                "password": default_hashed,
                "must_change_password": True,
            },
            {
                "emp_id": "MMSR24",
                "name": "Priyanka",
                "email": "priyanka@makemystay.ai",
                "phone": "9840000024",
                "role": "EMPLOYEE",
                "status": "ACTIVE",
                "designation": "Business Development Executive",
                "department": "Sales",
                "reporting_manager": "Kiran M R",
                "joining_date": "2024-05-01",
                "password_hash": default_hashed,
                "password": default_hashed,
                "must_change_password": True,
            },
            {
                "emp_id": "MMSR25",
                "name": "Nagarjuna",
                "email": "nagarjuna@makemystay.ai",
                "phone": "9840000025",
                "role": "EMPLOYEE",
                "status": "ACTIVE",
                "designation": "BDA & Ops Manager",
                "department": "Operations",
                "reporting_manager": "Gowtham N",
                "joining_date": "2024-05-15",
                "password_hash": default_hashed,
                "password": default_hashed,
                "must_change_password": True,
            },
            {
                "emp_id": "MMSR26",
                "name": "Lukmanul Hateem M A",
                "email": "lukmanul@makemystay.ai",
                "phone": "9840000026",
                "role": "EMPLOYEE",
                "status": "ACTIVE",
                "designation": "R.M",
                "department": "Sales",
                "reporting_manager": "Naveen",
                "joining_date": "2024-06-01",
                "password_hash": default_hashed,
                "password": default_hashed,
                "must_change_password": True,
            },
        ]

        created_count = 0
        updated_count = 0

        for item in roster:
            emp = (
                db.query(Employee)
                .filter(Employee.email == item["email"])
                .first()
            )
            if not emp:
                emp_by_id = (
                    db.query(Employee)
                    .filter(Employee.emp_id == item["emp_id"])
                    .first()
                )
                if not emp_by_id:
                    new_emp = Employee(**item)
                    db.add(new_emp)
                    created_count += 1
                else:
                    emp_by_id.name = item["name"]
                    emp_by_id.email = item["email"]
                    emp_by_id.designation = item["designation"]
                    emp_by_id.department = item["department"]
                    emp_by_id.reporting_manager = item["reporting_manager"]
                    emp_by_id.joining_date = item["joining_date"]
                    emp_by_id.role = item["role"]
                    emp_by_id.must_change_password = item[
                        "must_change_password"
                    ]
                    updated_count += 1
            else:
                emp.name = item["name"]
                emp.emp_id = item["emp_id"]
                emp.designation = item["designation"]
                emp.department = item["department"]
                emp.reporting_manager = item["reporting_manager"]
                emp.joining_date = item["joining_date"]
                emp.role = item["role"]
                emp.must_change_password = item["must_change_password"]
                if not emp.password_hash and not emp.password:
                    emp.password_hash = item["password_hash"]
                    emp.password = item["password"]
                updated_count += 1

        db.commit()
        print(
            f"   -> Successfully seeded MakeMyStay Realty employee database!"
        )
        print(
            f"   -> New records added: {created_count} | Updated records: {updated_count}"
        )

        print("4. Seeding month-specific targets (1L for August 2026, 0 for July 2026)...")
        all_emps = db.query(Employee).all()
        targets_created = 0
        for e in all_emps:
            # Set base default target to 0
            e.monthly_target = 0

            # Seed August 2026 target (1,00,000)
            aug_target = db.query(EmployeeMonthlyTarget).filter_by(employee_id=e.id, month=8, year=2026).first()
            if not aug_target:
                db.add(EmployeeMonthlyTarget(employee_id=e.id, month=8, year=2026, target=100000.0))
                targets_created += 1
            else:
                aug_target.target = 100000.0

            # Seed July 2026 target (0)
            jul_target = db.query(EmployeeMonthlyTarget).filter_by(employee_id=e.id, month=7, year=2026).first()
            if not jul_target:
                db.add(EmployeeMonthlyTarget(employee_id=e.id, month=7, year=2026, target=0.0))
                targets_created += 1
            else:
                jul_target.target = 0.0

        db.commit()
        print(f"   -> Successfully mapped {targets_created} monthly targets for all employees!")

        print("\nSummary of Key Credentials:")
        print("   * Admin Accounts (no forced password change):")
        print("     - admin@makemystay.ai (System Admin) | Password: 123456")
        print("     - madhava@makemystay.ai (Founder) | Password: 123456")
        print(
            "     - mahes@makemystay.ai (Full Stack Developer) | Password: 123456"
        )
        print("   * All Other Employees (forced password change on first login):")
        print(
            "     - e.g. jeron@makemystay.ai, arun@makemystay.ai | Initial Password: Welcome@123"
        )

    except Exception as e:
        db.rollback()
        print(f"Error seeding employee roster: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_company_roster()
