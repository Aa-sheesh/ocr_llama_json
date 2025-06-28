import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from playwright.sync_api import sync_playwright, Page


class NavakalCrawler:
    def __init__(self, base_url: str, output_dir: str = "downloads/navakal"):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self._setup_logging()
        self._create_output_dir()

    def _setup_logging(self):
        """Setup logging configuration"""
        self.logger = logging.getLogger("NavakalCrawler")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)

    def _create_output_dir(self):
        """Create output directory if it doesn't exist"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Output directory ready: {self.output_dir}")

    def _create_edition_folder(self, edition_name: str) -> Path:
        """Create folder structure for an edition"""
        edition_folder = self.output_dir / edition_name.lower()
        edition_folder.mkdir(parents=True, exist_ok=True)
        return edition_folder

    def _extract_edition_info(self, page: Page) -> List[Dict[str, str]]:
        """Extract editions from the main page"""
        self.logger.info("Extracting editions...")
        # Locate all the edition cards on the page
        cards = page.query_selector_all('div.epaper-common-card-container')
        editions = []

        for card in cards:
            # Extract the name of the edition
            name_span = card.query_selector('span.header-text')
            name = name_span.inner_text().strip() if name_span else None

            # Extract the URL or image source related to the edition
            img_tag = card.query_selector('a img.img')
            img_src = img_tag.get_attribute('src') if img_tag else None

            if name and img_src:
                # Derive the edition URL from the image source
                match = re.search(
                    r"/News/(\w+)/(\w+)/(\d{4}/\d{2}/\d{2})/Thumbnails/(\d+)_",
                    img_src
                )

                if match:
                    edition_code, city_code, date_part, unique_id = match.groups()
                    formatted_date = date_part.replace("/", "")
                    url = (
                        f"http://epaper.navakal.in/edition/"
                        f"{name}/{edition_code}_{city_code}"
                        f"/{edition_code}_{city_code}_{formatted_date}/page/1"
                    )
                    editions.append({'name': name, 'url': url})

        self.logger.info(f"Found {len(editions)} editions.")
        return editions

    def _download_pdf(self, page: Page, page_number: int,
                      edition_folder: Path,date_str) -> bool:
        """Download page PDF"""
        try:
            date_obj = datetime.strptime(date_str, '%d-%m-%Y')
            formatted_date = date_obj.strftime('%Y-%m-%d')

            self.logger.info(f"Downloading PDF for page {page_number}...")

            # Locate the image element for download icon
            download_img = page.query_selector(
                'div.epaper-header-actions img[src*="download.png"]')

            if not download_img:
                self.logger.warning(
                    f"Download icon not found for page {page_number}")
                return False

            parent_div = download_img.evaluate_handle(
                'node => node.parentElement')

            with page.expect_download() as download_info:
                try:
                    download_img.click()
                except Exception as e:
                    parent_div.as_element().click()

            download = download_info.value
            save_path = edition_folder / (f"navakal_{formatted_date}"
                                          f"_{page_number}.png")
            download.save_as(str(save_path))
            self.logger.info(f"Page {page_number} PDF saved: {save_path}")
            return True

        except Exception as e:
            self.logger.error(
                f"Error downloading PDF for page {page_number}: {e}")
            return False

    def _download_clips(self, page: Page, page_number: int,
                        edition_folder: Path,date_str) -> int:
        """Download clips for a specific page"""
        date_obj = datetime.strptime(date_str, '%d-%m-%Y')
        formatted_date = date_obj.strftime('%Y-%m-%d')

        clips_downloaded = 0

        try:
            page_container = page.query_selector('div.carousel-item.active')
            if not page_container:
                self.logger.warning(
                    f"No active page container found for page {page_number}")
                return 0

            clip_overlays = page_container.query_selector_all('div.overlay')
            if not clip_overlays:
                self.logger.warning(
                    f"No clip overlays found for page {page_number}")
                return 0

            self.logger.info(
                f"Found {len(clip_overlays)} clips for page {page_number}")

            for idx, overlay in enumerate(clip_overlays, start=1):
                try:

                    # Expect a new page to open after clicking the overlay
                    with page.context.expect_page() as new_page_info:
                        overlay.click(force=True)

                    new_page = new_page_info.value  # Fetch the new page
                    new_page.wait_for_load_state('load')
                    time.sleep(1)

                    # Locate the download button
                    download_button = new_page.query_selector(
                        'div.epaper-header-actions img[src*="download.jpeg"]'
                    )

                    time.sleep(1)

                    if download_button:
                        with new_page.expect_download() as download_info:
                            download_button.click()
                        download = download_info.value
                        clip_path = edition_folder / (f"navakal"
                                                      f"_{formatted_date}_{page_number}_article_{idx}.png")
                        download.save_as(clip_path)
                        self.logger.info(
                            f"Downloaded clip {idx} for page {page_number}")
                        clips_downloaded += 1
                    else:
                        self.logger.warning(
                            f"No download button found for clip {idx} on page {page_number}")

                    new_page.close()

                except Exception as e:
                    self.logger.error(
                        f"Error downloading clip {idx} for page {page_number}: {e}")

        except Exception as e:
            self.logger.error(
                f"Error downloading clips for page {page_number}: {e}")

        return clips_downloaded

    def _process_pages(self, page: Page, edition_folder: Path, url,date_str):
        """Process pages in the edition"""

        # Select all page number buttons inside the pagination nav,
        # ignoring Previous, Next, and disabled dots
        buttons = page.query_selector_all('nav.pagination button.page-link')

        time.sleep(2)
        # Filter buttons that have numeric text (actual page numbers)
        page_numbers = []
        for btn in buttons:
            text = btn.inner_text().strip()
            if text.isdigit():
                page_numbers.append(int(text))

        if not page_numbers:
            self.logger.warning("No page numbers found in pagination.")
            return

        total_pages = max(page_numbers)
        self.logger.info(f"Total pages detected: {total_pages}")

        for page_number in range(1, total_pages + 1):
            page_url = f"{url}/{page_number}"  # Append the page number for other pages
            # Navigate to the page URL, e.g., /page/1, /page/2, etc.
            page.goto(page_url)
            time.sleep(1)
            pdf_success = self._download_pdf(page, page_number,
                                             edition_folder,date_str)
            clips_count = self._download_clips(page, page_number,
                                               edition_folder,date_str)

            self.logger.info(
                f"Page {page_number}: PDF {'downloaded' if pdf_success else 'not downloaded'}, {clips_count} clips"
            )

    def run(self):
        """Main crawler execution"""
        self.logger.info("Starting Navakal e-paper crawler")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()

            try:
                page.goto(self.base_url)
                time.sleep(2)

                date_str = datetime.now().strftime('%d-%m-%Y')
                editions = self._extract_edition_info(page)

                for edition in editions:
                    edition_name = edition['name']
                    self.logger.info(f"Processing edition: {edition_name}")
                    page.goto(edition['url'])
                    url = re.sub(r'/1$', '', edition['url'])
                    edition_folder = self._create_edition_folder(
                                                                 edition_name)
                    time.sleep(2)
                    self._process_pages(page, edition_folder, url,date_str)

                self.logger.info("Crawler completed successfully")

            except Exception as e:
                self.logger.error(f"Critical error: {e}")

            finally:
                browser.close()


def main():
    base_url = "http://epaper.navakal.in/"
    crawler = NavakalCrawler(base_url)
    crawler.run()


if __name__ == "__main__":
    main()
