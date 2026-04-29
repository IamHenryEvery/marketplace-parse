import json
from datetime import date, timedelta
from pathlib import Path


from playwright.sync_api import Page, sync_playwright
from playwright_stealth import Stealth


PRODUCT_URL = "https://megamarket.ru/promo-page/details/#?slug=garnitura-a4tech-m30-chernyy-krasnyy-m30-blackred-100042947316_99804&merchantId=99804&exclusiveMerchantId=99804&exclusiveWarehouseId=1772874"
OUTPUT_PATH = Path(__file__).parent / "mm_reviews.json"
REVIEW_SELECTOR = "div.review-item"

RU_MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
    "мая": 5, "июня": 6, "июля": 7, "августа": 8,
    "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}


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


def open_reviews_page(page: Page) -> None:
    link = page.locator('a:has-text("Отзывы")').first
    link.wait_for(state="visible", timeout=15_000)
    link.click()
    page.wait_for_selector(REVIEW_SELECTOR, timeout=15_000)


NEXT_PAGE_SELECTOR = (
    'button.pui-button-element_only-icon:has(svg path[d^="M8.293 5.293"])'
)


def goto_next_page(page: Page) -> bool:
    """Click pagination next-arrow. Returns False when it's disabled (last page)."""
    btn = page.locator(NEXT_PAGE_SELECTOR).last
    if btn.count() == 0:
        return False
    if btn.is_disabled():
        return False
    btn.scroll_into_view_if_needed()
    btn.click()
    return True


def collect_all_reviews(page: Page, *, pause_ms: int = 1500) -> list[dict]:
    """Page through the review list, accumulating reviews from every page."""
    reviews: list[dict] = []
    while True:
        reviews.extend(extract_reviews(page))
        if not goto_next_page(page):
            break
        page.wait_for_timeout(pause_ms)
    return reviews


def extract_reviews(page: Page) -> list[dict]:
    reviews: list[dict] = []
    for block in page.query_selector_all(REVIEW_SELECTOR):
        date_block = block.query_selector("time.review-item-header__date")
        raw_date = date_block.inner_text() if date_block else None
        review_date = parse_date(raw_date) if raw_date else None

        parts: list[str] = []
        for el in block.query_selector_all("div.review-item__body, div.text-block"):
            lines = [ln.strip() for ln in el.inner_text().split("\n") if ln.strip()]
            t = ": ".join(lines)
            if t:
                parts.append(t)
        combined = "; ".join(parts)
        if not combined:
            continue
        reviews.append({
            "review_text": combined,
            "date_raw": raw_date,
            "date": review_date.isoformat() if review_date else None,
        })
    return reviews


def main() -> None:
    with Stealth().use_sync(sync_playwright()) as pw:
        browser = pw.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context()
        page = context.new_page()

        page.goto(PRODUCT_URL, wait_until="domcontentloaded")
        open_reviews_page(page)
        reviews = collect_all_reviews(page)

        OUTPUT_PATH.write_text(
            json.dumps(reviews, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Saved {len(reviews)} reviews to {OUTPUT_PATH}")

        browser.close()


if __name__ == "__main__":
    main()
