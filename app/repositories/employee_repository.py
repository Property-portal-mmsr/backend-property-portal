from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.utils.password import hash_password


class EmployeeRepository:
    @staticmethod
    def get_all(db: Session) -> List[Employee]:
        return db.query(Employee).all()

    @staticmethod
    def get_by_emp_id(db: Session, emp_id: str) -> Optional[Employee]:
        return db.query(Employee).filter(Employee.emp_id == emp_id).first()

    @staticmethod
    def get_by_id(db: Session, id_val: int) -> Optional[Employee]:
        return db.query(Employee).filter(Employee.id == id_val).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[Employee]:
        return db.query(Employee).filter(Employee.email == email).first()

    @staticmethod
    def create(
        db: Session, emp_data: EmployeeCreate, password: Optional[str] = "123456"
    ) -> Employee:
        hashed_pwd = hash_password(password or "123456")
        new_emp = Employee(
            emp_id=emp_data.id or f"EMP{str(db.query(Employee).count() + 1).zfill(3)}",
            name=emp_data.name,
            email=emp_data.email or "",
            phone=emp_data.phone or "",
            role=(emp_data.role or "EMPLOYEE").upper(),
            status=(emp_data.status or "ACTIVE").upper(),
            password_hash=hashed_pwd,
            password=hashed_pwd,
            must_change_password=True,
        )

        db.add(new_emp)
        db.commit()
        db.refresh(new_emp)
        return new_emp

    @staticmethod
    def update(db: Session, db_emp: Employee, update_data: EmployeeUpdate) -> Employee:
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, val in update_dict.items():
            if val is not None and hasattr(db_emp, key):
                if key in ("role", "status") and isinstance(val, str):
                    val = val.upper()
                setattr(db_emp, key, val)
        db.commit()
        db.refresh(db_emp)
        return db_emp

    @staticmethod
    def delete(db: Session, db_emp: Employee) -> None:
        db.delete(db_emp)
        db.commit()

    @staticmethod
    def seed_default_employees(db: Session) -> None:
        default_hashed = hash_password("Welcome@123")
        admin_hashed = hash_password("123456")

        # Clean up old dummy EMP00x test records
        try:
            db.query(Employee).filter(Employee.emp_id.like("EMP%")).delete(
                synchronize_session=False
            )
            db.commit()
        except Exception:
            db.rollback()

        defaults = [
            {
                "emp_id": "MMSR00",
                "name": "System Admin",
                "email": "admin@makemystay.ai",
                "phone": "9840000000",
                "role": "ADMIN",
                "status": "ACTIVE",
                "designation": "System Administrator",
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
                "password_hash": default_hashed,
                "password": default_hashed,
                "must_change_password": True,
            },
        ]

        for item in defaults:
            emp = EmployeeRepository.get_by_email(db, item["email"])
            if not emp:
                emp_by_id = (
                    db.query(Employee)
                    .filter(Employee.emp_id == item["emp_id"])
                    .first()
                )
                if not emp_by_id:
                    new_emp = Employee(**item)
                    db.add(new_emp)
                else:
                    emp_by_id.name = item["name"]
                    emp_by_id.email = item["email"]
                    emp_by_id.designation = item["designation"]
                    emp_by_id.role = item["role"]
            else:
                emp.name = item["name"]
                emp.emp_id = item["emp_id"]
                emp.designation = item["designation"]
                emp.role = item["role"]
                if not emp.password_hash and not emp.password:
                    emp.password_hash = item["password_hash"]
                    emp.password = item["password"]

        db.commit()


