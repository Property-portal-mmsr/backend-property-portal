from dotenv import load_dotenv
load_dotenv('.env.local')

from app.database.database import SessionLocal
from app.services.analytics_service import build_dashboard
import app.services.analytics_service as ans
from datetime import date
from collections import defaultdict
from app.services.google_sheet_service import SheetRecord

class MockRecord:
    def __init__(self, rm_name):
        self.rm_name = rm_name
        self.revenue = 1000
        self.key_count = 1
        self.date = date(2026, 10, 15)

def mock_fetch():
    return [
        MockRecord("Arun N"),
        MockRecord("kaveri Gogoi"),
        MockRecord("Sanjota")
    ]

ans.fetch_sheet_records = mock_fetch

db = SessionLocal()
try:
    resp = build_dashboard(db, month='2026-10')
    print("Team Performance payload:")
    for t in resp.team_performance:
        print(f"  {t.team_name}: {t.revenue}")
finally:
    db.close()
