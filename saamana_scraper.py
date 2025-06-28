import os
import time
from datetime import datetime

from playwright.sync_api import sync_playwright


class SaamanaEpaperScraper:
    def __init__(self,max_retries=3):
        self.base_dir = os.path.join("downloads", "saamana")
        self.today_date = datetime.now().strftime("%Y-%m-%d")
        self.today = datetime.strptime(self.today_date, "%Y-%m-%d").strftime(
            "%Y_%m_%d")
        self.max_retries = max_retries
        self.browser = None
        self.context = None
        self.page = None
        self.setup_directories()

    def setup_directories(self):
        """Create necessary directories for downloads"""
        os.makedirs(self.base_dir, exist_ok=True)

    def initialize_browser(self):
        """Initialize Playwright browser and context"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.context = self.browser.new_context()
        # Increase default timeouts
        self.context.set_default_timeout(30000)
        self.page = self.context.new_page()

    def close(self):
        """Clean up resources"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()

    def navigate_to_main_page(self):
        """Navigate to the Saamana ePaper homepage"""
        self.page.goto("https://epaper.saamana.com/")
        self.page.wait_for_selector(".epaper-header-center-date .header-text",
                                    timeout=15000)

    def get_editions(self):
        """Retrieve all available editions"""
        return self.page.query_selector_all("#myTabContent .col-md-4.col-lg-4")

    def wait_for_page_change(self, page, previous_page_number, timeout=10):
        """
        Waits for the page number OR image URL to change after clicking Next.
        Returns True if changed, False if not.
        """
        prev_page_text = ""
        prev_img_src = ""

        try:
            label = page.query_selector("div.pagination-text")
            if label:
                prev_page_text = label.inner_text().strip()
            image = page.query_selector("div.carousel-item.active img")
            if image:
                prev_img_src = image.get_attribute("src")
        except:
            pass

        for _ in range(timeout):
            try:
                # Check page text change
                label = page.query_selector("div.pagination-text")
                if label:
                    current_text = label.inner_text().strip()
                    if current_text != prev_page_text and str(
                            previous_page_number + 1) in current_text:
                        return True

                # Check image src change
                image = page.query_selector("div.carousel-item.active img")
                if image:
                    current_src = image.get_attribute("src")
                    if current_src and current_src != prev_img_src:
                        return True
            except:
                pass
            time.sleep(1)

        return False

    def process_edition(self, edition_name, edition_element):
        print(f"\nProcessing edition: {edition_name}")
        link = edition_element.query_selector("a")
        if not link:
            print("No clickable link in edition.")
            return

        edition_dir = os.path.join(self.base_dir, edition_name)
        os.makedirs(edition_dir, exist_ok=True)

        with self.context.expect_page() as new_page_info:
            link.click()
        edition_page = new_page_info.value
        # edition_page.wait_for_load_state("domcontentloaded")
        time.sleep(2)

        seen_pages = set()
        current_page = 1

        try:
            while True:
                page_label = edition_page.query_selector("div.pagination-text")
                current_page_text = page_label.inner_text().strip() if page_label else f"{current_page}"

                if current_page_text in seen_pages:
                    print("🔁 Detected page loop, stopping pagination.")
                    break
                seen_pages.add(current_page_text)

                self.download_page(edition_page, current_page, edition_name,
                                   edition_dir)

                next_btn = edition_page.query_selector(
                    "button[aria-label='Next']:not(:disabled)")
                if not next_btn:
                    print("✅ No more pages. Reached end of edition.")
                    break

                next_btn.click()
                if not self.wait_for_page_change(edition_page, current_page):
                    print(
                        "⚠️ Page did not change after clicking Next. Stopping.")
                    break

                current_page += 1
                time.sleep(1)

        finally:
            edition_page.close()

    def download_articles_on_page(self, page, page_number, edition_name,
                                  edition_dir):
        """Download article clips on a page with DOM stability handling"""

        # Get initial article count
        try:
            article_containers = page.query_selector_all(
                "div.carousel-item.active .epaper-article-container")
            num_articles = len(article_containers)
            print(f"Found {num_articles} articles on page {page_number}")
        except Exception as e:
            print(f"❌ Failed to query articles on page {page_number}: {e}")
            return 0

        if num_articles == 0:
            return 0

        clip_index = 1
        processed = 0
        max_attempts = 3

        while processed < num_articles:
            success = False
            for attempt in range(1, max_attempts + 1):
                try:
                    # Always get fresh references
                    articles = page.query_selector_all(
                        "div.carousel-item.active .epaper-article-container")
                    if not articles or len(articles) <= processed:
                        print(
                            f"⚠️ No articles found after {processed} processed. Waiting...")
                        time.sleep(2)
                        continue

                    current_article = articles[processed]

                    # Verify element stability
                    is_attached = page.evaluate("(el) => el.isConnected",
                                                current_article)
                    if not is_attached:
                        raise Exception("Element detached from DOM")

                    # Scroll and wait for article to stabilize
                    current_article.scroll_into_view_if_needed()
                    time.sleep(1)  # Allow rendering time after scroll

                    # Wait for overlay to be present and visible
                    overlay = current_article.wait_for_selector(
                        ".overlay",
                        state="visible",
                        timeout=5000
                    )

                    # Open article in new page context
                    with self.context.expect_page() as new_page_info:
                        overlay.click(force=True)
                    article_page = new_page_info.value

                    # Wait for article page to stabilize
                    # article_page.wait_for_load_state("networkidle")
                    time.sleep(1)  # Additional stabilization

                    # Download the clip
                    self.download_article_clip(article_page, page_number,
                                               edition_name, edition_dir,
                                               clip_index)

                    # Cleanup
                    article_page.close()
                    success = True
                    break  # Exit retry loop after success

                except Exception as e:
                    print(
                        f"⚠️ Attempt {attempt} failed for clip {clip_index}: {str(e)[:100]}")
                    if "detached" in str(e) or "not attached" in str(
                            e) or "not connected" in str(e):
                        print("🔄 DOM changed - refreshing element references")
                        time.sleep(1.5)
                        break  # Exit retry to refresh elements
                    time.sleep(1)

            if success:
                processed += 1
                clip_index += 1
            else:
                print(
                    f"❌ Permanent failure on article {processed + 1}/{num_articles}")
                clip_index += 1
                processed += 1  # Skip failed article

        return processed

    def download_article_clip(self, article_page, page_number, edition_name,
                              news_clip_dir, clip_index):
        """Download a single article clip with robust selectors"""
        for attempt in range(1, self.max_retries + 1):
            try:
                # Wait for critical elements to be ready
                article_page.wait_for_selector("body", state="attached")
                time.sleep(1)  # Additional stabilization

                download_btn = article_page.query_selector(
                    "div.epaper-header-actions img[src*='download.jpeg']"
                )

                with article_page.expect_download() as download_info:
                    download_btn.click()

                download = download_info.value
                clip_filename = (f"{edition_name}_{self.today}_page"
                                 f"_{page_number}_clip_"
                                 f"{clip_index}.png")
                clip_path = os.path.join(news_clip_dir, clip_filename)
                download.save_as(clip_path)
                print(f"📸 Article clip downloaded: {clip_path}")
                return  # Success, exit retry loop
            except Exception as e:
                print(
                    f"Error downloading article clip {clip_index} on page {page_number} (Attempt {attempt}): {e}"
                )
                if attempt == self.max_retries:
                    print(
                        f"❌ Failed to download article clip {clip_index} after {self.max_retries} attempts."
                    )
                else:
                    time.sleep(1)  # Small wait before retry

    def download_page(self, page, page_number, edition_name, edition_dir,
                      retries=3):
        """Download a full page PDF and associated articles"""
        for attempt in range(1, retries + 1):
            try:
                # Download PDF
                download_btn = page.wait_for_selector(
                    "div.epaper-header-actions.col img[src*='download.png']",
                    timeout=15000
                )

                if page.url.split("/")[-1] != str(page_number):
                    page.goto(
                        "/".join(page.url.split("/")[:-1:]) + "/" + str(
                            page_number))
                    page.wait_for_selector(
                        "div.epaper-header-actions.col img[src*='download.png']",
                        timeout=15000)

                with page.expect_download() as download_info:
                    download_btn.click()

                download = download_info.value
                filename = f"{edition_name}_{self.today}_page_{page_number}.pdf"
                filepath = os.path.join(edition_dir, filename)
                download.save_as(filepath)
                print(f"📄 PDF downloaded: {filepath}")

                # # Download article clips
                # num_articles = self.download_articles_on_page(
                #     page, page_number, edition_name, edition_dir)
                # print(
                #     f"Total articles downloaded on page {page_number}: {num_articles}")

                return  # Success if we reach here

            except Exception as e:
                print(
                    f"Error downloading page {page_number} (Attempt {attempt}): {e}")
                if attempt == retries:
                    print(
                        f"❌ Failed to download page {page_number} after {retries} attempts")
                else:
                    time.sleep(2)  # wait before retry

    def run(self):
        """Main method to execute the scraping process"""
        try:
            self.initialize_browser()
            self.navigate_to_main_page()

            editions = self.get_editions()
            print(f"\nTotal editions found: {len(editions)}")
            for i, edition in enumerate(editions):
                edition_name = edition.query_selector(
                    ".epaper-header-center-date .header-text").inner_text().strip().lower()

                edition_name = "_".join(edition_name.split())
                if edition_name.lower() == "mumbai":
                    try:
                        self.process_edition(edition_name, edition)
                        break
                    except Exception as e:
                        print(f"❌ Error processing Mumbai edition: {e}")
                else:
                    print("Not Mumbai. Skipping...")

            else:
                print("\n❗ Mumbai edition not found among available editions.")

            print("\n✅ Finished processing.")

        finally:
            self.close()


if __name__ == "__main__":
    scraper = SaamanaEpaperScraper()
    scraper.run()
