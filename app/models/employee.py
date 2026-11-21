from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, Boolean, Float, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.employee_monthly_target import EmployeeMonthlyTarget


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    emp_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True, index=True, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String(50), default="EMPLOYEE")
    designation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reporting_manager: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    joining_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    employment_end_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    deactivation_effective_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    profile_image: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(20), default="ACTIVE")
    must_change_password: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    monthly_target: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.0)
    is_team_leader: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True)

    monthly_targets: Mapped[List["EmployeeMonthlyTarget"]] = relationship(
        "EmployeeMonthlyTarget",
        back_populates="employee",
        cascade="all, delete-orphan",
    )
