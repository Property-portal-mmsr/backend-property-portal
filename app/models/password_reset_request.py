from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database.database import Base


class PasswordResetRequest(Base):
    __tablename__ = "password_reset_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(50), nullable=True)
    email = Column(String(150), nullable=False, index=True)
    status = Column(String(20), default="PENDING")  # PENDING, APPROVED, REJECTED
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_by = Column(String(50), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
