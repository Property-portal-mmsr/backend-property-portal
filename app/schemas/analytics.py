"""
Pydantic schemas for Performance Analytics Dashboard responses.
All business calculations are performed in the backend.
The frontend receives only final computed JSON.
"""

from pydantic import BaseModel
from typing import List, Optional


class IncentiveSlab(BaseModel):
    target: float
    incentive: float
    achieved: bool


class TeamMemberMini(BaseModel):
    name: str
    beds: float
    revenue: float
    target: float
    status: str


class TeamLeaderIncentiveTrackerItem(BaseModel):
    team_leader_name: str
    team_size: int
    team_beds: float
    team_revenue: float
    team_target: float
    achievement_pct: float
    slabs: List[IncentiveSlab]
    current_slab: Optional[float]
    next_slab_target: Optional[float]
    revenue_remaining: Optional[float]
    potential_incentive: Optional[float]
    incentive: Optional[float]
    team_members: List[TeamMemberMini] = []
    beds_sold: float
    progress_percentage: float


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
    is_team_leader: bool = False


class PerformanceTableItem(BaseModel):
    rm_name: str
    beds_sold: float
    revenue: float
    monthly_target: float
    achievement_pct: float
    remaining_target: float
    incentive: float
    status: str         # "Target Achieved" | "In Progress" | "Needs Improvement"
    is_team_leader: bool = False
    next_slab: Optional[float] = None


class DashboardResponse(BaseModel):
    kpis: KPIResponse
    monthly_revenue: List[MonthlyRevenueItem]
    daily_revenue: List[DailyRevenueItem]
    prev_daily_revenue: List[DailyRevenueItem]
    prev_current_month: PrevCurrentMonthResponse
    leaderboard: List[LeaderboardItem]
    performance_table: List[PerformanceTableItem]
    team_leader_tracker: List[TeamLeaderIncentiveTrackerItem]
    # Metadata for filter dropdowns
    available_months: List[str]
    available_rms: List[str]
