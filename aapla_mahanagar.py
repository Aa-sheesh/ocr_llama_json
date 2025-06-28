import os
import time
from datetime import datetime

from playwright.sync_api import sync_playwright


class AaplaMahanagarEpaperCrawler:
    def __init__(self, base_url, output_dir="downloads/aapla_mahanagar"):
        self.base_url = base_url
        self.output_dir = output_dir
        self.newspaper_name = "Aapla Mahanagar"
        self.editions = []

        os.makedirs(self.output_dir, exist_ok=True)
        print(f"Output directory set: {self.output_dir}")

    def get_available_editions(self, page):
        try:
            page.wait_for_selector('.epaper-common-card-container',
                                   timeout=3000)
            cards = page.query_selector_all('.epaper-common-card-container')

            editions = []
            latest_date = None
            for card in cards:
                try:
                    edition_name = card.query_selector(
                        '.header-text').inner_text().strip()
                    edition_date = card.query_selector(
                        '.epaper-date-span').inner_text().strip()

                    date_obj = datetime.strptime(edition_date, '%d-%m-%Y')
                    latest_date = max(latest_date,
                                      date_obj) if latest_date else date_obj

                    editions.append({
                        'name': edition_name,
                        'date': edition_date,
                        'date_obj': date_obj,
                        'card': card
                    })
                except Exception as e:
                    print(f"Error parsing edition card: {e}")

            latest_editions = [e for e in editions if
                               e['date_obj'] == latest_date]
            print(
                f"Found {len(latest_editions)} editions for {latest_date.strftime('%d-%m-%Y')}")
            return latest_editions
        except Exception as e:
            print(f"Error fetching editions: {e}")
            return []

    def create_edition_folder(self, edition_name):
        try:
            edition_folder = os.path.join(self.output_dir, edition_name.lower())
            os.makedirs(edition_folder, exist_ok=True)
            return edition_folder
        except Exception as e:
            print(f"Error creating folder: {e}")
            return None

    def download_clips(self, page, page_num, date_str, edition_name):
        try:
            date_obj = datetime.strptime(date_str, '%d-%m-%Y')
            formatted_date = date_obj.strftime('%Y-%m-%d')

            parent_container = page.query_selector(
                '.carousel-item.active .parent-container')
            if not parent_container:
                print(f"No clips found on page {page_num}")
                return False

            article_containers = parent_container.query_selector_all(
                '.epaper-article-container')
            print(f"Found {len(article_containers)} clips on page {page_num}")

            for idx, container in enumerate(article_containers, 1):
                try:
                    article_id = container.query_selector(
                        '.overlay').get_attribute('id') or f"clip_{idx}"
                    clip_path = os.path.join(
                        self.create_edition_folder( edition_name),
                        f"aapla_mahanagar_{formatted_date}_{page_num}_article_{idx}.png")
                    container.screenshot(path=clip_path)
                    print(f"Saved clip {article_id} from page {page_num}")
                except Exception as e:
                    print(f"Error saving clip {idx} on page {page_num}: {e}")
            return True
        except Exception as e:
            print(f"Error downloading clips: {e}")
            return False

    def download_page(self, page, page_num, date_str, edition_name):
        try:
            date_obj = datetime.strptime(date_str, '%d-%m-%Y')
            formatted_date = date_obj.strftime('%Y-%m-%d')

            download_button = page.wait_for_selector(
                '.epaper-header-actions img[src*="download.png"]')
            with page.expect_download() as download_info:
                download_button.click()
                download = download_info.value
                file_path = os.path.join(
                    self.create_edition_folder(edition_name),
                    f"aapla_mahanagar_{formatted_date}_{page_num}.pdf")
                download.save_as(file_path)
                print(f"Downloaded page {page_num} for {edition_name}")
                self.download_clips(page, page_num, date_str, edition_name)
            return True
        except Exception as e:
            print(f"Error downloading page {page_num}: {e}")
            return False

    def process_newspaper_pages(self, page, date_str, edition_name):
        successful_downloads = 0
        try:
            page.wait_for_selector('.pagination', timeout=2000)
            while True:
                current_page = page.query_selector(
                    '.active.page-item').inner_text()
                if self.download_page(page, int(current_page), date_str,
                                      edition_name):
                    successful_downloads += 1
                next_button = page.query_selector('button[aria-label="Next"]')
                if not next_button or not next_button.is_enabled():
                    break
                next_button.click()
                time.sleep(1)
            return successful_downloads
        except Exception as e:
            print(f"Error processing pages: {e}")
            return successful_downloads

    def process_edition(self, page, edition_info):
        try:
            edition_name = edition_info['name']
            edition_date = edition_info['date']
            print(f"Processing edition: {edition_name} ({edition_date})")

            link = edition_info['card'].query_selector('.card-header-image a')
            with page.context.expect_page() as new_page_info:
                link.click()
            edition_page = new_page_info.value

            pages_downloaded = self.process_newspaper_pages(edition_page,
                                                            edition_date,
                                                            edition_name)
            edition_page.close()
            return pages_downloaded
        except Exception as e:
            print(f"Error processing edition {edition_info['name']}: {e}")
            return 0

    def process_all_editions(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080})
            page = context.new_page()

            try:
                page.goto(self.base_url)
                self.editions = self.get_available_editions(page)

                if not self.editions:
                    print("No editions found!")
                    return False

                total_downloads = sum(
                    self.process_edition(page, edition) for edition in
                    self.editions)
                print(f"Total pages downloaded: {total_downloads}")
                return True
            except Exception as e:
                print(f"Error in main process: {e}")
                return False
            finally:
                browser.close()


def main():
    base_url = "https://epaper.mymahanagar.com/"
    crawler = AaplaMahanagarEpaperCrawler(base_url)

    print("Starting Aapla Mahanagar download process...")
    success = crawler.process_all_editions()

    if success:
        print("Process completed successfully.")
    else:
        print("Process completed with errors.")


if __name__ == "__main__":
    main()
