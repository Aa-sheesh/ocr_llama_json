import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from playwright.sync_api import sync_playwright, Page


class SamyuktaKarnatakaCrawler:
    def __init__(self, base_url: str, output_dir: str = "downloads/samyukta_karnataka"):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self._setup_logging()
        self._create_output_dir()

    def _setup_logging(self):
        """Setup logging configuration"""
        self.logger = logging.getLogger("SamyuktaKarnatakaCrawler")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:  # Avoid duplicate handlers
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)

    def _create_output_dir(self):
        """Create output directory if it doesn't exist"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Output directory ready: {self.output_dir}")

    def _create_edition_folder(self,
                               edition_name: str) -> Path:
        """Create folder structure for edition"""

        edition_name_clean = edition_name.replace('/', '-').strip()
        edition_folder = self.output_dir  / edition_name_clean.lower()

        edition_folder.mkdir(parents=True, exist_ok=True)
        return edition_folder

    def _extract_edition_info(self, card) -> Tuple[str, str]:
        """Extract name and URL from edition card"""
        name_span = card.query_selector('span.header-text')
        name = name_span.inner_text().strip() if name_span else None

        img_tag = card.query_selector('a img.img')
        img_src = img_tag.get_attribute('src') if img_tag else None

        if not (name and img_src):
            return None, None

        # Extract required parts from the img src
        match = re.search(
            r"/News/(\w+)/(\w+)/(\d{4}/\d{2}/\d{2})/Thumbnails/(\d+)_",
            img_src)

        if not match:
            return name, None

        edition_code, city_code, date_part, unique_id = match.groups()
        formatted_date = date_part.replace("/", "")
        url = (
            f"https://epaper.samyukthakarnataka.com/edition/"
            f"{name}/{edition_code}_{city_code}"
            f"/{edition_code}_{city_code}_{formatted_date}/page/1"
        )

        return name, url

    def _get_editions_by_type(self, page: Page, edition_type: str) -> List[
        Dict]:
        """Get editions by type (Main Edition or Sub Edition)"""
        editions = []
        heading_selector = f'div.sc-fsYfdN span:text("{edition_type}")'
        heading = page.query_selector(heading_selector)

        if not heading:
            return editions

        container = heading.evaluate_handle(
            "el => el.closest('div.epaper-edition-content')")
        if not container:
            return editions

        cards = container.query_selector_all(
            'div.epaper-common-card-container')

        for card in cards:
            name, url = self._extract_edition_info(card)
            if name and url:
                editions.append({'name': name, 'url': url})

        return editions

    def get_editions(self, page: Page) -> Dict[str, List[Dict]]:
        """Extract all editions organized by type"""
        self.logger.info("Extracting editions...")

        main_editions = self._get_editions_by_type(page, "Main Edition")
        sub_editions = self._get_editions_by_type(page, "Sub Edition")

        self.logger.info(
            f"Found {len(main_editions)} main editions and {len(sub_editions)} sub editions")

        return {
            'main': main_editions,
            'sub': sub_editions
        }

    def get_total_pages(self, page: Page) -> int:
        """Determine total pages from pagination"""
        try:
            buttons = page.query_selector_all(
                'nav.pagination-primary ul.pagination-primary > li.page-item > button.page-link')

            page_numbers = [
                int(btn.inner_text().strip())
                for btn in buttons
                if btn.inner_text().strip().isdigit()
            ]

            if page_numbers:
                total_pages = max(page_numbers)
                self.logger.info(f"Total pages detected: {total_pages}")
                return total_pages

        except Exception as e:
            self.logger.error(f"Error determining total pages: {e}")

        return 1

    def download_pdf(self, page: Page, page_number: int,
                     edition_folder: Path, date_str) -> bool:
        """Download PDF for a specific page"""
        try:
            date_obj = datetime.strptime(date_str, '%B %d, %Y')
            formatted_date = date_obj.strftime('%Y-%m-%d')

            self.logger.info(f"Downloading PDF for page {page_number}...")

            download_icon = page.query_selector(
                'div.epaper-header-actions img[src*="download.png"]')
            if not download_icon:
                self.logger.warning(
                    f"Download icon not found on page {page_number}")
                return False

            with page.expect_download() as download_info:
                download_icon.click()

            download = download_info.value
            save_path = edition_folder / (f"samyukta_karnataka"
                                          f"_{formatted_date}"
                                          f"_{page_number}.pdf")
            download.save_as(str(save_path))

            self.logger.info(f"Page {page_number} PDF saved: {save_path}")
            return True


        except Exception as e:
            self.logger.error(
                f"Error downloading PDF for page {page_number}: {e}")
            return False

    def download_clips(self, page: Page, page_number: int,
                       edition_folder: Path, date_str) -> int:
        """Download all clips for a specific page"""
        date_obj = datetime.strptime(date_str, '%B %d, %Y')
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
                    # Handle blocking element
                    blocking_element = page.query_selector(
                        'ol.carousel-indicators')
                    if blocking_element:
                        page.evaluate(
                            '(element) => element.style.pointerEvents = "none"',
                            blocking_element)

                    # Scroll to overlay and ensure it is visible
                    page.evaluate(
                        '(element) => element.scrollIntoViewIfNeeded()',
                        overlay)
                    overlay.wait_for_element_state('visible')

                    # Expect a new page to open after clicking the overlay
                    with page.context.expect_page() as new_page_info:
                        overlay.click()

                    new_page = new_page_info.value  # Fetch the new page
                    new_page.wait_for_load_state('load')
                    time.sleep(1)

                    if blocking_element:
                        page.evaluate(
                            '(element) => element.style.pointerEvents = "auto"',
                            blocking_element)

                    # Locate the download button
                    download_button = new_page.query_selector(
                        'div.epaper-header-actions img[src*="download.jpeg"]'
                    )

                    time.sleep(1)

                    if download_button:
                        with new_page.expect_download() as download_info:
                            download_button.click()
                        download = download_info.value
                        clip_path = edition_folder / (
                            f"samyukta_karnataka_{formatted_date}"
                            f"_{page_number}_article_{idx}.png")
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

    def extract_date(self, page: Page) -> str:
        """Extract date from date picker input"""
        try:
            date_input = page.query_selector(
                'div.rdt.epapper-date-picker input.form-control')
            if date_input:
                raw_date = date_input.get_attribute(
                    'value')  # e.g., "27-05-2025"
                if raw_date:
                    date_obj = datetime.strptime(raw_date, '%d-%m-%Y')
                    return date_obj.strftime('%B %d, %Y')

            self.logger.warning("Date input not found, using current date")
            return datetime.now().strftime('%B %d, %Y')

        except Exception as e:
            self.logger.error(f"Error extracting date: {e}")
            return datetime.now().strftime('%B %d, %Y')

    def _navigate_to_page(self, page: Page, page_number: int) -> bool:
        """Navigate to a specific page number"""
        try:
            if page_number == 1:
                return True

            # Use URL-based navigation (most reliable for this site)
            current_url = page.url
            new_url = re.sub(r'/page/\d+', f'/page/{page_number}', current_url)

            self.logger.info(
                f"Navigating to page {page_number}: {new_url}")
            page.goto(new_url)
            time.sleep(1)
            self.logger.info(
                f"Successfully navigated to page {page_number}")
            return True

        except Exception as e:
            self.logger.error(f"Error navigating to page {page_number}: {e}")
            return False

    def _process_edition_pages(self, date_str, page: Page,
                               edition_folder: Path,
                               download_clips: bool = True) -> \
            None:
        """Process all pages for an edition"""
        total_pages = self.get_total_pages(page)

        for page_number in range(1, total_pages + 1):
            # Navigate to the specific page first
            if not self._navigate_to_page(page, page_number):
                self.logger.warning(
                    f"Skipping page {page_number} - navigation failed")
                continue

            pdf_success = self.download_pdf(page, page_number,
                                            edition_folder, date_str)
            clips_count = 0

            if download_clips:
                clips_count = self.download_clips(page, page_number,
                                                  edition_folder, date_str)

            if pdf_success:
                self.logger.info(
                    f"Page {page_number}: PDF downloaded with {clips_count} clips")
            else:
                self.logger.warning(f"Page {page_number}: PDF download failed")

    def _process_editions(self, page: Page, editions: List[Dict],
                          edition_type: str,
                          date_str: str, download_clips: bool = True) -> None:
        """Process a list of editions"""
        for edition in editions:
            edition_name = edition['name']
            self.logger.info(
                f"Processing {edition_type.lower()} edition: {edition_name}")

            page.goto(edition['url'])
            time.sleep(2)

            edition_folder = self._create_edition_folder(
                                                         edition_name)
            self._process_edition_pages(date_str, page, edition_folder,
                                        download_clips)

    def run(self):
        """Main crawler execution"""
        self.logger.info("Starting Samyukta Karnataka e-paper crawler")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()

            try:
                page.goto(self.base_url)
                time.sleep(2)

                date_str = self.extract_date(page)
                editions = self.get_editions(page)

                if not editions['main'] and not editions['sub']:
                    self.logger.error("No editions found, exiting...")
                    return

                # Process main editions (with clips)
                self._process_editions(page, editions['main'], "Main Edition",
                                       date_str, True)

                # Process sub editions (without clips as per original code)
                self._process_editions(page, editions['sub'], "Sub Edition",
                                       date_str, False)

                self.logger.info("Crawler completed successfully")

            except Exception as e:
                self.logger.error(f"Critical error: {e}")

            finally:
                browser.close()


def main():
    base_url = "https://epaper.samyukthakarnataka.com/"
    crawler = SamyuktaKarnatakaCrawler(base_url)
    crawler.run()


if __name__ == "__main__":
    main()
