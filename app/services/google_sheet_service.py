"""
Google Sheet Service
Fetches live data from the configured Google Sheet CSV export endpoint.
Only extracts: Date, RM Name, Key Count, Revenue columns.
"""

import csv
import io
import re
import httpx
import logging
from datetime import date
from typing import List, Optional
from dataclasses import dataclass

from app.core.config import GOOGLE_SHEET_URL

logger = logging.getLogger(__name__)

# Patterns that identify monthly separator/header rows (e.g. "April 2026", "August 2026")
_MONTH_HEADER_RE = re.compile(
    r"^(january|february|march|april|may|june|july|august|september|october|november|december)"
    r"\s+\d{4}$",
    re.IGNORECASE,
)

# Multiple date format attempts
_DATE_FORMATS = ["%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%d/%m/%Y"]


@dataclass
class SheetRecord:
    date: date
    rm_name: str
    key_count: float
    revenue: float


def _extract_sheet_id(url: str) -> str:
    """Extract sheet ID from a Google Sheets URL."""
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if not match:
        raise ValueError(f"Cannot extract sheet ID from URL: {url}")
    return match.group(1)


def _parse_number(value: str) -> float:
    """Parse a numeric string, handling commas and whitespace. Returns 0 on failure."""
    if not value or not value.strip():
        return 0.0
    cleaned = value.strip().replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_date(value: str) -> Optional[date]:
    """Try multiple date formats. Returns None if unparseable."""
    from datetime import datetime

    if not value or not value.strip():
        return None
    value = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _is_separator_row(row: List[str]) -> bool:
    """
    Detect monthly separator / header rows like "April 2026".
    These rows have a month-year string in the first non-empty cell
    and the rest is empty.
    """
    non_empty = [cell.strip() for cell in row if cell.strip()]
    if not non_empty:
        return True  # completely empty row

    first = non_empty[0]
    if _MONTH_HEADER_RE.match(first):
        return True

    if re.match(r"^\d{4}$", first):
        return True

    return False


def fetch_sheet_records() -> List[SheetRecord]:
    """
    Fetch the latest data from Google Sheets and return cleaned records.
    Filters:
    - Ignores completely empty rows
    - Ignores rows where Date is empty or invalid
    - Ignores monthly separator/header rows
    - Empty Key Count -> 0, Empty Revenue -> 0
    - Trims spaces from RM names
    """
    if not GOOGLE_SHEET_URL:
        logger.warning("GOOGLE_SHEET_URL not configured, returning empty records.")
        return []

    sheet_id = _extract_sheet_id(GOOGLE_SHEET_URL)
    csv_url = (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        f"/gviz/tq?tqx=out:csv&tq=select+*"
    )

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(csv_url)
            response.raise_for_status()
        content = response.text
    except Exception as e:
        logger.error(f"Failed to fetch Google Sheet: {e}")
        raise RuntimeError(f"Could not fetch Google Sheet data: {e}")

    records: List[SheetRecord] = []

    reader = csv.reader(io.StringIO(content))
    header_row = None

    col_date = None
    col_rm_name = None
    col_key_count = None
    col_revenue = None

    for row in reader:
        # Skip completely empty rows
        if not any(cell.strip() for cell in row):
            continue

        # Detect and parse header row (first non-empty row)
        if header_row is None:
            header_row = [cell.strip().lower() for cell in row]
            for i, col in enumerate(header_row):
                if col == "date":
                    col_date = i
                elif col == "rm name":
                    col_rm_name = i
                elif col == "key count":
                    col_key_count = i
                elif col == "revenue":
                    col_revenue = i
            continue

        # Ensure we have enough columns
        if len(row) < 2:
            continue

        # Skip separator / header rows (e.g. "April 2026")
        if _is_separator_row(row):
            continue

        # --- Extract Date ---
        date_str = row[col_date].strip() if col_date is not None and col_date < len(row) else ""
        parsed_date = _parse_date(date_str)
        if parsed_date is None:
            continue

        # --- Extract RM Name ---
        rm_raw = row[col_rm_name].strip() if col_rm_name is not None and col_rm_name < len(row) else ""
        if not rm_raw:
            continue

        # --- Extract Key Count & Revenue ---
        kc_str = row[col_key_count].strip() if col_key_count is not None and col_key_count < len(row) else ""
        rev_str = row[col_revenue].strip() if col_revenue is not None and col_revenue < len(row) else ""

        key_count = _parse_number(kc_str)
        revenue = _parse_number(rev_str)

        records.append(
            SheetRecord(
                date=parsed_date,
                rm_name=rm_raw,
                key_count=key_count,
                revenue=revenue,
            )
        )

    logger.info(f"Fetched {len(records)} valid records from Google Sheet.")
    return records
