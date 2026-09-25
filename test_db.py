import sys
sys.path.append('.')
from app.database.database import SessionLocal, DATABASE_URL
from app.models.property import Property

print("URL:", DATABASE_URL)
db = SessionLocal()
try:
    props = db.query(Property).count()
    print("PROPERTIES IN DB:", props)
except Exception as e:
    print("ERROR:", e)
