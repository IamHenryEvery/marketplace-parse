import json
from pathlib import Path
from datetime import date, timedelta
from playwright.sync_api import Page, sync_playwright
from playwright_stealth import Stealth

# https://www.wildberries.ru/catalog/286175495/detail.aspx?targetUrl=SN штаны
# https://www.wildberries.ru/catalog/684352961/detail.aspx?targetUrl=SN ноут
PRODUCT_URL = "https://www.wildberries.ru/catalog/684352961/detail.aspx?targetUrl=SN"
OUTPUT_PATH = Path(__file__).parent / "wb_reviews.json"
FEEDBACK_SELECTOR = "li.feedback"
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

def wait_for_antibot(page: Page) -> None:
    page.wait_for_selector("#c_cont", state="detached", timeout=60_000)


def open_reviews_page(page: Page) -> None:
    link = page.get_by_role("link", name="Смотреть все отзывы").first
    link.wait_for(state="visible", timeout=15_000)
    link.click()
    wait_for_antibot(page)
    page.wait_for_selector(FEEDBACK_SELECTOR, timeout=30_000)


def scroll_until_loaded(page: Page, *, pause_ms: int = 1500, stagnant_limit: int = 3) -> None:
    stagnant = 0
    prev_count = 0
    while True:
        blocks = page.query_selector_all(FEEDBACK_SELECTOR)
        if blocks:
            blocks[-1].scroll_into_view_if_needed()
        page.mouse.wheel(0, 2000)
        page.wait_for_timeout(pause_ms)
        current = len(page.query_selector_all(FEEDBACK_SELECTOR))
        if current == prev_count:
            stagnant += 1
            if stagnant >= stagnant_limit:
                break
        else:
            stagnant = 0
        prev_count = current


def extract_reviews(page: Page) -> list[dict]:
    reviews: list[dict] = []
    for block in page.query_selector_all(FEEDBACK_SELECTOR):
        # review_info = {}
        fragments: list[str] = []
        bable_parts: list[str] = []
        
        for item in block.query_selector_all("span.feedback__text--item"):
            text = item.inner_text()
            if text:
                fragments.append(text)
        for bables in block.query_selector_all("div.feedbacks-bables"):
            title = bables.query_selector("span.feedbacks-bables__title")
            
            if title is not None:
                title_text = title.inner_text().strip() + ':'
                fragments.append(title_text)
                
            for li in bables.query_selector_all("ul.feedbacks-bables__list > li"):
                li_text = li.inner_text().strip().lower()
                bable_parts.append(li_text)
            all_bables = ','.join(bable_parts)
        combined = "; ".join(fragments)
        if all_bables:
            combined += all_bables
        if not combined:
            # review_info['text'] = combined
            continue
        date_block = block.query_selector('div.feedback__date')
        raw_date = date_block.inner_text().split(",", 1)[0].strip() if date_block else None
        print(f'raw_date = {raw_date}')
        review_date = parse_date(raw_date) if raw_date else None
        reviews.append({
            "text": combined,
            "date_raw": raw_date,
            "date": review_date.isoformat() if review_date else None,
        })
            # reviews.append({"text": combined})
    return reviews


def main() -> None:
    with Stealth().use_sync(sync_playwright()) as pw:
        browser = pw.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        page.goto(PRODUCT_URL, wait_until="domcontentloaded")
        wait_for_antibot(page)
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
