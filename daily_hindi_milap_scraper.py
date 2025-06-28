"""
Clipped Article Images
"""
import asyncio
import datetime
import os
from typing import Optional

from playwright.async_api import async_playwright, Page, ElementHandle, \
    TimeoutError as PlaywrightTimeoutError


# === Configuration ===
MAX_RETRIES = 3
TIMEOUT_POPUP = 5000
TIMEOUT_LOAD = 15000
TIMEOUT_SELECTOR = 10000
HINDI_MILAP_LOGO_NAME = "HindiMilapLogo1"
HINDI_MILAP_LOGO_DOWNLOADED = False

date = datetime.date.today()

OUTPUT_DIR = "downloads/daily_hindi_milap/hyderabad"
BASE_URL_TEMPLATE = "http://webmilap.com/edition/HindiMilap/HINDIMIL_HIN/HINDIMIL_HIN_{date}/page/{page}"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def download_image(url: str, filepath: str):
    import requests
    global HINDI_MILAP_LOGO_DOWNLOADED
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        if HINDI_MILAP_LOGO_NAME in url:
            if HINDI_MILAP_LOGO_DOWNLOADED:
                print(f"Skipped duplicate logo: {url}")
                return
            HINDI_MILAP_LOGO_DOWNLOADED = True

        with open(filepath, 'wb') as f:
            f.write(r.content)
        print(f"Downloaded: {url} -> {filepath}")
    except Exception as e:
        print(f"Failed downloading {url}: {e}")


async def remove_overlay(element: ElementHandle):
    await element.evaluate('''(container) => {
        const overlay = container.querySelector('.overlay');
        if (overlay) overlay.style.pointerEvents = 'none';
    }''')


async def open_article_popup(page: Page, article_div: ElementHandle) -> \
        Optional[Page]:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with page.expect_popup(timeout=TIMEOUT_POPUP) as popup_info:
                await article_div.click(force=True)
            return await popup_info.value
        except Exception as e:
            print(f"Popup attempt {attempt} failed: {e}")
            await page.wait_for_timeout(1000)
    return None


async def extract_images_from_tab(tab: Page, page_num: int, article_num: int):
    try:
        await tab.wait_for_load_state('networkidle', timeout=TIMEOUT_LOAD)
    except PlaywrightTimeoutError:
        print(
            f"Timeout waiting for networkidle in article {article_num} on page {page_num}")

    try:
        await tab.wait_for_selector('.card-profile.epaper-article-card.card',
                                    timeout=TIMEOUT_SELECTOR)
        container = await tab.query_selector(
            '.card-profile.epaper-article-card.card')
    except PlaywrightTimeoutError:
        print(
            f"Fallback: card not found in article {article_num} on page {page_num}")
        container = await tab.query_selector("body")

    if not container:
        print(
            f"No usable container found in article {article_num} on page {page_num}")
        return

    images = await container.query_selector_all("img")
    print(
        f"Found {len(images)} images in article {article_num} on page {page_num}")
    for idx, img in enumerate(images, 1):
        src = await img.get_attribute("src")
        if src:
            ext = os.path.splitext(src)[-1].split("?")[0] or ".jpg"
            filename = f"daily_hindi_milap{date.strftime('%Y_%m_%d')}{page_num}{article_num}{ext}"
            filepath = os.path.join(OUTPUT_DIR, filename)
            await asyncio.to_thread(download_image, src, filepath)


async def process_article(page: Page, article_div: ElementHandle,
                          page_num: int, article_num: int):
    try:
        await remove_overlay(article_div)
        if await article_div.is_visible():
            await article_div.scroll_into_view_if_needed(timeout=3000)

        new_tab = await open_article_popup(page, article_div)
        if not new_tab:
            print(
                f"Failed to open popup for article {article_num} on page {page_num}")
            return

        await extract_images_from_tab(new_tab, page_num, article_num)
        await new_tab.close()

    except Exception as e:
        print(
            f"Unexpected error in article {article_num} on page {page_num}: {e}")


async def scrape_page(page: Page, page_index: int):
    await page.click(f".carousel-indicators li:nth-child({page_index + 1})")
    await page.wait_for_selector(
        ".carousel-item.active div.epaper-article-container",
        timeout=TIMEOUT_SELECTOR)
    current_item = (await page.query_selector_all(".carousel-item"))[
        page_index]
    articles = await current_item.query_selector_all(
        "div.epaper-article-container")
    print(f"Page {page_index + 1} has {len(articles)} articles")

    for idx, article in enumerate(articles, 1):
        await process_article(page, article, page_index + 1, idx)


async def scrape_all_carousel_items(page: Page):
    await page.wait_for_selector(".carousel-inner", timeout=TIMEOUT_SELECTOR)
    indicators = await page.query_selector_all(".carousel-indicators li")
    print(f"Carousel has {len(indicators)} pages")

    for index in range(len(indicators)):
        await scrape_page(page, index)


async def hindi_milap_crawler():
    today = datetime.date.today()
    base_url = BASE_URL_TEMPLATE.format(date=today.strftime("%Y%m%d"), page=1)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(base_url)
        await scrape_all_carousel_items(page)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(hindi_milap_crawler())
