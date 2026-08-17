import re
from datetime import date, datetime


def row_to_dict(row):
    return dict(row) if row is not None else None


def today_iso() -> str:
    return date.today().isoformat()


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def parse_decimal(value) -> float:
    text = str(value if value is not None else "").strip()
    if not text:
        return 0.0
    text = text.replace("$", "").replace(" ", "")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    return float(text)


def current_period() -> str:
    today = date.today()
    return f"{today.year:04d}-{today.month:02d}"


def next_period(periodo: str | None = None) -> str:
    if periodo:
        year, month = map(int, periodo.split("-"))
    else:
        today = date.today()
        year, month = today.year, today.month
    month += 1
    if month == 13:
        year += 1
        month = 1
    return f"{year:04d}-{month:02d}"


def add_months(periodo: str, months: int) -> str:
    year, month = map(int, periodo.split("-"))
    month += months
    year += (month - 1) // 12
    month = ((month - 1) % 12) + 1
    return f"{year:04d}-{month:02d}"


def valid_period(value: str) -> bool:
    return bool(re.fullmatch(r"\d{4}-\d{2}", value or "")) and 1 <= int(value[5:7]) <= 12


def valid_date(value: str) -> bool:
    try:
        datetime.strptime(value or "", "%Y-%m-%d")
        return True
    except ValueError:
        return False
