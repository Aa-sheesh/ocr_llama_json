# Clipped Article Images

import asyncio
import time
from pathlib import Path
from datetime import datetime  # added for execution date

import requests
from playwright.async_api import (
    async_playwright,
    Browser,
    Page,
    Error as PWError,
)
from tqdm import tqdm

# ──────────────── configurable ────────────────────────────────────────────── #

SAVE_ROOT = Path("downloads")
PUBLICATION_NAME = "kannada_prabha"
EDITION_NAME = "bangalore"
HEADLESS = True          # set False to watch the browser
TIMEOUT = 25_000         # ms – Playwright waits
RETRY_MAX = 3            # per image download

# ──────────────── helpers ─────────────────────────────────────────────────── #

def download(url: str, dest: Path) -> None:
    """Stream-download *url*→*dest*  with retries & progress bar."""
    dest.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, RETRY_MAX + 1):
        try:
            with requests.get(url, stream=True, timeout=3) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                with dest.open("wb") as fh, tqdm(
                    total=total,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=dest.name,
                    leave=False,
                ) as bar:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            fh.write(chunk)
                            bar.update(len(chunk))
            print(f"Downloaded: {url} → {dest}")
            return
        except Exception as exc:
            if attempt == RETRY_MAX:
                print(f"Failed to download {url} after {RETRY_MAX} attempts: {exc}")
            else:
                print(f"Retry {attempt}/{RETRY_MAX} for {url}: {exc}")
                time.sleep(2 * attempt)


async def remove_popups(page: Page) -> None:
    """Remove common modals/popups that block clicks."""
    selectors = [
        "div[class*=modal]",
        "div[class*=popup]",
        "div[class*=ads]",
        "div[id*=ad]",
        ".swal2-container",
    ]
    for sel in selectors:
        for el in await page.query_selector_all(sel):
            try:
                await page.evaluate("(el) => el.remove()", el)
            except Exception:
                pass


# ──────────────── main page-harvest logic ─────────────────────────────────── #

async def harvest_articles_on_page(edition_page: Page, page_idx: int, date_seen: str, date_folder: Path) -> int:
    await edition_page.wait_for_selector("div.carousel-item.active", timeout=TIMEOUT)
    overlays = await edition_page.query_selector_all("div.carousel-item.active div.overlay")
    if not overlays:
        print(f"Page-{page_idx:02d}: 0 overlays found")
        return 0

    print(f"Page-{page_idx:02d}: {len(overlays)} cropped articles…")
    saved = 0

    for idx, ov in enumerate(overlays, 1):
        await remove_popups(edition_page)
        clicked = False
        try:
            await edition_page.evaluate("(el) => el.click()", ov)
            clicked = True
        except Exception:
            try:
                await ov.click(force=True, timeout=4000)
                clicked = True
            except Exception as e:
                print(f"    ↳ [skip] overlay {idx} not clickable ({e})")
        if not clicked:
            continue

        async with edition_page.context.expect_page() as new_tab:
            pass
        article_page = await new_tab.value

        try:
            await article_page.wait_for_selector(
                "div.epaper-article-image-container img",
                timeout=TIMEOUT,
            )
            img_el = await article_page.query_selector("div.epaper-article-image-container img")
            src = await img_el.get_attribute("src")

            if not src or "/ArticleImages/" not in src:
                print(f"    ↳ [skip] no ArticleImages/ src for overlay {idx}")
                continue

            ext = Path(src).suffix
            filename = f"{PUBLICATION_NAME}_{date_seen}_{page_idx:02d}_article_{idx:02d}{ext}"
            dest = date_folder / filename
            download(src, dest)
            saved += 1

        except PWError:
            print(f"    ↳ [skip] article tab timeout (overlay {idx})")
        finally:
            await article_page.close()

    return saved

async def scrape_today() -> None:
    # Determine execution date instead of parsing from URL
    date_seen = datetime.now().strftime("%Y-%m-%d")
    print(f"Using execution date: {date_seen}")

    date_folder = SAVE_ROOT / PUBLICATION_NAME / EDITION_NAME
    date_folder.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        browser: Browser = await pw.chromium.launch(headless=HEADLESS)
        context = await browser.new_context(viewport={"width":1280,"height":900}, accept_downloads=False)
        page: Page = await context.new_page()

        start_url = "https://kpepaper.asianetnews.com/edition/BENGALURU/KANPRABHA_BG/page/1"
        print("Opening edition…")
        await page.goto(start_url, timeout=60_000)

        total_saved = 0
        current_page = 1

        while True:
            saved = await harvest_articles_on_page(page, current_page, date_seen, date_folder)
            total_saved += saved

            next_btn = page.locator("nav.pagination li.page-item button[aria-label=Next]").first
            try:
                enabled = await next_btn.is_enabled()
            except Exception:
                enabled = False

            if not enabled:
                break

            await next_btn.click()
            current_page += 1
            try:
                await page.wait_for_selector(f"nav.pagination li.active >> text={current_page}", timeout=TIMEOUT)
            except PWError:
                print(f"Could not confirm active page {current_page} (continuing anyway)")

        print(f"Done – {total_saved} images downloaded.")
        await browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(scrape_today())
    except KeyboardInterrupt:
        print("Interrupted by user")

