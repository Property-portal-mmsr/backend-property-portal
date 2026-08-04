from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.properties import router as properties_router
from app.api.v1.employees import router as employees_router
from app.api.v1.audit_logs import router as audit_logs_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(properties_router)
api_router.include_router(employees_router)
api_router.include_router(audit_logs_router)


