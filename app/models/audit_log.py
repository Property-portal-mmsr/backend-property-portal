from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(50), nullable=True)
    employee_name = Column(String(100), nullable=True)
    action = Column(String(255), nullable=False)
    entity = Column(String(100), nullable=True)
    entity_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
