"""
Multi Page PDF
"""
import asyncio
from datetime import datetime
from pathlib import Path

from aiohttp import ClientSession, ClientTimeout
from playwright.async_api import async_playwright


class JaiHindCrawler:
    def __init__(self):
        self.base_url_template = "https://jaihindnewspaper.com/e-paper/?date={date}&edition=general&filter="
        self.output_dir = Path("downloads/jai_hind/rajkot")
        self.today = datetime.now()

    async def get_dynamic_date_url(self):
        formatted_date = self.today.strftime("%d-%m-%Y")
        return self.base_url_template.format(
            date=formatted_date), formatted_date

    @staticmethod
    async def get_total_pages(page, url):
        pdf_requests = []

        def log_pdf_request(request):
            if request.url.endswith(".pdf"):
                print(f"[PDF DETECTED] {request.url}")
                pdf_requests.append(request.url)

        page.on("request", log_pdf_request)

        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.click("._df_book-cover")
            await page.wait_for_selector('label[for="df_book_page_number"]',
                                         timeout=30000)

            label = await page.query_selector(
                'div.df-ui-btn.df-ui-page label[for="df_book_page_number"]')
            if not label:
                print("[ERROR] Page number label not found.")
                return None
            label_text = await label.inner_text()
            _, total = label_text.strip().split('/')
            return int(total), pdf_requests
        except Exception as e:
            print(f"[ERROR] Could not extract total pages: {e}")
            return None, []

    @staticmethod
    def construct_pdf_url(date_str, page_number):
        formatted_url_date = datetime.strptime(date_str, "%d-%m-%Y").strftime(
            "%Y/%m")
        formatted_file_date = datetime.strptime(date_str, "%d-%m-%Y").strftime(
            "%d-%m-%Y")
        return f"https://jaihindnewspaper.com/wp-content/uploads/{formatted_url_date}/JAIHIND-E-PAPER-{formatted_file_date}-{page_number}-Page_compressed.pdf"

    async def download_pdf(self, url, output_path):
        timeout = ClientTimeout(total=60)
        async with ClientSession(timeout=timeout) as session:
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        print(
                            f"[ERROR] Failed to download PDF, status: {response.status}")
                        return False
                    content = await response.read()
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(content)
                    print(f"Downloaded: {output_path}")
                    return True
            except Exception as e:
                print(f"[ERROR] Exception during PDF download: {e}")
                return False

    async def run(self):
        url, date_str = await self.get_dynamic_date_url()
        print(f"Checking page: {url}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            total_pages, pdf_urls = await self.get_total_pages(page, url)
            await browser.close()

        if not total_pages:
            print("Failed to extract total pages.")
            return

        constructed_url = self.construct_pdf_url(date_str, total_pages)

        # If there's any .pdf from network and it differs from the constructed one, prefer the first match
        final_url = constructed_url
        if pdf_urls:
            if constructed_url not in pdf_urls:
                print(
                    "[INFO] Using network-detected PDF URL instead of constructed one.")
                final_url = pdf_urls[0]
            else:
                print("[INFO] Constructed PDF URL matches detected one.")

        print(f"Final PDF URL: {final_url}")
        formatted_date = self.today.strftime("%d_%m_%Y")
        output_filename = (
            f"jaihind_epapers_{formatted_date}.pdf")
        output_file = self.output_dir / output_filename
        await self.download_pdf(final_url, output_file)


if __name__ == "__main__":
    asyncio.run(JaiHindCrawler().run())
