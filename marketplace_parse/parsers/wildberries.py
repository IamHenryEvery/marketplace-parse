from playwright.sync_api import Page, sync_playwright
from playwright_stealth import Stealth

from marketplace_parse.parsers.base import ParsedReview, parse_date


FEEDBACK_SELECTOR = "li.feedback"


def parse(
    url: str,
    *,
    headless: bool = False,
    slow_mo: int = 500,
    pause_ms: int = 1500,
    stagnant_limit: int = 3,
) -> list[ParsedReview]:
    with Stealth().use_sync(sync_playwright()) as pw:
        browser = pw.chromium.launch(headless=headless, slow_mo=slow_mo)
        try:
            context = browser.new_context(
                locale="ru-RU",
                timezone_id="Europe/Moscow",
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded")
            _wait_for_antibot(page)
            _open_reviews_page(page)
            _scroll_until_loaded(page, pause_ms=pause_ms, stagnant_limit=stagnant_limit)
            return _extract_reviews(page)
        finally:
            browser.close()


def _wait_for_antibot(page: Page) -> None:
    page.wait_for_selector("#c_cont", state="detached", timeout=60_000)


def _open_reviews_page(page: Page) -> None:
    link = page.get_by_role("link", name="Смотреть все отзывы").first
    link.wait_for(state="visible", timeout=15_000)
    link.click()
    _wait_for_antibot(page)
    page.wait_for_selector(FEEDBACK_SELECTOR, timeout=30_000)


def _scroll_until_loaded(page: Page, *, pause_ms: int, stagnant_limit: int) -> None:
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


def _extract_reviews(page: Page) -> list[ParsedReview]:
    reviews: list[ParsedReview] = []
    for block in page.query_selector_all(FEEDBACK_SELECTOR):
        fragments: list[str] = []
        bable_parts: list[str] = []
        all_bables = ""

        for item in block.query_selector_all("span.feedback__text--item"):
            text = item.inner_text()
            if text:
                fragments.append(text)

        for bables in block.query_selector_all("div.feedbacks-bables"):
            title = bables.query_selector("span.feedbacks-bables__title")
            if title is not None:
                fragments.append(title.inner_text().strip() + ":")
            for li in bables.query_selector_all("ul.feedbacks-bables__list > li"):
                bable_parts.append(li.inner_text().strip().lower())
            all_bables = ",".join(bable_parts)

        combined = "; ".join(fragments)
        if all_bables:
            combined += all_bables
        if not combined:
            continue

        date_block = block.query_selector("div.feedback__date")
        raw_date = date_block.inner_text().split(",", 1)[0].strip() if date_block else None
        review_date = parse_date(raw_date) if raw_date else None

        reviews.append(ParsedReview(review_text=combined, review_date=review_date))
    return reviews
