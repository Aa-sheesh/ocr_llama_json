import asyncio
import os
from datetime import datetime
from pathlib import Path

from PIL import Image
from playwright.async_api import async_playwright



class VishwavaniEpaperDownloader:
    def __init__(self, playwright):
        self.playwright = playwright
        self.today = datetime.today()
        self.date_str = self.today.strftime("%Y-%m-%d")
        self.formatted_date = datetime.strptime(self.date_str,
                                            "%Y-%m-%d").strftime(
            "%Y_%m_%d")
        # Base directory: vishwavani_edition/YYYY-MM-DD
        self.root_dir = Path(os.path.join("downloads","vishwavani"))
        self.root_dir.mkdir(parents=True, exist_ok=True)

    async def download_vishwavani_epaper_with_edition(self):
        browser = await self.playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://epaper.vishwavani.news/", timeout=60000)
        await page.evaluate(
            f"document.querySelector('#datepicker')._flatpickr.setDate('{self.date_str}')"
        )

        editions = await page.query_selector_all('#select-main-edition option')
        edition_values = []
        for edition in editions:
            edition_value = await edition.get_attribute("value")
            edition_name = await edition.inner_text()
            edition_values.append((edition_value, edition_name.strip().lower()))

        print(f"Found {len(edition_values)} editions: {edition_values}")

        for edition_value, edition_name in edition_values:
            print(f"🔄 Switching to edition: {edition_name} (ID: {edition_value})")

            # Create edition-specific folder structure
            edition_base_dir = self.root_dir / edition_name
            # pages_dir = edition_base_dir / "Pages"
            # news_paper_dir = edition_base_dir / "News_Paper"

            # for directory in [pages_dir, news_paper_dir]:
            edition_base_dir.mkdir(parents=True, exist_ok=True)

            await page.select_option("#select-main-edition", value=edition_value)
            await page.wait_for_timeout(1000)

            image_paths = await self.download_pages(page,edition_base_dir,edition_name)

            # if image_paths:
            #     await self.create_pdf(edition_name, image_paths, edition_base_dir)

            print(f"📄 Finished downloading edition {edition_name}.")

        await browser.close()
        print("✅ All editions processed successfully!")

    async def navigate_to_next_page(self, page, current_page_num):
        """
        Navigates to the next page using the page number buttons.

        Args:
            page: The Playwright page object used for interacting with the web page.
            current_page_num: The current page number, used to find the next page button.

        Returns:
            True if navigation to the next page was successful, otherwise False.
        """
        pagination_buttons = await page.query_selector_all(
            "#container-page-numbers .page-numbers")
        for button in pagination_buttons:
            button_page_num = int(await button.get_attribute("data-id"))
            if button_page_num == current_page_num + 1:
                # Click the next page number button
                await button.click()
                await page.wait_for_timeout(3000)  # Wait for the page to load
                return True
        return False

    async def download_image(self, page, page_num, edition_pages_dir,
                             downloaded_pages,edition_name):
        """
        Downloads the image for a given page number.

        Args:
            page: The Playwright page object used for interacting with the web page.
            page_num: The page number to download.
            edition_pages_dir: The directory where the images for this edition are stored.
            downloaded_pages: A set that tracks which pages have already been downloaded.

        Returns:
            The path to the downloaded image if successful, otherwise None.
        """
        img = await page.wait_for_selector("#crop-target", timeout=5000)
        img_url = await img.get_attribute("src")

        if not img_url or page_num in downloaded_pages:
            return None

        # Download the image
        img_data = await page.context.request.get(img_url)
        img_bytes = await img_data.body()

        img_path = edition_pages_dir / (f"{edition_name}_{self.formatted_date}_page"
                                        f"_{page_num:02d}.png")
        img_path.write_bytes(img_bytes)
        downloaded_pages.add(page_num)  # Mark this page as downloaded
        print(f"✅ Downloaded page {page_num}")
        return img_path

    async def download_pages(self, page, edition_pages_dir,edition_name):
        page_num = 1
        image_paths = []
        downloaded_pages = set()

        while True:
            try:
                img_path = await self.download_image(page, page_num,
                                                     edition_pages_dir, downloaded_pages,edition_name)
                if not img_path:
                    break

                image_paths.append(img_path)

                if not await self.navigate_to_next_page(page, page_num):
                    break

                page_num += 1

            except Exception as e:
                print(f"⚠️ Error or last page reached at page {page_num}: {e}")
                break

        return image_paths

    async def create_pdf(self, edition_name, image_paths, news_paper_dir):
        try:
            print(f"📄 Converting images to PDF for edition: {edition_name}")
            images = [Image.open(str(p)).convert("RGB") for p in image_paths]

            pdf_filename = f"{edition_name}_{self.formatted_date}.pdf"
            pdf_path = news_paper_dir / pdf_filename

            images[0].save(pdf_path, save_all=True, append_images=images[1:])
            print(f"✅ PDF created: {pdf_path}")
        except Exception as e:
            print(f"❌ Error creating PDF for {edition_name}: {e}")


async def main():
    """
    Main entry point of the program. Initializes the Playwright instance and starts the
    downloading process of Vishwavani ePaper for all editions.

    Returns:
        None
    """
    async with async_playwright() as playwright:
        downloader = VishwavaniEpaperDownloader(playwright)
        await downloader.download_vishwavani_epaper_with_edition()


if __name__ == "__main__":
    asyncio.run(main())
