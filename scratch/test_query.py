import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import SessionLocal
from app.repositories.property_repository import PropertyRepository

db = SessionLocal()
try:
    res = PropertyRepository.get_all(db, categories=["PG / Co-living", "Rental Apartment", "Buy / Sale"])
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()
