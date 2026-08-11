"""
Pydantic schemas for Performance Analytics Dashboard responses.
All business calculations are performed in the backend.
The frontend receives only final computed JSON.
"""

from pydantic import BaseModel
from typing import List, Optional


class KPIResponse(BaseModel):
    total_revenue: float
    beds_sold: float
    overall_target: float
    achievement_pct: float
    active_rms: int


class MonthlyRevenueItem(BaseModel):
    month: str          # e.g. "2026-04"
    revenue: float


class DailyRevenueItem(BaseModel):
    date: str           # e.g. "2026-04-15"
    revenue: float


class MonthComparisonItem(BaseModel):
    month: str          # e.g. "2026-04"
    revenue: float
    beds_sold: float
    achievement_pct: float
    incentive: float


class PrevCurrentMonthResponse(BaseModel):
    previous: Optional[MonthComparisonItem] = None
    current: Optional[MonthComparisonItem] = None


class LeaderboardItem(BaseModel):
    rm_name: str
    revenue: float
    beds_sold: float
    target: float
    achievement_pct: float
    remaining_target: float
    incentive: float


class PerformanceTableItem(BaseModel):
    rm_name: str
    beds_sold: float
    revenue: float
    monthly_target: float
    achievement_pct: float
    remaining_target: float
    incentive: float
    status: str         # "Target Achieved" | "In Progress" | "Needs Improvement"


class DashboardResponse(BaseModel):
    kpis: KPIResponse
    monthly_revenue: List[MonthlyRevenueItem]
    daily_revenue: List[DailyRevenueItem]
    prev_current_month: PrevCurrentMonthResponse
    leaderboard: List[LeaderboardItem]
    performance_table: List[PerformanceTableItem]
    # Metadata for filter dropdowns
    available_months: List[str]
    available_rms: List[str]
