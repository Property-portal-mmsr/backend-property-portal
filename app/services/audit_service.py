from sqlalchemy.orm import Session
from typing import List
from app.repositories.audit_log_repository import AuditLogRepository
from app.models.audit_log import AuditLog
from pydantic import BaseModel
from datetime import datetime


class AuditLogResponse(BaseModel):
    id: int
    employee_id: str
    employee_name: str
    action: str
    entity: str
    entity_id: str
    created_at: str

    @classmethod
    def from_db(cls, log: AuditLog) -> "AuditLogResponse":
        return cls(
            id=log.id,
            employee_id=log.employee_id or "",
            employee_name=log.employee_name or "System",
            action=log.action or "",
            entity=log.entity or "",
            entity_id=str(log.entity_id or ""),
            created_at=log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "",
        )


class AuditService:
    @staticmethod
    def log_action(
        db: Session,
        employee_id: str,
        employee_name: str,
        action: str,
        entity: str = "",
        entity_id: str = "",
    ):
        try:
            AuditLogRepository.create(
                db=db,
                employee_id=str(employee_id),
                employee_name=employee_name,
                action=action,
                entity=entity,
                entity_id=str(entity_id),
            )
        except Exception as e:
            print(f"[AUDIT LOG ERROR]: {e}")

    @staticmethod
    def get_audit_logs(db: Session) -> List[AuditLogResponse]:
        logs = AuditLogRepository.get_all(db)
        return [AuditLogResponse.from_db(log) for log in logs]
