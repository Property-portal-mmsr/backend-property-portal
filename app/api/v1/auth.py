from typing import List
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    PasswordResetRequestResponse,
    PasswordResetApprovalResponse,
)
from app.services.auth_service import AuthService
from app.dependencies import get_current_admin_user
from app.models.employee import Employee

router = APIRouter(prefix="/auth", tags=["Authentication"])



@router.post("/login", response_model=TokenResponse)

def login_json(
    credentials: LoginRequest,
    db: Session = Depends(get_db),
):
    return AuthService.authenticate_employee(
        db=db, email=credentials.email, password=credentials.password
    )



@router.post("/token", response_model=TokenResponse, include_in_schema=False)
def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    return AuthService.authenticate_employee(
        db=db, email=form_data.username, password=form_data.password
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token_endpoint(
    req: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    return AuthService.refresh_access_token(db=db, refresh_token=req.refresh_token)


@router.post("/change-password")
def change_password_endpoint(
    req: ChangePasswordRequest,
    db: Session = Depends(get_db),
):
    emp_id = req.employee_id or ""
    return AuthService.change_first_password(
        db=db,
        employee_id=emp_id,
        old_password=req.old_password,
        new_password=req.new_password,
    )


@router.post("/forgot-password")
def forgot_password_endpoint(
    req: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    return AuthService.submit_forgot_password(db=db, email=req.email)


@router.get(
    "/password-reset-requests", response_model=List[PasswordResetRequestResponse]
)
def get_password_reset_requests_endpoint(
    db: Session = Depends(get_db),
    admin: Employee = Depends(get_current_admin_user),
):
    return AuthService.get_password_reset_requests(db=db)


@router.patch(
    "/password-reset-requests/{req_id}/approve",
    response_model=PasswordResetApprovalResponse,
)
def approve_password_reset_endpoint(
    req_id: int,
    db: Session = Depends(get_db),
    admin: Employee = Depends(get_current_admin_user),
):
    return AuthService.approve_password_reset(
        db=db,
        request_id=req_id,
        admin_id=str(admin.id),
        admin_name=admin.name or "Admin",
    )


@router.patch("/password-reset-requests/{req_id}/reject")
def reject_password_reset_endpoint(
    req_id: int,
    db: Session = Depends(get_db),
    admin: Employee = Depends(get_current_admin_user),
):
    return AuthService.reject_password_reset(
        db=db,
        request_id=req_id,
        admin_id=str(admin.id),
        admin_name=admin.name or "Admin",
    )

