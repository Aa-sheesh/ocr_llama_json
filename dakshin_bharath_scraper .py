import asyncio
import os
from datetime import datetime

from playwright.async_api import async_playwright


class DakshinBharatEpaperDownloader:
    def __init__(self, base_url="https://epaper.dakshinbharat.com"):
        self.base_url = base_url
        self.base_dir = os.path.join("downloads", "dakshin_bharath")
        self.browser = None
        self.context = None
        self.page = None

    async def start_browser(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def close_browser(self):
        if self.browser:
            await self.browser.close()

    async def get_edition_links(self):
        await self.page.goto(self.base_url)
        await self.page.wait_for_load_state('domcontentloaded')

        edition_boxes = await self.page.locator("div.category-thumb-box").all()
        editions = []

        for box in edition_boxes:
            link = await box.locator(
                "a[href^='/epaper/default/open?id=']").first.get_attribute(
                "href")
            name = await box.locator(".category-title a").text_content()
            if link and name:
                full_url = self.base_url + link
                editions.append((name.strip(), full_url))

        return editions

    async def download_pdf(self, edition_name: str, edition_url: str):
        print(f"Navigating to {edition_name} edition...")
        await self.page.goto(edition_url)

        pdf_button = await self.page.wait_for_selector("a.btn-pdfdownload")
        pdf_url = await pdf_button.get_attribute("href")

        today_str = datetime.today().strftime("%Y-%m-%d")

        formatted_date = datetime.strptime(today_str, "%Y-%m-%d").strftime(
            "%Y_%m_%d")
        edition_dir = os.path.join(self.base_dir,edition_name)
        os.makedirs(edition_dir, exist_ok=True)

        pdf_filename = f"{edition_name}_{formatted_date}.pdf"
        pdf_path = os.path.join(edition_dir, pdf_filename)

        print(f"Downloading {edition_name} PDF from: {pdf_url}")

        response = await self.page.context.request.get(pdf_url)
        with open(pdf_path, "wb") as f:
            f.write(await response.body())

        print(f"Downloaded: {pdf_path}")

    async def process_page_articles(self, edition_name, page_url, page_number):
        print(f"📄 Finding articles on page: {page_url}")

        try:
            await self.page.wait_for_selector('#maparea', timeout=10000)
            article_areas = await self.page.locator(
                '#maparea a.areamapper-maparea').all()

            if not article_areas:
                print(f"⚠️ No articles found on page: {page_url}")
                return

            print(f"🔍 Found {len(article_areas)} articles on this page.")

            for i in range(len(article_areas)):
                article_number = i + 1
                try:
                    # Refresh locator each time because DOM may update after clicking
                    article_areas = await self.page.locator(
                        '#maparea a.areamapper-maparea').all()
                    article = article_areas[i]

                    print(f"📰 Opening article {i + 1}/{len(article_areas)}")
                    await article.click()

                    await self.page.wait_for_selector('#iframeDialog iframe',
                                                      state="attached",
                                                      timeout=10000)
                    iframe_element = await self.page.query_selector(
                        '#iframeDialog iframe')
                    iframe = await iframe_element.content_frame()

                    if iframe is None:
                        print("❌ Could not get iframe content frame")
                        return

                    await iframe.wait_for_selector('a.btn.btn-secondary',
                                                   timeout=10000)
                    download_href = await iframe.locator(
                        'a.btn.btn-secondary').get_attribute('href')

                    if download_href:
                        if download_href.startswith('/'):
                            download_url = self.base_url.rstrip(
                                '/') + download_href
                        else:
                            download_url = download_href

                        print(f"⬇️ Found clip URL: {download_url}")
                        await self.download_clip(edition_name, download_url,
                                                 page_number, article_number)
                    else:
                        print("⚠️ No download link found inside iframe")

                    await self.page.locator(
                        '#iframeDialog .btnCloseDialog').click()
                    await self.page.wait_for_timeout(500)

                except Exception as clip_error:
                    print(f"❌ Error processing article {article_number}: {clip_error}")

        except Exception as e:
            print(f"❌ Error loading article areas for {page_url}: {e}")

    async def process_all_pages(self, edition_name, edition_url):
        print(f"\n📖 Processing edition pages for: {edition_name}")

        await self.page.goto(edition_url)
        await self.page.wait_for_load_state('domcontentloaded')

        try:
            # Wait for thumbnails to load
            await self.page.wait_for_selector("a.epaper-thumb-link",
                                              timeout=10000)
            page_links = await self.page.locator("a.epaper-thumb-link").all()
            total_pages = len(page_links)
            print(f"🧾 Found {total_pages} pages in this edition.")

            for i in range(total_pages):
                page_number = i + 1
                try:
                    # Refresh locators because DOM might have changed
                    page_links = await self.page.locator(
                        "a.epaper-thumb-link").all()
                    page_element = page_links[i]
                    page_href = await page_element.get_attribute("href")

                    if page_href:
                        print(
                            f"\n➡️ Opening page {page_number}/{total_pages}: {page_href}")
                        await self.page.goto(page_href)
                        await self.page.wait_for_load_state('domcontentloaded')
                        await self.process_page_articles(edition_name,
                                                         page_href,
                                                         page_number)
                    else:
                        print(f"⚠️ No href found for page {page_number}")

                except Exception as page_error:
                    print(
                        f"❌ Error processing page {page_number}: {page_error}")

        except Exception as e:
            print(f"❌ Error fetching page links: {e}")

    async def download_clip(self, edition_name, clip_url, page_number,
                            article_number):
        print(
            f"🖼️ Downloading clip for {edition_name} page {page_number} article {article_number} from {clip_url}")

        today_str = datetime.today().strftime("%Y-%m-%d")
        formatted_date = datetime.strptime(today_str, "%Y-%m-%d").strftime(
            "%Y_%m_%d")
        edition_dir = os.path.join(self.base_dir, edition_name)
        os.makedirs(edition_dir, exist_ok=True)


        filename = (f"{edition_name}_{formatted_date}_page_{page_number}"
                    f"_article_{article_number}.png")
        save_path = os.path.join(edition_dir, filename)

        try:
            response = await self.page.context.request.get(clip_url)
            if response.status == 200:
                content = await response.body()
                with open(save_path, 'wb') as f:
                    f.write(content)
                print(f"✅ Clip saved: {save_path}")
            else:
                print(f"❌ Failed to download clip. Status: {response.status}")
        except Exception as e:
            print(f"❌ Error downloading clip: {e}")

    async def run(self):
        await self.start_browser()

        try:
            editions = await self.get_edition_links()
            for name, url in editions:
                name = "_".join(name.split()).lower()
                print(f"Starting edition: {name}")
                await self.download_pdf(name, url)
                await self.process_all_pages(name, url)
                print(f"Finished edition: {name}")

        finally:
            await self.close_browser()


if __name__ == "__main__":
    asyncio.run(DakshinBharatEpaperDownloader().run())
