"""
Team model — represents a named team with a designated leader and
an active period for month-based performance filtering.

A team is "active for a month" when:
    active_from <= period_end AND (active_until IS NULL OR active_until >= period_start)
"""

from sqlalchemy import Column, Integer, String, Boolean, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    leader_id = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True)
    active_from = Column(Date, nullable=True)        # e.g. 2026-10-01
    active_until = Column(Date, nullable=True)        # NULL = still active
    is_active = Column(Boolean, default=True)
    target = Column(Float, nullable=True, default=0.0)  # team-level base target (optional)

    leader = relationship("Employee", foreign_keys=[leader_id])
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")


class TeamMember(Base):
    """
    Tracks which employees belong to which team and when.
    An employee can move between teams over time.
    """
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    start_date = Column(Date, nullable=True)         # when they joined this team
    end_date = Column(Date, nullable=True)            # NULL = still a member

    team = relationship("Team", back_populates="members")
    employee = relationship("Employee")
