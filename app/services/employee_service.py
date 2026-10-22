from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from fastapi import HTTPException, status
from app.models.employee import Employee
from app.models.audit_log import AuditLog
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
    LoginReportResponse,
    LoginReportRow,
)
from app.repositories.employee_repository import EmployeeRepository
from app.utils.password import hash_password

IST = ZoneInfo("Asia/Kolkata")


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
    def get_login_report(db: Session, month: Optional[str] = None) -> LoginReportResponse:
        month_key = month or datetime.now(IST).strftime("%Y-%m")
        if not re.fullmatch(r"\d{4}-\d{2}", month_key):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="month must be YYYY-MM",
            )
        year, mon = int(month_key[:4]), int(month_key[5:7])
        if mon < 1 or mon > 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="month must be YYYY-MM",
            )

        start_local = datetime(year, mon, 1, tzinfo=IST)
        if mon == 12:
            end_local = datetime(year + 1, 1, 1, tzinfo=IST)
        else:
            end_local = datetime(year, mon + 1, 1, tzinfo=IST)
        start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
        end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)

        counts = {
            str(employee_id): int(total)
            for employee_id, total in (
                db.query(AuditLog.employee_id, func.count(AuditLog.id))
                .filter(
                    AuditLog.action == "Logged In",
                    AuditLog.created_at >= start_utc,
                    AuditLog.created_at < end_utc,
                )
                .group_by(AuditLog.employee_id)
                .all()
            )
        }

        rows: List[LoginReportRow] = []
        for emp in EmployeeRepository.get_all(db):
            if (emp.status or "").upper() != "ACTIVE":
                continue
            last_login = getattr(emp, "last_login_at", None)
            login_count = counts.get(str(emp.id), 0)
            logged_in_this_month = bool(
                last_login and start_utc <= last_login < end_utc
            )
            if logged_in_this_month and login_count == 0:
                login_count = 1
            response = EmployeeResponse.from_db(emp)
            rows.append(
                LoginReportRow(
                    id=response.id,
                    name=response.name,
                    department=response.department or "",
                    last_login_at=response.last_login_at,
                    login_count=login_count,
                    used=login_count > 0,
                    never_logged_in=last_login is None,
                )
            )

        rows.sort(key=lambda row: (row.used, (row.name or "").lower()))
        used = sum(1 for row in rows if row.used)
        never = sum(1 for row in rows if row.never_logged_in)
        return LoginReportResponse(
            month=month_key,
            used=used,
            unused=len(rows) - used,
            never_logged_in=never,
            employees=rows,
        )

    @staticmethod
    def delete_employee(db: Session, emp_id: str) -> bool:
        emp = EmployeeRepository.get_by_emp_id(db, emp_id)
        if not emp:
            return False
        EmployeeRepository.delete(db, emp)
        return True

