"""
Performance Analytics Dashboard API
GET /api/v1/analytics/dashboard
GET /api/v1/analytics/filters

Requires JWT authentication (Bearer token).
All KPI / chart / table calculations are performed server-side.
The frontend only receives the final computed JSON.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies import get_current_user
from app.models.employee import Employee
from app.schemas.analytics import DashboardResponse
from app.services.analytics_service import build_dashboard

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Performance Analytics Dashboard",
    description=(
        "Returns fully-computed dashboard data including KPIs, charts, "
        "leaderboard, and performance table. All calculations are performed "
        "server-side from live Google Sheet data joined with the Employee table. "
        "Requires JWT authentication."
    ),
)
def get_dashboard(
    month: Optional[str] = Query(
        None,
        description="Filter by month in YYYY-MM format (e.g. 2026-04). "
                    "Also drives the daily-revenue chart and prev/current month comparison.",
        example="2026-04",
        pattern=r"^\d{4}-\d{2}$",
    ),
    rm_name: Optional[str] = Query(
        None,
        description="Filter by RM name (case-insensitive partial match).",
        example="Chethan",
    ),
    start_date: Optional[date] = Query(
        None,
        description="Filter records on or after this date (YYYY-MM-DD).",
        example="2026-04-01",
    ),
    end_date: Optional[date] = Query(
        None,
        description="Filter records on or before this date (YYYY-MM-DD).",
        example="2026-04-30",
    ),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Fetch live Google Sheet data, join with active Employee table,
    apply filters, and return fully computed dashboard JSON.
    """
    try:
        return build_dashboard(
            db=db,
            month=month,
            rm_name=rm_name,
            start_date=start_date,
            end_date=end_date,
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dashboard computation failed: {str(e)}",
        )


@router.get(
    "/filters",
    summary="Available Dashboard Filters",
    description="Returns available months and RM names for populating filter dropdowns. Requires JWT authentication.",
)
def get_dashboard_filters(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Returns the available_months and available_rms for dropdown filters.
    Fetches a full unfiltered dashboard and extracts metadata only.
    """
    try:
        result = build_dashboard(db=db)
        return {
            "available_months": result.available_months,
            "available_rms": result.available_rms,
        }
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch filters: {str(e)}",
        )
