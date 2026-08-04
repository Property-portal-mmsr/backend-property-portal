from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
import random
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.password_reset_repository import PasswordResetRepository
from app.utils.password import verify_password, hash_password
from app.utils.jwt import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.schemas.auth import TokenResponse
from app.services.audit_service import AuditService
from app.models.employee import Employee



class AuthService:
    @staticmethod
    def authenticate_employee(
        db: Session, email: str, password: str
    ) -> TokenResponse:


        employee = EmployeeRepository.get_by_email(db, email)
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        stored_hash = employee.password_hash or employee.password
        if not stored_hash or not verify_password(password, stored_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if (employee.status or "").upper() != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled. Contact administrator.",
            )

        role_str = (employee.role or "EMPLOYEE").upper()
        emp_id_str = str(employee.id)
        emp_name_str = employee.name or "Employee"
        must_change = bool(getattr(employee, "must_change_password", False))

        payload = {
            "employee_id": emp_id_str,
            "email": employee.email or "",
            "role": role_str,
        }
        access_token = create_access_token(data=payload)
        refresh_token = create_refresh_token(data=payload)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            role=role_str,
            employee_name=emp_name_str,
            employee_id=emp_id_str,
            must_change_password=must_change,
        )

    @staticmethod
    def refresh_access_token(db: Session, refresh_token: str) -> TokenResponse:
        payload = decode_refresh_token(refresh_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        email = payload.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        employee = EmployeeRepository.get_by_email(db, email)
        if not employee or (employee.status or "").upper() != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled or not found",
            )

        role_str = (employee.role or "EMPLOYEE").upper()
        emp_id_str = str(employee.id)
        emp_name_str = employee.name or "Employee"
        must_change = bool(getattr(employee, "must_change_password", False))

        new_payload = {
            "employee_id": emp_id_str,
            "email": employee.email or "",
            "role": role_str,
        }
        new_access = create_access_token(data=new_payload)
        new_refresh = create_refresh_token(data=new_payload)

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            token_type="bearer",
            role=role_str,
            employee_name=emp_name_str,
            employee_id=emp_id_str,
            must_change_password=must_change,
        )

    @staticmethod
    def change_first_password(
        db: Session,
        employee_id: str,
        old_password: str,
        new_password: str,
    ) -> Dict[str, str]:
        employee = None
        if employee_id.isdigit():
            employee = EmployeeRepository.get_by_id(db, int(employee_id))
        if not employee:
            employee = EmployeeRepository.get_by_emp_id(db, employee_id)
        if not employee and "@" in employee_id:
            employee = EmployeeRepository.get_by_email(db, employee_id)

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found"
            )

        stored_hash = employee.password_hash or employee.password
        if not stored_hash or not verify_password(old_password, stored_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        if len(new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 6 characters long",
            )

        hashed = hash_password(new_password)
        employee.password_hash = hashed
        employee.password = hashed
        if hasattr(employee, "must_change_password"):
            employee.must_change_password = False

        db.commit()

        try:
            AuditService.log_action(
                db=db,
                employee_id=str(employee.id),
                employee_name=employee.name or "Employee",
                action="Changed Password",
                entity="Employee",
                entity_id=str(employee.id),
            )
        except Exception:
            pass

        return {"message": "Password updated successfully"}

    @staticmethod
    def submit_forgot_password(db: Session, email: str) -> Dict[str, str]:
        employee = EmployeeRepository.get_by_email(db, email)
        if employee:
            PasswordResetRepository.create_request(
                db=db,
                email=email,
                employee_id=str(employee.id),
            )
            try:
                AuditService.log_action(
                    db=db,
                    employee_id=str(employee.id),
                    employee_name=employee.name or "Employee",
                    action="Password Reset Request Submitted",
                    entity="Employee",
                    entity_id=str(employee.id),
                )
            except Exception:
                pass
        return {"message": "If the account exists, your request has been received."}

    @staticmethod
    def get_password_reset_requests(db: Session) -> List[Any]:
        return PasswordResetRepository.get_all(db)

    @staticmethod
    def approve_password_reset(
        db: Session, request_id: int, admin_id: str = "ADMIN", admin_name: str = "Admin"
    ) -> Dict[str, Any]:
        req = PasswordResetRepository.get_by_id(db, request_id)
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Password reset request not found",
            )
        if req.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request has already been processed",
            )

        employee = EmployeeRepository.get_by_email(db, req.email)
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee associated with this email no longer exists",
            )

        temp_pwd = f"Welcome@{random.randint(1000, 9999)}"
        hashed = hash_password(temp_pwd)
        if hasattr(employee, "password_hash"):
            employee.password_hash = hashed
        employee.password = hashed
        if hasattr(employee, "must_change_password"):
            employee.must_change_password = True

        PasswordResetRepository.update_status(
            db=db, req_id=request_id, status="APPROVED", approved_by=admin_id
        )

        try:
            AuditService.log_action(
                db=db,
                employee_id=admin_id,
                employee_name=admin_name,
                action=f"Approved Password Reset for {req.email}",
                entity="Employee",
                entity_id=str(employee.id),
            )
        except Exception:
            pass

        return {
            "message": "Password reset request approved.",
            "temporary_password": temp_pwd,
        }

    @staticmethod
    def reject_password_reset(
        db: Session, request_id: int, admin_id: str = "ADMIN", admin_name: str = "Admin"
    ) -> Dict[str, str]:
        req = PasswordResetRepository.get_by_id(db, request_id)
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Password reset request not found",
            )
        if req.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request has already been processed",
            )

        PasswordResetRepository.update_status(
            db=db, req_id=request_id, status="REJECTED", approved_by=admin_id
        )

        try:
            AuditService.log_action(
                db=db,
                employee_id=admin_id,
                employee_name=admin_name,
                action=f"Rejected Password Reset for {req.email}",
                entity="PasswordResetRequest",
                entity_id=str(request_id),
            )
        except Exception:
            pass

        return {"message": "Password reset request rejected."}

