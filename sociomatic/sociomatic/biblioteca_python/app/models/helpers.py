import re
from datetime import date, datetime


def row_to_dict(row):
    return dict(row) if row is not None else None


def today_iso() -> str:
    return date.today().isoformat()


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


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


def valid_period(value: str) -> bool:
    return bool(re.fullmatch(r"\d{4}-\d{2}", value or "")) and 1 <= int(value[5:7]) <= 12

