from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeResponse
from app.repositories.employee_repository import EmployeeRepository
from app.utils.password import hash_password


class EmployeeService:
    @staticmethod
    def get_all_employees(db: Session) -> List[EmployeeResponse]:
        emps = EmployeeRepository.get_all(db)
        return [EmployeeResponse.from_db(e) for e in emps]

    @staticmethod
    def get_employee_by_emp_id(db: Session, emp_id: str) -> Optional[EmployeeResponse]:
        emp = EmployeeRepository.get_by_emp_id(db, emp_id)
        if not emp:
            return None
        return EmployeeResponse.from_db(emp)

    @staticmethod
    def create_employee(db: Session, emp_data: EmployeeCreate) -> EmployeeResponse:
        new_emp = EmployeeRepository.create(
            db, emp_data, password=emp_data.password or "123456"
        )
        return EmployeeResponse.from_db(new_emp)

    @staticmethod
    def update_employee(
        db: Session, emp_id: str, update_data: EmployeeUpdate
    ) -> Optional[EmployeeResponse]:
        emp = EmployeeRepository.get_by_emp_id(db, emp_id)
        if not emp:
            return None
        if update_data.password:
            hashed = hash_password(update_data.password)
            emp.password = hashed
            emp.password_hash = hashed
        updated_emp = EmployeeRepository.update(db, emp, update_data)
        return EmployeeResponse.from_db(updated_emp)

    @staticmethod
    def reset_password(db: Session, emp_id: str, new_password: str) -> bool:
        emp = EmployeeRepository.get_by_emp_id(db, emp_id)
        if not emp:
            return False
        hashed = hash_password(new_password)
        emp.password = hashed
        emp.password_hash = hashed
        emp.must_change_password = True
        db.commit()
        return True


    @staticmethod
    def update_status(db: Session, emp_id: str, status_val: str) -> Optional[EmployeeResponse]:
        emp = EmployeeRepository.get_by_emp_id(db, emp_id)
        if not emp:
            return None
        emp.status = status_val.upper()
        db.commit()
        db.refresh(emp)
        return EmployeeResponse.from_db(emp)

    @staticmethod
    def delete_employee(db: Session, emp_id: str) -> bool:
        emp = EmployeeRepository.get_by_emp_id(db, emp_id)
        if not emp:
            return False
        EmployeeRepository.delete(db, emp)
        return True

