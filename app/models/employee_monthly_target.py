from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.employee import Employee


class EmployeeMonthlyTarget(Base):
    __tablename__ = "employee_monthly_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    month: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "August", "September"
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    target: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint("employee_id", "month", "year", name="uq_emp_month_year"),
    )

    employee: Mapped["Employee"] = relationship("Employee", back_populates="monthly_targets")
