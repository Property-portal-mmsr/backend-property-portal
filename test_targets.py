from app.database.database import SessionLocal
from app.services.analytics_service import _get_targets_for_month
from app.models.employee import Employee
db = SessionLocal()
emps = db.query(Employee).all()
t = _get_targets_for_month(db, emps, "2026-09")
for e in emps:
    print(e.name, getattr(e, 'monthly_target', 'MISSING'), t.get(e.id))
