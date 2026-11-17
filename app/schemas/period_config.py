"""
Pydantic schemas for Period Configuration, Employee Employment History,
Team Assignments, Target Allocations, Incentive Slabs, Team Targets,
and Configuration Audit History.
"""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel


class EmployeeStatusChangeRequest(BaseModel):
    status: str  # "ACTIVE" | "INACTIVE"
    effective_date: date
    employment_end_date: Optional[date] = None
    reason: Optional[str] = None


class EmployeeEmploymentHistoryResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    employment_start_date: Optional[date] = None
    employment_end_date: Optional[date] = None
    employment_status: str
    effective_date: date
    reactivation_history: Optional[str] = None
    reason: Optional[str] = None
    changed_by: Optional[str] = None
    created_at: Optional[datetime] = None


class TeamAssignmentInput(BaseModel):
    employee_id: int
    team_id: int
    team_leader_id: int
    team_name: Optional[str] = None
    effective_start_date: Optional[date] = None
    effective_end_date: Optional[date] = None


class TeamAssignmentResponse(BaseModel):
    id: int
    period_id: int
    employee_id: int
    employee_name: str
    employee_status: str
    team_id: int
    team_name: str
    team_leader_id: int
    team_leader_name: str
    effective_start_date: date
    effective_end_date: date


class TargetAllocationInput(BaseModel):
    employee_id: int
    assigned_target_amount: float
    target_type: str = "INDIVIDUAL_RM"
    approval_status: str = "APPROVED"


class TargetAllocationResponse(BaseModel):
    id: int
    period_id: int
    employee_id: int
    employee_name: str
    employee_status: str
    team_name: Optional[str] = None
    team_leader_name: Optional[str] = None
    assigned_target_amount: float
    target_type: str
    approval_status: str


class IncentiveSlabInput(BaseModel):
    incentive_type: str  # "RM" | "TEAM_LEADER"
    slab_label: Optional[str] = None
    assigned_target_amount: Optional[float] = None
    min_assigned_target: Optional[float] = None
    max_assigned_target: Optional[float] = None
    achievement_threshold: float = 100.0
    incentive_amount: float
    eligibility_conditions: Optional[str] = "EXACT_TARGET_PCT"
    calculation_method: str = "FIXED_SLAB"
    priority: int = 1
    active_status: bool = True


class IncentiveSlabResponse(BaseModel):
    id: int
    period_id: int
    incentive_type: str
    slab_label: Optional[str] = None
    assigned_target_amount: Optional[float] = None
    min_assigned_target: Optional[float] = None
    max_assigned_target: Optional[float] = None
    achievement_threshold: float
    incentive_amount: float
    eligibility_conditions: Optional[str] = None
    calculation_method: str
    priority: int
    active_status: bool


class TeamTargetConfigInput(BaseModel):
    team_id: int
    team_leader_id: int
    team_name: Optional[str] = None
    aggregate_target: Optional[float] = None
    team_leader_incentive: float = 20000.0
    eligibility_percentage: float = 100.0


class TeamTargetConfigResponse(BaseModel):
    id: int
    period_id: int
    team_id: int
    team_name: str
    team_leader_id: int
    team_leader_name: str
    member_count: int = 0
    aggregate_target: float
    computed_member_target_sum: float = 0.0
    team_leader_incentive: float
    eligibility_percentage: float


class PeriodConfigurationCreateRequest(BaseModel):
    period_code: Optional[str] = None
    period_name: str
    start_date: date
    end_date: date
    month: str  # YYYY-MM
    year: int
    period_type: str = "CUSTOM"  # FULL_MONTH | FIRST_HALF | SECOND_HALF | CUSTOM
    clone_from_period_id: Optional[int] = None


class PeriodConfigurationBulkSaveRequest(BaseModel):
    period_name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    team_assignments: Optional[List[TeamAssignmentInput]] = None
    target_allocations: Optional[List[TargetAllocationInput]] = None
    incentive_slabs: Optional[List[IncentiveSlabInput]] = None
    team_target_configs: Optional[List[TeamTargetConfigInput]] = None
    reason: Optional[str] = None


class PeriodActionRequest(BaseModel):
    reason: Optional[str] = None


class PeriodSummaryBrief(BaseModel):
    id: int
    period_code: str
    period_name: str
    start_date: date
    end_date: date
    month: str
    year: int
    period_type: str
    configuration_status: str
    approval_status: str
    version: int
    active_employee_count: int = 0
    total_target: float = 0.0
    team_count: int = 0


class PeriodConfigurationDetailResponse(BaseModel):
    id: int
    period_code: str
    period_name: str
    start_date: date
    end_date: date
    month: str
    year: int
    period_type: str
    configuration_status: str
    approval_status: str
    version: int
    created_by: Optional[str] = None
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    team_assignments: List[TeamAssignmentResponse] = []
    target_allocations: List[TargetAllocationResponse] = []
    incentive_slabs: List[IncentiveSlabResponse] = []
    team_target_configs: List[TeamTargetConfigResponse] = []
    total_individual_target: float = 0.0
    total_team_aggregate_target: float = 0.0
    targets_valid: bool = True
    active_assigned_employees_count: int = 0


class ConfigurationAuditHistoryResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_by: str
    change_timestamp: datetime
    reason: Optional[str] = None

