from app.database.database import SessionLocal
from app.models.property import Property

db = SessionLocal()
properties = db.query(Property).order_by(Property.id.desc()).limit(1).all()
for p in properties:
    print(f"ID: {p.id}, name: {p.property_name}, furnishing: {p.furnishing}, preferredFor: {p.preferred_for}")
