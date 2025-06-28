import asyncio
import os
from datetime import datetime

from playwright.async_api import async_playwright


async def download_pdf():
    today_date = datetime.now().strftime("%Y-%m-%d")
    today = datetime.strptime(today_date, "%Y-%m-%d").strftime(
        "%Y_%m_%d")
    edition_name = "kolkata"  # You can dynamically detect this if needed

    # Build the full save path
    folder_path = os.path.join("downloads","samagya", edition_name)
    os.makedirs(folder_path, exist_ok=True)
    file_name = f"{edition_name}_{today}.pdf"
    file_path = os.path.join(folder_path, file_name)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        await page.goto("https://epaper.samagya.in/")

        async with page.expect_download() as download_info:
            await page.click("a.btn-pdfdownload")

        download = await download_info.value
        await download.save_as(file_path)
        print(f"Downloaded to: {file_path}")

        await browser.close()


asyncio.run(download_pdf())
