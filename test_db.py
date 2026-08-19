from app.database.database import SessionLocal
from app.services.property_service import PropertyService

db = SessionLocal()
try:
    props = PropertyService.get_all_properties(db)
    print("Success", len(props))
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()
