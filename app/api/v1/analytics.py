"""
Performance Analytics Dashboard API
GET /api/v1/analytics/dashboard
GET /api/v1/analytics/filters

Requires JWT authentication (Bearer token).
All KPI / chart / table calculations are performed server-side from database configurations.
The frontend only receives the final computed JSON.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies import get_current_user
from app.models.employee import Employee
from app.schemas.analytics import DashboardResponse, DailyRevenueDrilldownResponse
from app.services.analytics_service import build_dashboard, build_daily_revenue_drilldown

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Performance Analytics Dashboard",
    description=(
        "Returns fully-computed dashboard data including KPIs, charts, "
        "leaderboard, performance table, team performance table, and period breakdowns. "
        "All calculations are performed server-side from live Google Sheet data "
        "joined with database PeriodConfiguration and Employee employment history."
    ),
)
def get_dashboard(
    month: Optional[str] = Query(
        None,
        description="Filter by month in YYYY-MM format (e.g. 2026-11).",
        examples=["2026-11"],
        pattern=r"^\d{4}-\d{2}$",
    ),
    period_code: Optional[str] = Query(
        None,
        description="Optional specific period code (e.g. 2026-11-H1 or 2026-11-H2).",
        examples=["2026-11-H2"],
    ),
    period_id: Optional[int] = Query(
        None,
        description="Optional specific period database ID.",
    ),
    employee_id: Optional[int] = Query(
        None,
        description="Filter by Employee database ID.",
        examples=[6],
    ),
    rm_name: Optional[str] = Query(
        None,
        description="Filter by RM name (case-insensitive partial match).",
        examples=["Chethan"],
    ),
    start_date: Optional[date] = Query(
        None,
        description="Filter records on or after this date (YYYY-MM-DD).",
        examples=["2026-11-01"],
    ),
    end_date: Optional[date] = Query(
        None,
        description="Filter records on or before this date (YYYY-MM-DD).",
        examples=["2026-11-15"],
    ),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    MIN_REPORTING_DATE = date(2026, 9, 1)

    if start_date and start_date < MIN_REPORTING_DATE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Start date cannot be earlier than {MIN_REPORTING_DATE.isoformat()}",
        )

    if end_date and end_date < MIN_REPORTING_DATE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"End date cannot be earlier than {MIN_REPORTING_DATE.isoformat()}",
        )

    if start_date and end_date and end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date cannot be earlier than start date",
        )

    if month and month < "2026-09":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reporting month cannot be earlier than September 2026 (2026-09)",
        )

    try:
        return build_dashboard(
            db=db,
            month=month,
            employee_id=employee_id,
            rm_name=rm_name,
            start_date=start_date,
            end_date=end_date,
            period_code=period_code,
            period_id=period_id,
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
    description="Returns available months, periods, and active RM names for populating filter dropdowns.",
)
def get_dashboard_filters(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    try:
        result = build_dashboard(db=db)
        return {
            "available_months": result.available_months,
            "available_rms": result.available_rms,
            "available_employees": result.available_employees,
            "available_periods": result.available_periods,
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


@router.get(
    "/daily-drilldown",
    response_model=DailyRevenueDrilldownResponse,
    summary="Employee-Wise Daily Revenue Drill-Down",
    description=(
        "Returns employee-wise revenue breakdown, team, team leader, and transaction counts "
        "for a specific date, enforcing the active Sales Period View boundaries."
    ),
)
def get_daily_revenue_drilldown(
    target_date: date = Query(
        ...,
        alias="date",
        description="Selected date in YYYY-MM-DD format (e.g. 2026-11-14).",
        examples=["2026-11-14"],
    ),
    month: Optional[str] = Query(
        None,
        description="Active month filter in YYYY-MM format.",
    ),
    period_code: Optional[str] = Query(
        None,
        description="Active period code (e.g. 2026-11-H1 or 2026-11-H2).",
    ),
    period_id: Optional[int] = Query(
        None,
        description="Active period database ID.",
    ),
    employee_id: Optional[int] = Query(
        None,
        description="Optional Employee database ID filter.",
    ),
    rm_name: Optional[str] = Query(
        None,
        description="Optional RM name filter.",
    ),
    start_date: Optional[date] = Query(
        None,
        description="Optional custom start date filter.",
    ),
    end_date: Optional[date] = Query(
        None,
        description="Optional custom end date filter.",
    ),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    MIN_REPORTING_DATE = date(2026, 9, 1)
    if target_date < MIN_REPORTING_DATE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Selected date cannot be earlier than {MIN_REPORTING_DATE.isoformat()}",
        )

    try:
        return build_daily_revenue_drilldown(
            db=db,
            target_date=target_date,
            month=month,
            period_code=period_code,
            period_id=period_id,
            employee_id=employee_id,
            rm_name=rm_name,
            start_date=start_date,
            end_date=end_date,
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except RuntimeError as re_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(re_err),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Daily drill-down computation failed: {str(e)}",
        )

