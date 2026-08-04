from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.database.database import get_db
from app.services.audit_service import AuditService, AuditLogResponse
from app.dependencies import get_current_admin_user
from app.models.employee import Employee

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=List[AuditLogResponse])
def get_all_audit_logs(
    db: Session = Depends(get_db),
    current_admin: Employee = Depends(get_current_admin_user),
):
    return AuditService.get_audit_logs(db)
