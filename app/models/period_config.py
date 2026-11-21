"""
Database-driven Period, Employment History, Team Assignment, Target,
Incentive, Performance Calculation, and Configuration Audit models.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.team import Team


class PeriodConfiguration(Base):
    """
    A. Period Configuration
    Stores full-month or sub-month (First Half / Second Half / Custom) periods.
    """
    __tablename__ = "period_configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    period_code: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    period_name: Mapped[str] = mapped_column(String(150), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    month: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # YYYY-MM, e.g. "2026-11"
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    period_type: Mapped[str] = mapped_column(String(30), nullable=False, default="FULL_MONTH")  # FULL_MONTH | FIRST_HALF | SECOND_HALF | CUSTOM
    configuration_status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")  # DRAFT | ACTIVE | ARCHIVED
    approval_status: Mapped[str] = mapped_column(String(30), nullable=False, default="APPROVED")  # DRAFT | APPROVED | REOPENED
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    modified_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    team_assignments: Mapped[List["PeriodTeamAssignment"]] = relationship(
        "PeriodTeamAssignment",
        back_populates="period",
        cascade="all, delete-orphan",
    )
    target_configurations: Mapped[List["PeriodTargetConfiguration"]] = relationship(
        "PeriodTargetConfiguration",
        back_populates="period",
        cascade="all, delete-orphan",
    )
    incentive_configurations: Mapped[List["PeriodIncentiveConfiguration"]] = relationship(
        "PeriodIncentiveConfiguration",
        back_populates="period",
        cascade="all, delete-orphan",
    )
    team_target_configurations: Mapped[List["PeriodTeamTargetConfiguration"]] = relationship(
        "PeriodTeamTargetConfiguration",
        back_populates="period",
        cascade="all, delete-orphan",
    )


class EmployeeEmploymentHistory(Base):
    """
    B. Employee Employment History
    Tracks effective-dated employment start, end, deactivation, and reactivation.
    Never deletes employee records or historical performance.
    """
    __tablename__ = "employee_employment_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False, index=True)
    employment_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    employment_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    employment_status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")  # ACTIVE | INACTIVE
    effective_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    reactivation_history: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    changed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    employee: Mapped["Employee"] = relationship("Employee")

    __table_args__ = (
        Index("ix_emp_history_emp_eff", "employee_id", "effective_date", "employment_status"),
    )


class PeriodTeamAssignment(Base):
    """
    C. Team Assignments
    Maps employees to teams and team leaders for a specific performance period and effective date range.
    """
    __tablename__ = "period_team_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False, index=True)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False, index=True)
    team_leader_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False, index=True)
    team_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    period_id: Mapped[int] = mapped_column(Integer, ForeignKey("period_configurations.id", ondelete="CASCADE"), nullable=False, index=True)
    effective_start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    effective_end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    period: Mapped["PeriodConfiguration"] = relationship("PeriodConfiguration", back_populates="team_assignments")
    employee: Mapped["Employee"] = relationship("Employee", foreign_keys=[employee_id])
    team: Mapped["Team"] = relationship("Team", foreign_keys=[team_id])
    team_leader: Mapped["Employee"] = relationship("Employee", foreign_keys=[team_leader_id])

    __table_args__ = (
        UniqueConstraint("period_id", "employee_id", name="uq_period_team_assignment_emp"),
    )


class PeriodTargetConfiguration(Base):
    """
    D. Target Configuration
    Stores individual employee target allocations for a specific period.
    """
    __tablename__ = "period_target_configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False, index=True)
    period_id: Mapped[int] = mapped_column(Integer, ForeignKey("period_configurations.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_target_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False, default="INDIVIDUAL_RM")  # INDIVIDUAL_RM | TEAM_LEADER
    approval_status: Mapped[str] = mapped_column(String(30), nullable=False, default="APPROVED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    modified_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    period: Mapped["PeriodConfiguration"] = relationship("PeriodConfiguration", back_populates="target_configurations")
    employee: Mapped["Employee"] = relationship("Employee")

    __table_args__ = (
        UniqueConstraint("period_id", "employee_id", "target_type", name="uq_period_emp_target_type"),
    )


class PeriodIncentiveConfiguration(Base):
    """
    E. Incentive Configuration
    Stores database-driven RM and Team Leader incentive slabs for a specific period.
    """
    __tablename__ = "period_incentive_configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    period_id: Mapped[int] = mapped_column(Integer, ForeignKey("period_configurations.id", ondelete="CASCADE"), nullable=False, index=True)
    incentive_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)  # RM | TEAM_LEADER
    slab_label: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    assigned_target_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Exact assigned target required for this slab (e.g. 35000, 55000, 90000)
    min_assigned_target: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Optional min target range (e.g. 120000, 55000 for Oct)
    max_assigned_target: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    achievement_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)  # Percentage (e.g. 100.0) or absolute revenue
    incentive_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    eligibility_conditions: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # EXACT_TARGET_PCT | MIN_TARGET_PCT | TEAM_TARGET_PCT | ABSOLUTE_REVENUE
    calculation_method: Mapped[str] = mapped_column(String(50), nullable=False, default="FIXED_SLAB")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    active_status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    period: Mapped["PeriodConfiguration"] = relationship("PeriodConfiguration", back_populates="incentive_configurations")


class PeriodTeamTargetConfiguration(Base):
    """
    F. Team Target Configuration
    Stores aggregate team target, Team Leader incentive amount, and eligibility percentage per period.
    """
    __tablename__ = "period_team_target_configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False, index=True)
    team_leader_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False, index=True)
    team_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    period_id: Mapped[int] = mapped_column(Integer, ForeignKey("period_configurations.id", ondelete="CASCADE"), nullable=False, index=True)
    aggregate_target: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    team_leader_incentive: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    eligibility_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    period: Mapped["PeriodConfiguration"] = relationship("PeriodConfiguration", back_populates="team_target_configurations")
    team: Mapped["Team"] = relationship("Team", foreign_keys=[team_id])
    team_leader: Mapped["Employee"] = relationship("Employee", foreign_keys=[team_leader_id])

    __table_args__ = (
        UniqueConstraint("period_id", "team_id", name="uq_period_team_target_cfg"),
    )


class PerformanceCalculationRecord(Base):
    """
    G. Performance Calculation Records
    Stores auditable calculation snapshots per employee and period.
    """
    __tablename__ = "performance_calculation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False, index=True)
    period_id: Mapped[int] = mapped_column(Integer, ForeignKey("period_configurations.id", ondelete="CASCADE"), nullable=False, index=True)
    role_type: Mapped[str] = mapped_column(String(30), nullable=False, default="RM")  # RM | TEAM_LEADER
    eligible_revenue: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    assigned_target: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    achievement_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    applicable_incentive_slab: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    calculated_incentive: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    calculation_timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    configuration_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (
        UniqueConstraint("period_id", "employee_id", "role_type", name="uq_calc_record_period_emp_role"),
    )


class ConfigurationAuditHistory(Base):
    """
    H. Audit History
    Tracks all administrative changes to periods, employee status, teams, targets, and incentives.
    """
    __tablename__ = "configuration_audit_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    previous_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_by: Mapped[str] = mapped_column(String(100), nullable=False)
    change_timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


class PeriodEmployeeExclusion(Base):
    """
    I. Period-Specific Employee Exclusions
    Excludes an otherwise active employee from a specific reporting period's
    calculations, dropdowns, charts, and team trackers without deactivating or deleting them.
    """
    __tablename__ = "period_employee_exclusions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    period_id: Mapped[int] = mapped_column(Integer, ForeignKey("period_configurations.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False, index=True)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    period: Mapped["PeriodConfiguration"] = relationship("PeriodConfiguration")
    employee: Mapped["Employee"] = relationship("Employee")

    __table_args__ = (
        UniqueConstraint("period_id", "employee_id", name="uq_period_employee_exclusion"),
    )
