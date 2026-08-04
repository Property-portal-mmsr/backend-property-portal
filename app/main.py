from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.database.database import Base, engine, SessionLocal, sync_table_schema, get_db
from app.models.employee import Employee
from app.models.owner import Owner
from app.models.property import Property
from app.models.audit_log import AuditLog
from app.models.password_reset_request import PasswordResetRequest
from app.repositories.property_repository import PropertyRepository

from app.repositories.employee_repository import EmployeeRepository
from app.api.v1.router import api_router

from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import AuthService

sync_table_schema(engine, Base)
Base.metadata.create_all(bind=engine)


app = FastAPI(title="Property Portal API", version="1.0.0")

# Configure CORS for Next.js frontend and production domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://employee.makemystay.ai",
        "https://www.employee.makemystay.ai",
        "http://employee.makemystay.ai",
        "https://makemystay.ai",
        "https://www.makemystay.ai",
        "https://admin.makemystay.ai",
        "http://localhost:3000",
        "http://localhost:3005",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3005",
    ],
    allow_origin_regex=r"https://.*\.makemystay\.ai|http://localhost:.*|http://127\.0\.0\.1:.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 API router
app.include_router(api_router)


@app.on_event("startup")
def startup_seed_db():
    db = SessionLocal()
    try:
        PropertyRepository.seed_default_properties(db)
        EmployeeRepository.seed_default_employees(db)
    finally:
        db.close()


@app.get("/")
def root():
    return {
        "message": "Property Portal API Running 🚀",
        "docs_url": "/docs",
    }


@app.get("/health")
def health_check():
    """AWS ALB health check endpoint."""
    return {"status": "healthy"}


@app.post("/login", response_model=TokenResponse, tags=["Authentication"])
def root_login(
    credentials: LoginRequest,
    db=Depends(get_db),
):
    return AuthService.authenticate_employee(
        db=db, email=credentials.email, password=credentials.password
    )