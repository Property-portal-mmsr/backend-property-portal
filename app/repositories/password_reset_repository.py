from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Optional
from app.models.password_reset_request import PasswordResetRequest


class PasswordResetRepository:
    @staticmethod
    def create_request(
        db: Session, email: str, employee_id: Optional[str] = None
    ) -> PasswordResetRequest:
        req = PasswordResetRequest(
            email=email,
            employee_id=employee_id,
            status="PENDING",
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        return req

    @staticmethod
    def get_all(db: Session) -> List[PasswordResetRequest]:
        return (
            db.query(PasswordResetRequest)
            .order_by(PasswordResetRequest.requested_at.desc())
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, req_id: int) -> Optional[PasswordResetRequest]:
        return (
            db.query(PasswordResetRequest)
            .filter(PasswordResetRequest.id == req_id)
            .first()
        )

    @staticmethod
    def update_status(
        db: Session, req_id: int, status: str, approved_by: Optional[str] = None
    ) -> Optional[PasswordResetRequest]:
        req = PasswordResetRepository.get_by_id(db, req_id)
        if not req:
            return None
        req.status = status
        req.approved_by = approved_by
        req.approved_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(req)
        return req
