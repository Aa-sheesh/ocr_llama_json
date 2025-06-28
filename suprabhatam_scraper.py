import logging
import time
from datetime import datetime
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright, Page


class SuprabhaathamCrawler:
    def __init__(self, base_url: str, output_dir: str =
    "downloads/suprabhaatham"):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self._setup_logging()
        self._create_output_dir()

    def _setup_logging(self):
        """Setup logging configuration"""
        self.logger = logging.getLogger("SuprabhaathamCrawler")
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

    def _get_editions(self, page: Page) -> list:
        """Scrape all available editions from the homepage."""
        self.logger.info("Fetching available editions...")
        try:
            page.wait_for_selector("div.Homescreen-itemBox2", timeout=2000)
            edition_links = page.query_selector_all("div.Homescreen-item")
            editions = [
                {
                    "name": item.query_selector(
                        "div.Homescreen-itemBox2").inner_text().strip().split(
                        " -")[0],

                }
                for item in edition_links
            ]
            self.logger.info(f"Found {len(editions)} editions.")
            return editions
        except Exception as e:
            self.logger.error(f"Error fetching editions: {e}")
            return []

    def _download_pages(self, page: Page, edition_name: str, paper_date: str):
        """Download all pages for a specific edition."""
        self.logger.info(f"Downloading pages for edition: {edition_name}")
        image_selector = "div.detailScreen-imageContainer img"
        next_button_selector = "div.detailScreen-headerBox2 > div:nth-child(3)"
        current_page_selector = "span.ant-select-selection-item"

        try:
            # Create directory for saving pages
            page_folder = self.output_dir  / edition_name.lower()
            page_folder.mkdir(parents=True, exist_ok=True)

            while True:
                # Wait for the image to load
                page.wait_for_selector(image_selector, timeout=2000)

                # Extract the image URL
                image_element = page.query_selector(image_selector)
                if not image_element:
                    self.logger.error("Image not found.")
                    break

                image_url = image_element.get_attribute("src")
                self.logger.info(f"Found image URL: {image_url}")

                # Download the image
                current_page = page.query_selector(
                    current_page_selector).inner_text().strip()
                image_path = page_folder / (f"suprabhatam_{paper_date}"
                                            f"_{current_page}.png")
                response = requests.get(image_url, stream=True)
                with open(image_path, "wb") as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
                self.logger.info(f"Saved page {current_page} to {image_path}")

                # Check if the next button exists and is clickable
                next_button = page.query_selector(next_button_selector)
                if not next_button:
                    self.logger.info(
                        "No next button found. Last page reached.")
                    break

                # Click the next button and wait for the next page to load
                next_button.click()
                time.sleep(2)  # Adjust sleep for page load timing

                # Verify if the current page has changed
                new_current_page = page.query_selector(
                    current_page_selector).inner_text().strip()
                if new_current_page == current_page:
                    self.logger.info(
                        "Pagination did not advance. Last page reached.")
                    break

        except Exception as e:
            self.logger.error(
                f"Error downloading pages for edition {edition_name}: {e}")

    def run(self):
        """Main crawler execution"""
        self.logger.info("Starting Suprabhaatham e-paper crawler")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            try:
                page.goto(self.base_url)
                time.sleep(2)

                paper_date = datetime.now().strftime('%Y-%m-%d')
                editions = self._get_editions(page)
                if not editions:
                    self.logger.warning("No editions found.")
                    return

                for edition in editions:
                    try:
                        edition_name = edition["name"]
                        edition_url = f"https://epaper.suprabhaatham.com/details/{edition_name}/{paper_date}/1"
                        self.logger.info(f"Processing edition: {edition_name}")
                        page.goto(edition_url)
                        time.sleep(2)
                        self._download_pages(page, edition_name, paper_date)
                    except Exception as e:
                        self.logger.error(
                            f"Error processing edition {edition_name}: {e}")

            except Exception as e:
                self.logger.error(f"Critical error: {e}")

            finally:
                browser.close()


def main():
    base_url = "https://epaper.suprabhaatham.com/"
    crawler = SuprabhaathamCrawler(base_url)
    crawler.run()


if __name__ == "__main__":
    main()
