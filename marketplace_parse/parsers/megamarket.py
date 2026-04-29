from playwright.sync_api import Page, sync_playwright
from playwright_stealth import Stealth

from marketplace_parse.parsers.base import ParsedReview, parse_date


REVIEW_SELECTOR = "div.review-item"
NEXT_PAGE_SELECTOR = (
    'button.pui-button-element_only-icon:has(svg path[d^="M8.293 5.293"])'
)


def parse(
    url: str,
    *,
    headless: bool = True,
    slow_mo: int = 500,
    pause_ms: int = 1500,
) -> list[ParsedReview]:
    with Stealth().use_sync(sync_playwright()) as pw:
        browser = pw.chromium.launch(headless=headless, slow_mo=slow_mo)
        try:
            page = browser.new_context().new_page()
            page.goto(url, wait_until="domcontentloaded")
            _open_reviews_page(page)
            return _collect_all_reviews(page, pause_ms=pause_ms)
        finally:
            browser.close()


def _open_reviews_page(page: Page) -> None:
    link = page.locator('a:has-text("Отзывы")').first
    link.wait_for(state="visible", timeout=15_000)
    link.click()
    page.wait_for_selector(REVIEW_SELECTOR, timeout=15_000)


def _goto_next_page(page: Page) -> bool:
    btn = page.locator(NEXT_PAGE_SELECTOR).last
    if btn.count() == 0:
        return False
    if btn.is_disabled():
        return False
    btn.scroll_into_view_if_needed()
    btn.click()
    return True


def _collect_all_reviews(page: Page, *, pause_ms: int) -> list[ParsedReview]:
    reviews: list[ParsedReview] = []
    while True:
        reviews.extend(_extract_reviews(page))
        if not _goto_next_page(page):
            break
        page.wait_for_timeout(pause_ms)
    return reviews


def _extract_reviews(page: Page) -> list[ParsedReview]:
    reviews: list[ParsedReview] = []
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
        reviews.append(ParsedReview(review_text=combined, review_date=review_date))
    return reviews
