import json
from datetime import date, timedelta
from pathlib import Path


from playwright.sync_api import Page, sync_playwright
from playwright_stealth import Stealth


# https://market.yandex.ru/cc/9KxEJM комплект одежды
# https://market.yandex.ru/cc/9JFmGf видеокарта
# https://market.yandex.ru/cc/9KV93a сковорода
# https://market.yandex.ru/cc/9Kwnea покрывало
PRODUCT_URL = "https://market.yandex.ru/cc/9KV93a"
OUTPUT_PATH = Path(__file__).parent / "reviews.json"
REVIEW_SELECTOR = 'div[data-baobab-name="review"]'

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
    link = page.locator('a[href*="reviews"]:has-text("отзыв"):has-text("оцен")').first
    link.wait_for(state="visible", timeout=15_000)
    link.click()
    page.wait_for_selector(REVIEW_SELECTOR, timeout=15_000)


def scroll_until_loaded(page: Page, *, pause_ms: int = 1500, stagnant_limit: int = 3) -> None:
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


def extract_reviews(page: Page) -> list[dict]:
    reviews: list[dict] = []
    for block in page.query_selector_all(REVIEW_SELECTOR):
        date_block = block.query_selector('div[data-auto="created-date"]')
        # print(f'date block = {date_block}')
        raw_date = date_block.inner_text() if date_block else None
        # print(f'raw_date = {raw_date}')
        review_date = parse_date(raw_date) if raw_date else None
        description = block.query_selector('span[data-auto="review-description"]')
        if description is None:
            continue
        texts = [s.inner_text().strip() for s in description.query_selector_all("span")]
        combined = "; ".join(t for t in texts if t and t[-1] != ':')
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
        browser = pw.chromium.launch(headless=True, slow_mo=500)
        context = browser.new_context()
        page = context.new_page()

        page.goto(PRODUCT_URL, wait_until="domcontentloaded")
        open_reviews_page(page)
        scroll_until_loaded(page)
        reviews = extract_reviews(page)

        OUTPUT_PATH.write_text(
            json.dumps(reviews, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Saved {len(reviews)} reviews to {OUTPUT_PATH}")

        browser.close()


if __name__ == "__main__":
    main()
