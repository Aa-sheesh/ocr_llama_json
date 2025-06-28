import logging
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, Page


class DishaCrawler:
    def __init__(self, base_url: str, output_dir: str = "downloads/disha"):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self._setup_logging()
        self._create_output_dir()

    def _setup_logging(self):
        """Setup logging configuration"""
        self.logger = logging.getLogger("DishaCrawler")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            )
            self.logger.addHandler(handler)

    def _create_output_dir(self):
        """Create output directory if it doesn't exist"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Output directory ready: {self.output_dir}")

    def _get_editions(self, page: Page) -> list:
        """Scrape all available editions from the homepage."""
        self.logger.info("Fetching available editions...")
        try:
            # Wait for the container holding the editions to load
            page.wait_for_selector("div.card-box", timeout=3000)

            # Select all edition cards
            edition_cards = page.query_selector_all("div.card-box a")

            # Extract name and URL for each edition
            editions = [
                {
                    "name": card.query_selector(
                        "div.name_of_card").inner_text().strip(),
                    "url": card.get_attribute("href")
                }
                for card in edition_cards if
                card.query_selector("div.name_of_card")
            ]

            self.logger.info(f"Found {len(editions)} editions.")
            return editions
        except Exception as e:
            self.logger.error(f"Error fetching editions: {e}")
            return []

    def _download_pages(self, page: Page, edition_name: str, paper_date: str):
        """Download pages for the given edition using screenshot method."""
        self.logger.info(f"Downloading pages for edition: {edition_name}")

        container_selector = "div#de-chunks-container"
        next_button_selector = "button.nextpage"
        total_pages_selector = "button#pagecount-btn"

        try:
            # Create directory for saving pages
            page_folder = self.output_dir / edition_name.lower()
            page_folder.mkdir(parents=True, exist_ok=True)

            # Get the total number of pages
            page.wait_for_selector(total_pages_selector, timeout=2000)
            total_pages_text = page.query_selector(
                total_pages_selector).inner_text().strip()
            total_pages = int(
                total_pages_text.split()[-1])  # Extract the total page count

            for current_page in range(1, total_pages + 1):
                # Wait for the container to load
                page.wait_for_selector(container_selector, timeout=2000)
                # Method 1: Try screenshot approach
                success = self._screenshot_method(page, page_folder,
                                                  paper_date, current_page)
                if not success:
                    self.logger.error(
                        f"All methods failed for page {current_page}")
                    break

                self.logger.info(f"Successfully saved page {current_page}")

                time.sleep(2)
                # Navigate to the next page if not the last page
                if current_page < total_pages:
                    next_button = page.query_selector(next_button_selector)
                    if not next_button:
                        self.logger.info(
                            f"No next button found at page {current_page}.")
                        break

                    # Click the next button and wait for the next page to load
                    next_button.click()

            self.logger.info(
                f"Finished downloading all pages for {edition_name}.")

        except Exception as e:
            self.logger.error(
                f"Error downloading pages for edition {edition_name}: {e}")

    def _screenshot_method(self, page: Page, page_folder, paper_date: str,
                           current_page: int) -> bool:
        """Take a screenshot of the page container, excluding pagination elements."""
        try:
            self.logger.info(
                f"Trying screenshot method for page {current_page}")

            # Method 1: Hide pagination elements before screenshot
            self._hide_pagination_elements(page)

            # Find the container
            container = page.query_selector("div#de-chunks-container")
            if not container:
                self.logger.error("Container not found for screenshot")
                return False

            page.set_viewport_size({"width": 800, "height": 1000})

            screenshot_bytes = container.screenshot()

            self._restore_pagination(page)
            # Save the screenshot
            image_path = page_folder / f"disha_{paper_date}_{current_page}.png"
            with open(image_path, "wb") as f:
                f.write(screenshot_bytes)

            self.logger.info(f"Screenshot saved: {image_path}")
            return True

        except Exception as e:
            self.logger.error(f"Screenshot method failed: {e}")
            return False

    def _hide_pagination_elements(self, page: Page):
        """Hide pagination and other UI elements before taking screenshot."""
        try:
            page.evaluate("""
                    // Store original display styles before hiding
                    window.hiddenElements = [];

                    const elementsToHide = [
                        'div#page-level-nav',
                        '.nav-group',
                        '.btn-group',
                        '.input-group'
                    ];

                    elementsToHide.forEach(selector => {
                        document.querySelectorAll(selector).forEach(el => {
                            // Only hide if not inside content container
                            if (!el.closest('#de-chunks-container')) {
                                window.hiddenElements.push({
                                    element: el,
                                    originalDisplay: el.style.display || 'block'
                                });
                                el.style.display = 'none';
                            }
                        });
                    });

                    console.log('Temporarily hid', window.hiddenElements.length, 'elements');
                """)

        except Exception as e:
            self.logger.warning(f"Failed to temporarily hide pagination: {e}")

    def _restore_pagination(self, page: Page):
        """Restore pagination elements to their original state."""
        try:
            page.evaluate("""
                if (window.hiddenElements) {
                    window.hiddenElements.forEach(item => {
                        item.element.style.display = item.originalDisplay;
                    });
                    window.hiddenElements = [];
                    console.log('Restored pagination elements');
                }
            """)

        except Exception as e:
            self.logger.warning(f"Failed to restore pagination: {e}")

    def _download_clips(self, page: Page, edition_name: str, paper_date: str):
        """Download all available clips for the given edition across all pages."""
        self.logger.info(f"Downloading clips for edition: {edition_name}")

        # Create directory for saving clips
        clip_folder = self.output_dir / edition_name
        clip_folder.mkdir(parents=True, exist_ok=True)

        try:

            page_number = 1
            clip_index = 1  # Sequential numbering for articles

            while True:
                self.logger.info(f"Processing clips on page {page_number}")

                clips_tab = page.query_selector(
                    "#left-panel-topclips a.tab-link")
                if not clips_tab:
                    self.logger.error("Clips tab not found")
                    return

                clips_tab.click()
                self.logger.info("Switched to Clips tab")
                time.sleep(2)  # Allow clips to load

                # Get all clip elements on the current page
                clip_elements = page.query_selector_all("#page-thumbs a")
                if not clip_elements:
                    self.logger.warning("No clips found on this page")
                    break  # No clips means probably no content here, stop

                num_clips = len(clip_elements)
                self.logger.info(
                    f"Found {num_clips} clips to download on page {page_number}")

                for i in range(num_clips):
                    try:
                        # Re-query clips fresh to avoid stale element errors
                        clip_elements = page.query_selector_all(
                            "#page-thumbs a")
                        clip = clip_elements[i]

                        clip.click()
                        self.logger.info(
                            f"Opened clip {i + 1}/{num_clips} on page {page_number}")
                        time.sleep(1)  # Allow modal to open

                        modal = page.wait_for_selector(
                            "div.enlarged.clipactions",
                            state="visible",
                            timeout=2000)
                        download_button = modal.query_selector(
                            "a.downloadclip")
                        if not download_button:
                            self.logger.error(
                                f"Download button not found for clip {i + 1} on page {page_number}")
                            self._close_modal(page)
                            continue

                        with page.expect_download() as download_info:
                            download_button.click()

                        download = download_info.value
                        save_path = clip_folder / (
                            f"disha_{paper_date}_{page_number}_article_"
                            f"{clip_index}.png")
                        download.save_as(save_path)
                        self.logger.info(f"Saved clip to: {save_path}")

                        self._close_modal(page)
                        self.logger.info(
                            "Closed modal after finishing clip download")
                        clip_index += 1

                    except Exception as e:
                        self.logger.error(
                            f"Error downloading clip {i + 1} on page {page_number}: {e}")
                        self._close_modal(page)

                # Check for the "next page" button
                next_button = page.query_selector(
                    "button.nextpage")  # update selector based on actual site
                if next_button and "disablebtn" not in next_button.get_attribute(
                        "class"):
                    self.logger.info(
                        f"Navigating to next page {page_number + 1}")
                    next_button.click()
                    time.sleep(2)  # wait for the page to load clips
                    page_number += 1
                else:
                    self.logger.info(
                        "No more pages left, finished downloading clips.")
                    break

        except Exception as e:
            self.logger.error(f"Error downloading clips: {e}")

    def _close_modal(self, page: Page):
        try:
            close_button = page.query_selector("#modal-close-btn")
            if close_button:
                close_button.click()
                self.logger.info("Clicked close button on modal")
            else:
                self.logger.info(
                    "Close button not found; modal might already be closed")
        except Exception as e:
            self.logger.warning(f"Couldn't close modal: {e}")

    def run(self):
        """Main crawler execution"""
        self.logger.info("Starting Disha e-paper crawler")

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
                    if edition["name"] in ["HYDERABAD TABLOID", "AP-MAIN"]:
                        try:
                            edition_name = edition["name"]
                            edition_url = edition["url"]
                            self.logger.info(
                                f"Processing edition: {edition_name}")
                            page.goto(edition_url)
                            time.sleep(2)
                            self._download_pages(page, edition_name,
                                                 paper_date)

                            page.goto(edition_url)
                            time.sleep(2)
                            self._download_clips(page, edition_name.lower,
                                                 paper_date)

                        except Exception as e:
                            self.logger.error(
                                f"Error processing edition {edition_name}: {e}")

            except Exception as e:
                self.logger.error(f"Critical error: {e}")

            finally:
                browser.close()


def main():
    base_url = "https://epaper.dishadaily.com/"
    crawler = DishaCrawler(base_url)
    crawler.run()


if __name__ == "__main__":
    main()
