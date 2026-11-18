"""
Pydantic schemas for Performance Analytics Dashboard responses.
All business calculations are performed in the backend from database configurations.
The frontend receives only final computed JSON.
"""

from pydantic import BaseModel
from typing import List, Optional, Union


class IncentiveSlab(BaseModel):
    target: float
    incentive: float
    achieved: bool
    label: Optional[str] = None


class TeamMemberMini(BaseModel):
    name: str
    beds: float
    revenue: float
    target: float
    pending_revenue: float = 0.0
    achievement_pct: float = 0.0
    incentive_slab: Optional[str] = None
    incentive: float = 0.0
    status: str


class TeamLeaderIncentiveTrackerItem(BaseModel):
    team_id: int
    team_name: str
    team_leader_name: str
    team_size: int
    team_beds: float
    team_revenue: float
    team_target: float
    pending_revenue: float = 0.0
    achievement_pct: float
    eligibility_status: str = "Not Eligible"
    slabs: List[IncentiveSlab]
    current_slab: Optional[float]
    next_slab_target: Optional[float]
    revenue_remaining: Optional[float]
    potential_incentive: Optional[float]
    incentive: Optional[float]
    team_members: List[TeamMemberMini] = []
    beds_sold: float
    progress_percentage: float
    team_leader_revenue: float = 0.0
    team_member_revenue: float = 0.0
    team_leader_beds: float = 0.0
    team_member_beds: float = 0.0
    leader_in_members: bool = False
    overall_team_revenue: float = 0.0


class TeamPerformanceChartItem(BaseModel):
    team_name: str
    revenue: float
    beds: float = 0.0
    team_leader_revenue: float = 0.0
    team_member_revenue: float = 0.0
    overall_team_revenue: float = 0.0


class KPIResponse(BaseModel):
    total_revenue: float
    beds_sold: float
    overall_target: float
    achievement_pct: float
    active_rms: int
    total_rm_incentives: float = 0.0
    total_tl_incentives: float = 0.0
    total_incentives: float = 0.0


class MonthlyRevenueItem(BaseModel):
    month: str          # e.g. "2026-04"
    revenue: float


class DailyRevenueItem(BaseModel):
    date: str           # e.g. "2026-04-15"
    revenue: float


class DailyRevenueEmployeeItem(BaseModel):
    employee_id: Optional[int] = None
    employee_name: str
    team_name: str
    team_leader_name: str
    transaction_count: int
    beds_sold: float = 0.0
    revenue: float


class DailyRevenueDrilldownResponse(BaseModel):
    selected_date: str
    period_code: Optional[str] = None
    period_name: Optional[str] = None
    total_revenue: float
    employee_count: int
    total_transactions: int
    employees: List[DailyRevenueEmployeeItem] = []


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
    incentive_slab: Optional[str] = None
    status: str         # "Target Achieved" | "In Progress" | "Needs Improvement"
    is_team_leader: bool = False
    next_slab: Optional[float] = None
    team_name: Optional[str] = None   # e.g. "Team Arun", "Team Goutham"
    team_leader_name: Optional[str] = None
    is_top_rm: bool = False
    top_rm_status: Optional[str] = None


class EmployeeFilterOption(BaseModel):
    id: int
    name: str


class PeriodOptionItem(BaseModel):
    id: int
    period_code: str
    period_name: str
    start_date: str
    end_date: str
    month: str
    period_type: str
    approval_status: str = "APPROVED"


class PeriodBreakdownItem(BaseModel):
    period_id: int
    period_code: str
    period_name: str
    start_date: str
    end_date: str
    kpis: KPIResponse
    performance_table: List[PerformanceTableItem] = []
    team_leader_tracker: List[TeamLeaderIncentiveTrackerItem] = []


class DashboardResponse(BaseModel):
    kpis: KPIResponse
    monthly_revenue: List[MonthlyRevenueItem]
    daily_revenue: List[DailyRevenueItem]
    prev_daily_revenue: List[DailyRevenueItem]
    prev_current_month: PrevCurrentMonthResponse
    leaderboard: List[LeaderboardItem]
    performance_table: List[PerformanceTableItem]
    team_leader_tracker: List[TeamLeaderIncentiveTrackerItem]
    team_performance: List[TeamPerformanceChartItem]
    # Metadata for filter dropdowns & period breakdowns
    available_months: List[str]
    available_rms: List[Union[EmployeeFilterOption, str]]
    available_employees: List[EmployeeFilterOption] = []
    available_periods: List[PeriodOptionItem] = []
    selected_period_code: Optional[str] = None
    period_breakdowns: List[PeriodBreakdownItem] = []
