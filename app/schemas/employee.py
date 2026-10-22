from pydantic import BaseModel
from typing import List, Optional


class EmployeeCreate(BaseModel):
    id: Optional[str] = None
    name: str
    email: Optional[str] = ""
    phone: Optional[str] = ""
    password: Optional[str] = None
    role: Optional[str] = "EMPLOYEE"
    designation: Optional[str] = ""
    department: Optional[str] = ""
    reporting_manager: Optional[str] = ""
    joining_date: Optional[str] = ""
    profile_image: Optional[str] = ""
    status: Optional[str] = "ACTIVE"


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    designation: Optional[str] = None
    department: Optional[str] = None
    reporting_manager: Optional[str] = None
    joining_date: Optional[str] = None
    profile_image: Optional[str] = None
    status: Optional[str] = None


class EmployeeResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    role: str
    status: str
    designation: Optional[str] = ""
    department: Optional[str] = ""
    reporting_manager: Optional[str] = ""
    joining_date: Optional[str] = ""
    profile_image: Optional[str] = ""
    last_login_at: Optional[str] = None

    @classmethod
    def from_db(cls, emp) -> "EmployeeResponse":
        status_val = str(emp.status or "Active")
        if status_val.upper() == "ACTIVE":
            status_val = "Active"
        elif status_val.upper() == "INACTIVE":
            status_val = "Inactive"
        elif status_val.upper() == "ON_LEAVE":
            status_val = "On Leave"
        elif status_val.upper() == "RESIGNED":
            status_val = "Resigned"
        elif status_val.upper() == "TERMINATED":
            status_val = "Terminated"
        elif status_val.upper() == "PROBATION":
            status_val = "Probation"

        role_val = str(emp.role or "EMPLOYEE").upper()

        return cls(
            id=emp.emp_id or f"EMP{str(emp.id).zfill(3)}",
            name=emp.name or "",
            email=emp.email or "",
            phone=emp.phone or "",
            role=role_val,
            status=status_val,
            designation=getattr(emp, "designation", "") or "",
            department=getattr(emp, "department", "") or "",
            reporting_manager=getattr(emp, "reporting_manager", "") or "",
            joining_date=getattr(emp, "joining_date", "") or "",
            profile_image=getattr(emp, "profile_image", "") or "",
            last_login_at=_format_login_at(getattr(emp, "last_login_at", None)),
        )


def _format_login_at(value) -> Optional[str]:
    if not value:
        return None
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


class LoginReportRow(BaseModel):
    id: str
    name: str
    department: str
    last_login_at: Optional[str] = None
    login_count: int
    used: bool
    never_logged_in: bool


class LoginReportResponse(BaseModel):
    month: str
    used: int
    unused: int
    never_logged_in: int
    employees: List[LoginReportRow]



