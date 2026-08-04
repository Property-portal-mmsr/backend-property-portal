from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.database import get_db
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeResponse
from app.schemas.auth import PasswordResetRequest, StatusUpdateRequest
from app.services.employee_service import EmployeeService
from app.services.audit_service import AuditService
from app.dependencies import get_current_admin_user
from app.models.employee import Employee

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.get("", response_model=List[EmployeeResponse])
def get_employees(db: Session = Depends(get_db)):
    return EmployeeService.get_all_employees(db)


@router.get("/{emp_id}", response_model=EmployeeResponse)
def get_employee(emp_id: str, db: Session = Depends(get_db)):
    emp = EmployeeService.get_employee_by_emp_id(db, emp_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    emp_data: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_admin_user),
):
    new_emp = EmployeeService.create_employee(db, emp_data)
    AuditService.log_action(
        db, current_user.id, current_user.name or "Admin", "Created Employee", "Employee", new_emp.id
    )
    return new_emp


@router.put("/{emp_id}", response_model=EmployeeResponse)
def update_employee(
    emp_id: str,
    emp_data: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_admin_user),
):
    updated = EmployeeService.update_employee(db, emp_id, emp_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Employee not found")
    AuditService.log_action(
        db, current_user.id, current_user.name or "Admin", "Updated Employee", "Employee", updated.id
    )
    return updated


@router.delete("/{emp_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    emp_id: str,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_admin_user),
):
    success = EmployeeService.delete_employee(db, emp_id)
    if not success:
        raise HTTPException(status_code=404, detail="Employee not found")
    AuditService.log_action(
        db, current_user.id, current_user.name or "Admin", "Deleted Employee", "Employee", emp_id
    )
    return None


@router.patch("/{emp_id}/reset-password", status_code=status.HTTP_200_OK)
def reset_employee_password(
    emp_id: str,
    pwd_req: PasswordResetRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_admin_user),
):
    success = EmployeeService.reset_password(db, emp_id, pwd_req.new_password)
    if not success:
        raise HTTPException(status_code=404, detail="Employee not found")
    AuditService.log_action(
        db, current_user.id, current_user.name or "Admin", "Reset Employee Password", "Employee", emp_id
    )
    return {"message": "Password reset successfully"}


@router.patch("/{emp_id}/status", response_model=EmployeeResponse)
def update_employee_status(
    emp_id: str,
    status_req: StatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_admin_user),
):
    updated = EmployeeService.update_status(db, emp_id, status_req.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Employee not found")
    AuditService.log_action(
        db, current_user.id, current_user.name or "Admin", f"Disabled Employee" if status_req.status.upper() != "ACTIVE" else "Activated Employee", "Employee", updated.id
    )
    return updated

