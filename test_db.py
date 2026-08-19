import time
from app.database.database import SessionLocal
from app.services.property_service import PropertyService

db = SessionLocal()
start = time.time()
props = PropertyService.get_all_properties(db=db)
end = time.time()
print(f"Fetched {len(props)} properties in {end - start:.2f} seconds")
db.close()
