from pydantic import BaseModel
from typing import Optional, Any


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):


    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    employee_name: str
    employee_id: str
    must_change_password: bool = False


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    employee_id: Optional[str] = None
    old_password: str
    new_password: str


class PasswordResetRequest(BaseModel):
    new_password: str


class StatusUpdateRequest(BaseModel):
    status: str


class ForgotPasswordRequest(BaseModel):
    email: str


class PasswordResetRequestResponse(BaseModel):
    id: int
    employee_id: Optional[str] = None
    email: str
    status: str
    requested_at: Optional[Any] = None
    approved_by: Optional[str] = None
    approved_at: Optional[Any] = None

    class Config:
        from_attributes = True



class PasswordResetApprovalResponse(BaseModel):
    message: str
    temporary_password: Optional[str] = None

