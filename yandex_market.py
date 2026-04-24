import json
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

# https://market.yandex.ru/cc/9JEhbF аэрогриль
# https://market.yandex.ru/cc/9JFmGf видеокарта
PRODUCT_URL = "https://market.yandex.ru/cc/9JEhbF"
OUTPUT_PATH = Path(__file__).parent / "reviews.json"
REVIEW_SELECTOR = 'div[data-baobab-name="review"]'


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


def extract_reviews(page: Page) -> list[str]:
    reviews: list[str] = []
    for block in page.query_selector_all(REVIEW_SELECTOR):
        description = block.query_selector('span[data-auto="review-description"]')
        if description is None:
            continue
        texts = [s.inner_text().strip() for s in description.query_selector_all("span")]
        combined = "; ".join(t for t in texts if t)
        if combined:
            reviews.append(combined)
    return reviews


def main() -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, slow_mo=500)
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
