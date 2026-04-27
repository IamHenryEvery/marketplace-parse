from dataclasses import dataclass
from datetime import date, timedelta


RU_MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
    "мая": 5, "июня": 6, "июля": 7, "августа": 8,
    "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}


@dataclass(frozen=True)
class ParsedReview:
    review_text: str
    review_date: date | None = None


def parse_date(text: str, *, today: date | None = None) -> date | None:
    today = today or date.today()
    parts = text.strip().lower().split()
    if len(parts) == 1:
        if parts[0] == "сегодня":
            return today
        if parts[0] == "вчера":
            return today - timedelta(days=1)
        return None
    if len(parts) not in (2, 3):
        return None
    try:
        day = int(parts[0])
        month = RU_MONTHS[parts[1]]
    except (ValueError, KeyError):
        return None
    if len(parts) == 3:
        try:
            year = int(parts[2])
        except ValueError:
            return None
        return date(year, month, day)
    year = today.year
    candidate = date(year, month, day)
    if candidate > today:
        year -= 1
    return date(year, month, day)
