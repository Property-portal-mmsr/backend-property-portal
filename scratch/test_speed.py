import sys, time
sys.path.append('.')
from app.database.database import SessionLocal
from app.models.property import Property

db = SessionLocal()
query = db.query(Property)

t0 = time.time()
total = query.count()
t1 = time.time()
print(f"Count took {t1 - t0:.2f}s (Total: {total})")

t0 = time.time()
items = query.limit(10).all()
t1 = time.time()
print(f"Limit(10) took {t1 - t0:.2f}s (Items: {len(items)})")

from sqlalchemy.orm import selectinload
t0 = time.time()
items_full = query.options(
    selectinload(Property.property_pricing),
    selectinload(Property.property_images),
    selectinload(Property.property_amenities)
).limit(10).all()
t1 = time.time()
print(f"Full fetch took {t1 - t0:.2f}s")
