import sys
sys.path.append('.')
from app.database.database import SessionLocal
from app.repositories.property_repository import PropertyRepository

db = SessionLocal()
res, total, stats = PropertyRepository.get_all(db)
print("Total from get_all:", total)
