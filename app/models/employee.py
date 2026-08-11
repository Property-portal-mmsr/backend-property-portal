from sqlalchemy import Column, Integer, String, Boolean, Float
from app.models.base import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    emp_id = Column(String(50), unique=True, index=True, nullable=True)
    name = Column(String(100), nullable=True)
    email = Column(String(100), nullable=True, unique=True, index=True)
    phone = Column(String(20), nullable=True)
    password = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=True)
    role = Column(String(50), default="EMPLOYEE")
    designation = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    reporting_manager = Column(String(100), nullable=True)
    joining_date = Column(String(20), nullable=True)
    profile_image = Column(String(255), nullable=True)
    status = Column(String(20), default="ACTIVE")
    must_change_password = Column(Boolean, default=False, nullable=True)
    monthly_target = Column(Float, default=100000.0, nullable=True)