"""
Migration 04: Dynamic Period-Based Target, Incentive, Team Management and Employee Status System
Usage:
    python scripts/migration/04_period_target_incentive_system.py
"""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.database.database import SessionLocal
from app.services.migration_seed_service import ensure_period_system_migrated_and_seeded


def main():
    db = SessionLocal()
    try:
        summary = ensure_period_system_migrated_and_seeded(db)
        print("Migration 04 completed successfully:")
        print("  Deactivated employees (effective 2026-11-01):", summary["deactivated_employees"])
        print("  Periods seeded:", summary["periods_seeded"])
        print("  Teams ensured:", summary["teams_ensured"])
    finally:
        db.close()


if __name__ == "__main__":
    main()

