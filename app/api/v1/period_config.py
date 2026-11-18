"""
Period Configuration, Team Assignment, Target Allocation, Incentive Slab,
Employee Effective Status, and Configuration Audit Administration API.
"""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies import get_current_admin_user, get_current_user
from app.models.employee import Employee
from app.schemas.employee import EmployeeResponse
from app.schemas.period_config import (
    PeriodSummaryBrief,
    PeriodConfigurationDetailResponse,
    PeriodConfigurationCreateRequest,
    PeriodConfigurationBulkSaveRequest,
    PeriodActionRequest,
    EmployeeStatusChangeRequest,
    EmployeeEmploymentHistoryResponse,
    ConfigurationAuditHistoryResponse,
)
from app.services.period_config_service import PeriodConfigService
from app.services.eligibility_service import EligibilityService

router = APIRouter(prefix="/period-config", tags=["Period & Target Configuration"])


@router.get("/periods", response_model=List[PeriodSummaryBrief])
def list_periods(
    month: Optional[str] = Query(None, description="Filter by month YYYY-MM"),
    year: Optional[int] = Query(None, description="Filter by year"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    return PeriodConfigService.list_periods(db=db, month=month, year=year)


@router.get("/periods/{period_id}", response_model=PeriodConfigurationDetailResponse)
def get_period_detail(
    period_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    return PeriodConfigService.get_period_detail(db=db, period_id=period_id)


@router.post(
    "/periods",
    response_model=PeriodConfigurationDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_period(
    req: PeriodConfigurationCreateRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_admin_user),
):
    return PeriodConfigService.create_period(
        db=db,
        req=req,
        changed_by=current_user.name or "Admin",
    )


@router.put("/periods/{period_id}", response_model=PeriodConfigurationDetailResponse)
def save_period_configuration(
    period_id: int,
    req: PeriodConfigurationBulkSaveRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_admin_user),
):
    return PeriodConfigService.save_period_configuration(
        db=db,
        period_id=period_id,
        req=req,
        changed_by=current_user.name or "Admin",
    )


@router.post("/periods/{period_id}/approve", response_model=PeriodConfigurationDetailResponse)
def approve_period(
    period_id: int,
    req: Optional[PeriodActionRequest] = None,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_admin_user),
):
    return PeriodConfigService.approve_and_publish_period(
        db=db,
        period_id=period_id,
        reason=req.reason if req else None,
        changed_by=current_user.name or "Admin",
    )


@router.post("/periods/{period_id}/reopen", response_model=PeriodConfigurationDetailResponse)
def reopen_period(
    period_id: int,
    req: Optional[PeriodActionRequest] = None,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_admin_user),
):
    return PeriodConfigService.reopen_period(
        db=db,
        period_id=period_id,
        reason=req.reason if req else None,
        changed_by=current_user.name or "Admin",
    )


@router.get("/employees-status")
def get_employees_for_period_admin(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    return PeriodConfigService.get_employees_for_period_admin(
        db=db,
        start_date=start_date,
        end_date=end_date,
    )


@router.post("/employees/{emp_identifier}/status", response_model=EmployeeResponse)
def change_employee_status_effective(
    emp_identifier: str,
    req: EmployeeStatusChangeRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_admin_user),
):
    emp = None
    if emp_identifier.isdigit():
        emp = db.query(Employee).filter(Employee.id == int(emp_identifier)).first()
    if not emp:
        emp = db.query(Employee).filter(Employee.emp_id == emp_identifier).first()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    updated = EligibilityService.change_employee_employment_status(
        db=db,
        emp=emp,
        new_status=req.status,
        effective_date=req.effective_date,
        employment_end_date=req.employment_end_date,
        reason=req.reason,
        changed_by=current_user.name or "Admin",
    )
    return EmployeeResponse.from_db(updated)


@router.get("/employment-history", response_model=List[EmployeeEmploymentHistoryResponse])
def list_employment_history(
    employee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    return PeriodConfigService.list_employment_history(db=db, employee_id=employee_id)


@router.get("/audit-history", response_model=List[ConfigurationAuditHistoryResponse])
def list_configuration_audit_history(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    return PeriodConfigService.list_audit_history(db=db, limit=limit)

