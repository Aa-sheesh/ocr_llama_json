import os
import time
from datetime import datetime

from playwright.sync_api import sync_playwright


# same as NavBharatEpaperCrawler
class NavRashtraCrawler:
    def __init__(self):
        self.base_url = "https://epaper.navarashtra.com"
        self.newspaper_name = "nav_rashtra"

        self.output_dir =os.path.join("downloads",self.newspaper_name)
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"Output directory: {self.newspaper_name}")

    def create_folder(self, *paths):
        """Creates a folder hierarchy and returns the final path."""
        folder_path = os.path.join(self.newspaper_name, *paths)
        os.makedirs(folder_path, exist_ok=True)
        return folder_path

    def wait_and_get(self, page, selector, timeout=2000):
        """Waits for a selector to appear and returns the element."""
        try:
            return page.wait_for_selector(selector, timeout=timeout)
        except Exception as e:
            print(f"Failed to find selector {selector}: {e}")
            return None

    def download_clips(self, page, newspaper_name, page_num, date_str, edition_type):
        try:
            self.wait_and_get(
                page, ".carousel-item.active .parent-container", timeout=5000
            )
            article_containers = page.query_selector_all(
                ".carousel-item.active .epaper-article-container"
            )

            if not article_containers:
                print(f"No clips found on page {page_num}")
                return False

            print(f"Found {len(article_containers)} clips on page {page_num}")
            # clips_folder = self.create_folder(date_str, newspaper_name)
            clips_folder = os.path.join(self.output_dir, newspaper_name)

            for idx, container in enumerate(article_containers, 1):
                try:
                    overlay = container.query_selector(".overlay")
                    article_id = (
                        overlay.get_attribute("id") if overlay else f"clip_{idx}"
                    )

                    container.scroll_into_view_if_needed()
                    time.sleep(0.5)  # Allow stabilization
                    if not container.is_visible():
                        print(f"Clip {article_id} not visible, skipping.")
                        continue
                    clip_path = os.path.join(
                        clips_folder,
                        f"{newspaper_name}_{date_str}_page_{page_num}_article_{idx}.png",
                    )
                    container.screenshot(path=clip_path)
                    print(f"Saved clip {article_id} from page {page_num}")
                except Exception as e:
                    print(f"Error saving clip {idx} from page {page_num}: {e}")
            return True
        except Exception as e:
            print(f"Error downloading clips from page {page_num}: {e}")
            return False

    def download_page(self, page, newspaper_name, page_num, date_str, edition_type):
        try:
            # download_button = self.wait_and_get(
            #     page, '.epaper-header-actions img[src*="download.png"]'
            # )
            # if not download_button:
            #     print(f"Download button not found on page {page_num}")
            #     return False
            #
            # with page.expect_download() as download_info:
            #     download_button.click()
            #     download = download_info.value
            #     newspaper_folder = self.create_folder(
            #         date_str, edition_type, newspaper_name
            #     )
            #     download.save_as(os.path.join(newspaper_folder, f"Page_{page_num}.pdf"))
            #     print(f"Downloaded page {page_num} for {newspaper_name}")

            self.download_clips(page, newspaper_name, page_num, date_str, edition_type)
            return True
        except Exception as e:
            print(f"Error downloading page {page_num}: {e}")
            return False

    def process_newspaper_pages(self, page, newspaper_name, date_str, edition_type):
        successful_downloads = 0
        try:
            self.wait_and_get(page, ".pagination-primary", timeout=5000)

            while True:
                current_page = page.query_selector(".page-item.active .page-link")
                if not current_page:
                    break

                page_num = int(current_page.inner_text())
                if self.download_page(
                    page, newspaper_name, page_num, date_str, edition_type
                ):
                    successful_downloads += 1

                next_button = page.query_selector('button[aria-label="Next"]')
                if not next_button or next_button.is_disabled():
                    break

                next_button.click()
                time.sleep(1)
            return successful_downloads
        except Exception as e:
            print(f"Error processing pages: {e}")
            return successful_downloads

    def process_edition_tab(self, page, tab_name, date_str):
        successful_downloads = 0
        try:
            tab = self.wait_and_get(
                page, f'.nav-pills .nav-item .nav-link:text("{tab_name}")'
            )
            if tab:
                tab.click()
            else:
                print(f"Tab {tab_name} not found.")
                return 0

            self.wait_and_get(page, ".epaper-common-card-container", timeout=5000)
            cards = page.query_selector_all(".epaper-common-card-container")

            print(f"Found {len(cards)} newspapers in {tab_name}")
            for card in cards:
                name_el = card.query_selector(".header-text")
                newspaper_name ='_'.join((name_el.inner_text().strip().lower()).split()) if (
                    name_el) else "unknown"
                print(f"newspaper name: {newspaper_name}")
                img_link = card.query_selector(".card-header-image a")

                if not img_link:
                    print(f"No link for {newspaper_name}")
                    continue

                with page.context.expect_page() as new_page_info:
                    img_link.click()
                new_page = new_page_info.value

                downloads = self.process_newspaper_pages(
                    new_page, newspaper_name, date_str, tab_name
                )
                successful_downloads += downloads
                print(f"Processed {newspaper_name}: {downloads} pages downloaded.")
                new_page.close()
            return successful_downloads
        except Exception as e:
            print(f"Error processing tab {tab_name}: {e}")
            return 0

    def process_all_editions(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            try:
                page.goto(self.base_url)
                self.wait_and_get(
                    page, ".epaper-edition-list-main-container", timeout=5000
                )

                date_str = datetime.now().strftime("%Y_%m_%d")
                total_downloads = 0
                edition_tabs = ["Main Edition"]

                for tab_name in edition_tabs:
                    downloads = self.process_edition_tab(page, tab_name, date_str)
                    total_downloads += downloads
                    print(f"Completed {tab_name}: {downloads} pages downloaded.")

                print(f"Total pages downloaded: {total_downloads}")
                return True
            except Exception as e:
                print(f"Error in main process: {e}")
                return False
            finally:
                browser.close()


if __name__ == "__main__":
    crawler = NavRashtraCrawler()
    print("Starting newspaper download process...")
    success = crawler.process_all_editions()
    if success:
        print("Process completed successfully.")
    else:
        print("Process completed with errors.")
