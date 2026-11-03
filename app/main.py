from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

from app.database.database import Base, engine, SessionLocal, sync_table_schema, get_db
from app.models.employee import Employee
from app.models.employee_monthly_target import EmployeeMonthlyTarget
from app.models.owner import Owner
from app.models.property import Property
from app.models.audit_log import AuditLog
from app.models.password_reset_request import PasswordResetRequest
from app.models.team import Team, TeamMember
from app.repositories.property_repository import PropertyRepository

from app.repositories.employee_repository import EmployeeRepository
from app.api.v1.router import api_router

from app.schemas.auth import TokenResponse
from app.services.auth_service import AuthService

sync_table_schema(engine, Base)
Base.metadata.create_all(bind=engine)

try:
    from sqlalchemy import text as _sql_text
    with engine.begin() as _conn:
        _conn.execute(_sql_text(
            "ALTER TABLE property_images MODIFY image_url VARCHAR(2048) NOT NULL"
        ))
except Exception as _alter_err:
    logger.warning("Could not widen property_images.image_url: %s", _alter_err)


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

# Serve leftover disk uploads (legacy relative URLs). New photos go to CloudFront.
from app.core.config import CLOUDFRONT_DOMAIN, UPLOADS_DIR, UPLOADS_FALLBACK_ORIGIN

os.makedirs(os.path.join(UPLOADS_DIR, "images"), exist_ok=True)
UPLOADS_ROOT = UPLOADS_DIR


def _upload_headers(content_type: str, size: Optional[int] = None) -> dict:
    headers = {"Cache-Control": "public, max-age=86400"}
    if size is not None:
        headers["Content-Length"] = str(size)
    return headers


def _safe_upload_path(file_path: str) -> str:
    local_path = os.path.abspath(os.path.join(UPLOADS_ROOT, file_path))
    if local_path == UPLOADS_ROOT or not local_path.startswith(UPLOADS_ROOT + os.sep):
        raise HTTPException(status_code=404, detail="Not Found")
    return local_path


def _resolve_existing_upload(local_path: str) -> Optional[str]:
    if os.path.isfile(local_path):
        return local_path
    spaced = local_path.replace("_", " ")
    if os.path.isfile(spaced):
        return spaced
    directory, name = os.path.split(local_path)
    if not os.path.isdir(directory):
        return None
    compact = name.lower().replace("_", "").replace(" ", "")
    try:
        for candidate in os.listdir(directory):
            if candidate.lower().replace("_", "").replace(" ", "") == compact:
                path = os.path.join(directory, candidate)
                if os.path.isfile(path):
                    return path
    except OSError:
        return None
    return None


@app.api_route("/uploads/{file_path:path}", methods=["GET", "HEAD"])
async def serve_upload(file_path: str, request: Request):
    requested_path = _safe_upload_path(file_path)
    local_path = _resolve_existing_upload(requested_path)
    if local_path:
        return FileResponse(local_path, headers={"Cache-Control": "public, max-age=86400"})

    remote_candidates = []
    if CLOUDFRONT_DOMAIN:
        domain = CLOUDFRONT_DOMAIN if CLOUDFRONT_DOMAIN.startswith("http") else f"https://{CLOUDFRONT_DOMAIN}"
        domain = domain.rstrip("/")
        remote_candidates.append(f"{domain}/uploads/{file_path}")
        if file_path.startswith("images/"):
            remote_candidates.append(f"{domain}/uploads/{file_path[len('images/'):]}")
    if UPLOADS_FALLBACK_ORIGIN:
        remote_candidates.append(f"{UPLOADS_FALLBACK_ORIGIN.rstrip('/')}/uploads/{file_path}")

    for remote_url in remote_candidates:
        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                upstream = await client.get(remote_url)
            content_type = upstream.headers.get("content-type", "")
            if upstream.status_code == 200 and content_type.startswith("image/"):
                media_type = content_type.split(";")[0]
                try:
                    os.makedirs(os.path.dirname(requested_path), exist_ok=True)
                    with open(requested_path, "wb") as cached:
                        cached.write(upstream.content)
                except OSError:
                    logger.warning("Could not cache fallback upload for %s", file_path)
                if request.method == "HEAD":
                    return Response(
                        status_code=200,
                        media_type=media_type,
                        headers=_upload_headers(media_type, len(upstream.content)),
                    )
                return Response(
                    content=upstream.content,
                    media_type=media_type,
                    headers=_upload_headers(media_type, len(upstream.content)),
                )
        except httpx.HTTPError:
            logger.warning("Upload fallback failed for %s", remote_url)

    raise HTTPException(status_code=404, detail="Not Found")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."},
    )


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
async def root_login(
    request: Request,
    db=Depends(get_db),
):
    from app.api.v1.auth import credentials_from_request
    email, password = await credentials_from_request(request)
    return AuthService.authenticate_employee(db=db, email=email, password=password)
@app.get("/api/v1/debug_employees")
def debug_employees(db=Depends(get_db)):
    emps = db.query(Employee).all()
    return [{"name": e.name, "role": e.role, "designation": e.designation, "is_team_leader": e.is_team_leader, "rm": e.reporting_manager} for e in emps]
