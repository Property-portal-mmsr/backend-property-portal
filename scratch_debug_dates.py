import sys, os, csv, io, httpx
sys.path.append(os.getcwd())
from app.core.config import GOOGLE_SHEET_URL
from app.services.google_sheet_service import _extract_sheet_id

sheet_id = _extract_sheet_id(GOOGLE_SHEET_URL)
csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&tq=select+*"
r = httpx.get(csv_url)
reader = csv.reader(io.StringIO(r.text))
rows = list(reader)[1:]

empty_streaks = []
streak = 0
for i, row in enumerate(rows):
    d = str(row[1] if len(row)>1 else '').strip()
    rm = str(row[2] if len(row)>2 else '').strip()
    if not d and not rm:
        streak += 1
    else:
        if streak > 0:
            empty_streaks.append((i-streak, streak))
        streak = 0
print(empty_streaks)
