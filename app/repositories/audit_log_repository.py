from sqlalchemy.orm import Session
from typing import List
from app.models.audit_log import AuditLog


class AuditLogRepository:
    @staticmethod
    def get_all(db: Session) -> List[AuditLog]:
        return db.query(AuditLog).order_by(AuditLog.created_at.desc()).all()

    @staticmethod
    def create(
        db: Session,
        employee_id: str,
        employee_name: str,
        action: str,
        entity: str = "",
        entity_id: str = "",
    ) -> AuditLog:
        log_entry = AuditLog(
            employee_id=employee_id,
            employee_name=employee_name,
            action=action,
            entity=entity,
            entity_id=entity_id,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry
