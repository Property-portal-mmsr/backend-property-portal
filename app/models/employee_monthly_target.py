from sqlalchemy import Column, Integer, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import Base

class EmployeeMonthlyTarget(Base):
    __tablename__ = "employee_monthly_targets"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    target = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint('employee_id', 'month', 'year', name='uq_emp_month_year'),
    )

    employee = relationship("Employee", back_populates="monthly_targets")
