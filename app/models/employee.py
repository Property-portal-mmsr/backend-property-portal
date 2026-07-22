from sqlalchemy import Column, Integer, String

from app.models.base import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(20))
    password = Column(String(255))
    role = Column(String(20), default="employee")