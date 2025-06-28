#Clipped Article Images 

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import aiohttp

# === CONFIG ===
BASE_DATE = "20250529"
EDITION_NAME = "POKNAPHAM"
EDITION_CODE = "POKNAP_POK"
CLIP_DIR = Path(f"downloads/{EDITION_NAME.lower()}/{EDITION_CODE.lower()}")
CLIP_DIR.mkdir(parents=True, exist_ok=True)

async def download_image(session, url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                with open(dest, 'wb') as f:
                    f.write(await resp.read())
                print(f"✅ Downloaded: {dest.name}")
                return True
    except Exception as e:
        print(f"❌ Error downloading {url}: {e}")
    return False

async def extract_article_ids(page):
    containers = await page.query_selector_all("div.epaper-article-container > div.overlay")
    ids = []
    for c in containers:
        article_id = await c.get_attribute("id")
        if article_id:
            ids.append(article_id)
    return ids

async def extract_article_image_url(article_page):
    try:
        await article_page.wait_for_selector("div.epaper-article-image-container img", timeout=7000)
        img = await article_page.query_selector("div.epaper-article-image-container img")
        if img:
            src = await img.get_attribute("src")
            if src and "ArticleImages" in src:
                return src
    except Exception:
        return None
    return None

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        main_page = await browser.new_page()
        article_page = await browser.new_page()
        session = aiohttp.ClientSession()

        page_no = 1
        while True:
            print(f"🔎 Scanning page {page_no}")
            main_url = f"https://epaper.poknapham.in/edition/{EDITION_NAME}/{EDITION_CODE}/{EDITION_CODE}_{BASE_DATE}/page/{page_no}"
            try:
                await main_page.goto(main_url, timeout=10000)
                await main_page.wait_for_timeout(1000)
                article_ids = await extract_article_ids(main_page)
                if not article_ids:
                    print("✅ No more articles found. Done.")
                    break

                for idx, article_id in enumerate(article_ids, start=1):
                    article_url = f"https://epaper.poknapham.in/editionname/{EDITION_NAME}/{EDITION_CODE}/page/{page_no}/article/{article_id}"
                    print(f"🔗 Visiting article: {article_url}")
                    await article_page.goto(article_url)
                    img_url = await extract_article_image_url(article_page)
                    if img_url:
                        filename = f"{EDITION_NAME}_{BASE_DATE}_{page_no}_article_{idx}.png"
                        save_path = CLIP_DIR / filename
                        await download_image(session, img_url, save_path)
                    else:
                        print(f"❌ No image URL for {article_id}")

                page_no += 1

            except Exception as e:
                print(f"❌ Failed to process page {page_no}: {e}")
                break

        await session.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

