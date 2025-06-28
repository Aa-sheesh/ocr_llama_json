import os
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright


class HeraldEpaperScraper:
    def __init__(self, base_url: str, download_root: str = "herald"):
        self.base_url = base_url
        self.download_dir = os.path.join("downloads",download_root)
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.today_date = datetime.strptime(self.today, "%Y-%m-%d").strftime(
            "%Y_%m_%d")

    async def start(self):
        os.makedirs(self.download_dir, exist_ok=True)
        async with async_playwright() as p:
            self.browser = await p.chromium.launch(headless=True)
            self.context = await self.browser.new_context(accept_downloads=True)
            self.page = await self.context.new_page()

            await self.page.goto(self.base_url)
            await self.page.wait_for_selector('.content-title', timeout=60000)

            edition_names = await self._get_edition_names()

            for index, edition_name in enumerate(edition_names):
                print(f"\n>>> Processing edition: {edition_name}")
                await self._process_edition(index, edition_name)

            await self.browser.close()

    async def _get_edition_names(self):
        edition_elements = await self.page.query_selector_all('.thumBox')
        names = []

        for edition in edition_elements:
            name_el = await edition.query_selector("p")
            name = (await name_el.text_content()).strip().lower() if name_el else ""
            names.append(name)
            print(f"Found edition: {name}")
        return names

    async def _process_edition(self, index, edition_name):
        editions = await self.page.query_selector_all('.thumBox')
        await editions[index].click()

        for attempt in range(3):
            try:
                await self.page.wait_for_load_state('load', timeout=120000)
                break
            except TimeoutError:
                print(f"Retry {attempt + 1} for edition load failed...")
                await asyncio.sleep(5)

        await self.page.wait_for_selector('.pg_thumb_main_div', timeout=60000)
        thumb_panel = await self.page.query_selector('.col_sidebar.page_thumb_panel')
        thumbs = await thumb_panel.query_selector_all('.pg_thumb_main_div')

        for page_index, thumb in enumerate(thumbs):
            await self._download_full_page_and_clips(thumb, edition_name, page_index + 1)

        # Return to landing page
        home_button = await self.page.query_selector('#gotoLandingPageBtn')
        if home_button:
            await home_button.click()
            await self.page.reload()
            await asyncio.sleep(5)
        await self.page.wait_for_selector('.content-title', timeout=60000)
        await self.page.bring_to_front()
        await asyncio.sleep(2)

    async def _download_full_page_and_clips(self, thumb, edition_name, page_number):
        img = await thumb.query_selector('img')
        if not img:
            return

        await thumb.click()
        await asyncio.sleep(2)

        try:
            await self.page.wait_for_selector("#downloadpagetoolbar", timeout=60000)
            async with self.page.expect_download() as download_info:
                btn = await self.page.query_selector("#downloadpagetoolbar")
                if btn:
                    await btn.click()
            download = await download_info.value

            edition_dir = os.path.join(self.download_dir, edition_name)
            os.makedirs(edition_dir, exist_ok=True)

            filename = f"{edition_name.replace(' ', '_')}_{self.today_date}_page_{page_number}.pdf"
            file_path = os.path.join(edition_dir, filename)
            await download.save_as(file_path)
            print(f"Saved full page: {file_path}")

            # await self._get_article_clips(edition_name, page_number)

        except Exception as e:
            print(f"Error downloading page {page_number} of {edition_name}: {str(e)}")

    async def _get_article_clips(self, edition_name, page_number):
        await self.page.wait_for_selector('#ImageContainer', timeout=60000)
        articles = await self.page.query_selector_all('#ImageContainer .pagerectangle')
        print(f"Found {len(articles)} article clips.")

        for idx, article in enumerate(articles):
            print(f"Processing article {idx + 1}/{len(articles)}")
            try:
                await article.scroll_into_view_if_needed()

                await self.page.evaluate('''(element) => {
                    const mouseOverEvent = new MouseEvent('mouseover', {
                        view: window, bubbles: true, cancelable: true
                    });
                    element.dispatchEvent(mouseOverEvent);

                    const clickEvent = new MouseEvent('click', {
                        view: window, bubbles: true, cancelable: true
                    });
                    element.dispatchEvent(clickEvent);
                }''', article)

                await self.page.wait_for_load_state('load', timeout=60000)

                download_button = await self.page.wait_for_selector('#downloadImage', timeout=10000)
                if download_button:
                    await download_button.scroll_into_view_if_needed()
                    await download_button.evaluate('btn => btn.click()')

                    download = await self.page.wait_for_event('download')

                    clip_dir = os.path.join(self.download_dir, edition_name)
                    os.makedirs(clip_dir, exist_ok=True)

                    filename = (f"{edition_name.replace(' ', '_')}_"
                                f"{self.today_date}_page_"
                                f"{page_number}_clip{idx + 1}.png")
                    clip_path = os.path.join(clip_dir, filename)

                    await download.save_as(clip_path)
                    print(f"Saved article clip: {clip_path}")

            except Exception as e:
                print(f"Error processing article {idx + 1}: {str(e)}")


# ========== USAGE ==========
if __name__ == "__main__":
    url = "https://epaper.heraldgoa.in/"
    scraper = HeraldEpaperScraper(url)
    asyncio.run(scraper.start())
