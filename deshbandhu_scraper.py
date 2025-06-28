# Clipped Article Images

import os
import asyncio
from pathlib import Path
from tqdm import tqdm
from datetime import datetime
from playwright.async_api import async_playwright

# === CONFIG ===
TODAY = datetime.now().strftime("%Y-%m-%d")
EDITIONS = [
    ("https://epaper.deshbandhu.co.in/view/7760/deshbandhu-delhi/1", "deshbandhu-delhi")
]

ROOT_SAVE = Path("downloads/deshbandhu")
BASE_DOMAIN = "https://epaper.deshbandhu.co.in"
CLIP_BASE = f"{BASE_DOMAIN}/map-image/"

async def download_image(page, url, dest_folder, filename):
    dest_folder.mkdir(parents=True, exist_ok=True)
    filepath = dest_folder / filename
    if filepath.exists():
        return filepath
    response = await page.request.get(url)
    content = await response.body()
    with open(filepath, "wb") as f:
        f.write(content)
    return filepath

async def extract_clippings(page, edition_url, edition_folder, edition_date):
    save_folder = ROOT_SAVE / edition_folder
    current_url = edition_url
    visited = set()
    clip_ids = set()

    print(f"\n🔍 Extracting clippings for: {edition_folder} ({edition_date})")

    while current_url and current_url not in visited:
        visited.add(current_url)
        await page.goto(current_url, timeout=60000)

        try:
            await page.wait_for_selector("a.areamapper-maparea", timeout=5000)
            elements = await page.query_selector_all("a.areamapper-maparea")
            for el in elements:
                clip_id = await el.get_attribute("data-id")
                if clip_id and clip_id not in clip_ids:
                    clip_ids.add(clip_id)
        except:
            print(f"❌ No clipping areas found on: {current_url}")

        try:
            next_btn = await page.query_selector("ul.pagination li.page-item.next a.page-link")
            if next_btn:
                next_url = await next_btn.get_attribute("href")
                if next_url and next_url.startswith("/"):
                    current_url = BASE_DOMAIN + next_url
                elif next_url.startswith("http"):
                    current_url = next_url
                else:
                    break
            else:
                break
        except:
            break

    downloaded = []
    for idx, cid in enumerate(tqdm(sorted(clip_ids), desc=f"⬇️ Downloading clippings for {edition_folder}")):
        clip_url = f"{CLIP_BASE}{cid}.jpg"
        filename = f"{edition_folder}_{edition_date}_article_{idx + 1}.jpg"
        try:
            path = await download_image(page, clip_url, save_folder, filename)
            downloaded.append(path)
        except:
            print(f"⚠️ Failed to download: {clip_url}")

    if not downloaded:
        print(f"⚠️ No clippings downloaded for {edition_folder}")
    else:
        print(f"✅ Downloaded {len(downloaded)} clipping images for {edition_folder} ({edition_date})")

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()

        for url, folder in EDITIONS:
            await extract_clippings(page, url, folder, TODAY)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
