import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import os
import urllib.request

class StateTimesDownloader:
    def __init__(self):
        self.today = datetime.today()
        self.date_str = self.today.strftime("%Y-%m-%d")
        self.base_dir = os.path.join("downloads", "state_times")
        self.browser = None
        self.page = None
        self.edition_name = "jammu"

    async def setup(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        await self.page.goto("https://epaper.statetimes.in/", timeout=60000)

    async def select_today_date(self):
        day = self.today.day
        month = self.today.month - 1  # 0-indexed
        year = self.today.year

        await self.page.select_option("#orderdate_Month_ID", str(month))
        await self.page.select_option("#orderdate_Day_ID", str(day))
        await self.page.fill("#orderdate_Year_ID", str(year))

        await self.page.click("#Button1")
        await self.page.wait_for_timeout(5000)

    async def extract_edition_name(self):
        title = await self.page.title()
        if " - " in title:
            self.edition_name = title.split(" - ")[-1].strip().replace(" ", "_").lower()
        else:
            self.edition_name = "jammu"

    def create_folder(self):
        folder_path = os.path.join(self.base_dir,self.edition_name)
        os.makedirs(folder_path, exist_ok=True)
        return folder_path

    async def download_pages(self):
        await self.extract_edition_name()
        folder_path = self.create_folder()

        options = await self.page.query_selector_all("#DropDownList1 > option")
        page_count = len(options)
        print(f"Found {page_count} pages to download...")

        for i in range(page_count):
            await self.page.select_option("#DropDownList1", str(i + 1))
            await self.page.wait_for_timeout(3000)

            pdf_link = await self.page.get_attribute("a.pdficon", "href")
            if pdf_link:
                formatted_date = datetime.strptime(self.date_str,"%Y-%m-%d").strftime(
                    "%Y_%m_%d")
                file_name = f"{self.edition_name}_{formatted_date}_{i + 1}.pdf"
                full_path = os.path.join(folder_path, file_name)
                print(f"Downloading page {i + 1}: {pdf_link}")
                urllib.request.urlretrieve(pdf_link, full_path)
            else:
                print(f"PDF not found on page {i + 1}")

    async def close(self):
        await self.browser.close()
        await self.playwright.stop()

    async def run(self):
        await self.setup()
        await self.select_today_date()
        await self.download_pages()
        await self.close()

# Main script runner
if __name__ == "__main__":
    downloader = StateTimesDownloader()
    asyncio.run(downloader.run())
