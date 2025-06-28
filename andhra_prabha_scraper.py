import os
import time
from datetime import datetime

from playwright.sync_api import sync_playwright


class AndhraPrabhaEpaperCrawler:
    def __init__(self, base_url, output_dir="downloads/andhra_prabha"):
        self.base_url = base_url
        self.output_dir = output_dir
        self.newspaper_name = "Andhra Prabha"
        self.editions = []

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"Created output directory: {self.output_dir}")

    def get_available_editions(self, page) -> list:
        """Dynamically fetch available editions from the webpage"""
        editions = []
        try:
            page.wait_for_selector('#allOrgData', timeout=2000)
            current_date = datetime.now().strftime('%d/%m/%Y')
            print(f"Getting editions for current date: {current_date}")

            sections = page.query_selector_all('.productlist')
            for section in sections:
                items = section.query_selector_all('.item')
                for item in items:
                    try:
                        name_el = item.query_selector('p')
                        img_el = item.query_selector('img.lozad')

                        if not name_el or not img_el:
                            continue

                        edition_name = name_el.inner_text().strip()
                        edition_date = img_el.get_attribute('eddate')

                        if edition_date != current_date:
                            continue

                        ed_id = img_el.get_attribute('edid')
                        se_no = img_el.get_attribute('seno')

                        editions.append({
                            'name': edition_name,
                            'date': edition_date,
                            'edid': ed_id,
                            'seno': se_no,
                            'element': item
                        })
                    except Exception as e:
                        print(f"Error processing edition item: {str(e)}")
                        continue

            print(
                f"Found {len(editions)} editions for current date {current_date}:")
            for edition in editions:
                print(
                    f"- {edition['name']} ({edition['date']}) [ID: {edition['edid']}]")
            return editions

        except Exception as e:
            print(f"Error getting available editions: {str(e)}")
            return []

    def create_edition_folder(self, edition_name: str) -> str:

        os.makedirs(self.output_dir, exist_ok=True)

        edition_name = edition_name.replace('/', '-').strip()
        edition_folder = os.path.join(self.output_dir, edition_name.lower())
        os.makedirs(edition_folder, exist_ok=True)

        return edition_folder

    def download_page(self, page, page_num: int, date_str: str,
                      edition_name: str) -> bool:
        try:
            date_obj = datetime.strptime(date_str, '%d/%m/%Y')
            formatted_date = date_obj.strftime('%Y-%m-%d')

            download_button = page.wait_for_selector('#pg_download',
                                                     timeout=2000)
            download_span = page.wait_for_selector('#downloadpagetoolbar',
                                                   timeout=2000)

            with page.expect_download() as download_info:
                download_span.click()
                download = download_info.value
                edition_folder = self.create_edition_folder(
                                                            edition_name)
                download.save_as(os.path.join(edition_folder,
                                              f"andhra_prabha_{formatted_date}"
                                              f"_{page_num}.pdf"))
                print(f"Downloaded page {page_num} for {edition_name} edition")
                return True

        except Exception as e:
            print(
                f"Error downloading page {page_num} for {edition_name}: {str(e)}")
            return False

    def process_newspaper_pages(self, page, date_str: str, edition_name: str,
                                ) -> int:
        try:
            successful_downloads = 0
            page.wait_for_selector('#ddl_Pages', timeout=2000)

            options = page.eval_on_selector_all('#ddl_Pages option', '''(options) => {
                return options.map(option => ({
                    value: option.value,
                    pageNum: option.textContent.split(':')[0]
                }));
            }''')


            total_pages = len(options)
            print(f"Found {total_pages} pages for {edition_name}")

            for option in options:
                try:
                    page.select_option('#ddl_Pages', option['value'])
                    time.sleep(2)
                    page_num = int(option['pageNum'])

                    print(
                        f"Processing page {page_num} of {total_pages} for {edition_name}")
                    if self.download_page(page, page_num, date_str,
                                          edition_name):
                        successful_downloads += 1
                        time.sleep(2)

                except Exception as e:
                    print(
                        f"Error processing page {option['pageNum']}: {str(e)}")
                    continue

            return successful_downloads

        except Exception as e:
            print(f"Error processing pages for {edition_name}: {str(e)}")
            return 0

    def process_edition(self, page, edition_info: dict) -> int:
        try:
            edition_name = edition_info['name']
            edition_date = edition_info['date']
            edition_id = edition_info['edid']
            print(
                f"\nProcessing {edition_name} edition for date {edition_date}...")

            try:
                page.click(f'img[edid="{edition_id}"]')
            except Exception as e:
                page.evaluate(
                    f'document.querySelector("img[edid=\"{edition_id}\"]").click()')

            time.sleep(3)
            if not self.handle_popup(page):
                print(f"Warning: No popup handled for {edition_name}")

            time.sleep(3)
            page.wait_for_selector('.nav_action_bar', timeout=2000)
            pages_downloaded = self.process_newspaper_pages(page, edition_date,
                                                            edition_name,
                                                            )
            print(
                f"Downloaded {pages_downloaded} pages for {edition_name} edition")

            page.go_back()
            time.sleep(3)

            return pages_downloaded

        except Exception as e:
            print(f"Error processing edition: {str(e)}")
            page.goto(self.base_url)
            time.sleep(3)
            return 0

    def handle_popup(self, page) -> bool:
        try:
            popup_selectors = ['.gdpr-container', '.modal-dialog',
                               '#cookie-notice']
            button_selectors = ['#gdprContinue', '.gdpr-button',
                                '.accept-button']

            for popup_selector in popup_selectors:
                try:
                    if page.wait_for_selector(popup_selector, timeout=2000):
                        for button_selector in button_selectors:
                            button = page.query_selector(button_selector)
                            if button:
                                button.click()
                                time.sleep(2)
                                return True
                except Exception as e:
                    continue

            return False

        except Exception as e:
            print(f"Error handling popup: {str(e)}")
            return False

    def process_all_editions(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080})
            page = context.new_page()

            try:
                page.goto(self.base_url)
                time.sleep(3)

                current_date = datetime.now().strftime('%d/%m/%Y')
                print(f"\nFetching editions for {current_date}")
                self.editions = self.get_available_editions(page)

                if not self.editions:
                    print(f"No editions found for {current_date}!")
                    return False

                total_downloads = 0
                failed_editions = []

                for edition_info in self.editions:
                    try:
                        if edition_info['date'] != current_date:
                            continue

                        downloads = self.process_edition(page, edition_info)
                        if downloads > 0:
                            total_downloads += downloads
                        else:
                            failed_editions.append(edition_info['name'])

                        if not page.query_selector('#allOrgData'):
                            page.goto(self.base_url)
                            time.sleep(3)

                    except Exception as edition_error:
                        print(
                            f"Failed to process edition {edition_info['name']}: {str(edition_error)}")
                        failed_editions.append(edition_info['name'])
                        page.goto(self.base_url)
                        time.sleep(3)

                print(f"\nFinished processing editions for {current_date}")
                print(f"Total pages downloaded: {total_downloads}")
                if failed_editions:
                    print(f"Failed editions: {', '.join(failed_editions)}")
                return True

            except Exception as e:
                print(f"Error in main process: {str(e)}")
                return False

            finally:
                browser.close()


def main():
    base_url = "https://epaper.prabhanews.com/"
    crawler = AndhraPrabhaEpaperCrawler(base_url)

    print("Starting Andhra Prabha download process...")
    success = crawler.process_all_editions()

    if success:
        print("Process completed successfully.")
    else:
        print("Process completed with errors.")


if __name__ == "__main__":
    main()