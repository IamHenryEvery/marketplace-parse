from dataclasses import dataclass
from datetime import date

from playwright.sync_api import Page, sync_playwright


REVIEW_SELECTOR = 'div[data-baobab-name="review"]'

_MONTHS_TRANSLATION = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
    "мая": 5, "июня": 6, "июля": 7, "августа": 8,
    "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}


def _parse_date(text: str, *, today: date | None = None) -> date | None:
    today = today or date.today()
    parts = text.strip().lower().split()
    if len(parts) not in (2, 3):
        return None
    try:
        day = int(parts[0])
        month = _MONTHS_TRANSLATION[parts[1]]
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


@dataclass(frozen=True)
class ParsedReview:
    review_text: str
    review_date: date | None = None


def parse(
    url: str,
    *,
    headless: bool = False,
    slow_mo: int = 500,
    pause_ms: int = 1500,
    stagnant_limit: int = 3,
) -> list[ParsedReview]:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless, slow_mo=slow_mo)
        try:
            page = browser.new_context().new_page()
            page.goto(url, wait_until="domcontentloaded")
            _open_reviews_page(page)
            _scroll_until_loaded(page, pause_ms=pause_ms, stagnant_limit=stagnant_limit)
            return _extract_reviews(page)
        finally:
            browser.close()


def _open_reviews_page(page: Page) -> None:
    link = page.locator('a[href*="reviews"]:has-text("отзыв"):has-text("оцен")').first
    link.wait_for(state="visible", timeout=15_000)
    link.click()
    page.wait_for_selector(REVIEW_SELECTOR, timeout=15_000)


def _scroll_until_loaded(page: Page, *, pause_ms: int, stagnant_limit: int) -> None:
    stagnant = 0
    prev_count = 0
    while True:
        blocks = page.query_selector_all(REVIEW_SELECTOR)
        if blocks:
            blocks[-1].scroll_into_view_if_needed()
        page.mouse.wheel(0, 2000)
        page.wait_for_timeout(pause_ms)
        current = len(page.query_selector_all(REVIEW_SELECTOR))
        if current == prev_count:
            stagnant += 1
            if stagnant >= stagnant_limit:
                break
        else:
            stagnant = 0
        prev_count = current


def _extract_reviews(page: Page) -> list[ParsedReview]:
    reviews: list[ParsedReview] = []
    for block in page.query_selector_all(REVIEW_SELECTOR):
        description = block.query_selector('span[data-auto="review-description"]')
        if description is None:
            continue
        texts = [s.inner_text().strip() for s in description.query_selector_all("span")]
        combined = "; ".join(t for t in texts if t)
        if not combined:
            continue

        date_block = block.query_selector('span[data-auto="created-date"]')
        review_date = _parse_date(date_block.inner_text()) if date_block else None

        reviews.append(ParsedReview(review_text=combined, review_date=review_date))
    return reviews
