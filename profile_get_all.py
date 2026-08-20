from app.db.session import SessionLocal
from app.repositories.property_repository import PropertyRepository
from app.schemas.property import PropertyResponse
import time

db = SessionLocal()
start = time.time()
props = PropertyRepository.get_all(db)
print("DB get_all took", time.time() - start)

start = time.time()
for p in props:
    _ = PropertyResponse.from_db(p)
print("Serialization took", time.time() - start)
