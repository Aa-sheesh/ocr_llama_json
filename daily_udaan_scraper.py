import os
import time
from datetime import datetime

from playwright.sync_api import sync_playwright


class DailyUdaanEpaperCrawler:
    def __init__(self, base_url, output_dir="downloads/daily_udaan"):
        self.base_url = base_url
        self.output_dir = output_dir
        self.newspaper_name = "Daily Udaan"
        self.editions = []

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"Created output directory: {self.output_dir}")

    def get_available_editions(self, page) -> list:
        """Get available editions from the modal"""
        editions = []
        try:
            # Wait for the modal to appear
            page.wait_for_selector('#city-edition-modal', timeout=2000)
            current_date = datetime.now().strftime('%Y-%m-%d')
            print(f"Getting editions for current date: {current_date}")

            # Get all edition links from the modal
            edition_links = page.query_selector_all(
                '#city-edition-modal a.block.pages')

            for link in edition_links:
                try:
                    # Get edition name from the paragraph element
                    name_el = link.query_selector('p')
                    if not name_el:
                        continue
                    edition_name = name_el.inner_text().strip()

                    # Get the href attribute
                    href = link.get_attribute('href')
                    if not href:
                        continue

                    editions.append({
                        'name': edition_name,
                        'url': href,
                        'date': current_date
                    })
                except Exception as e:
                    print(f"Error processing edition item: {str(e)}")
                    continue

            print(f"Found {len(editions)} editions:")
            for edition in editions:
                print(f"- {edition['name']}")
            return editions

        except Exception as e:
            print(f"Error getting available editions: {str(e)}")
            return []

    def is_last_page(self, page) -> bool:
        """Check if current page is the last page"""
        try:
            # Get all page numbers
            page_numbers = page.query_selector_all('nav ul li a:not([id])')
            if not page_numbers:
                return True

            # Find the current page (with blue background)
            current_page = None
            for page_el in page_numbers:
                if 'bg-blue-700' in page_el.get_attribute('class'):
                    current_page = int(page_el.inner_text().strip())
                    break

            if current_page is None:
                return True

            # Find the highest page number
            max_page = 1
            for page_el in page_numbers:
                try:
                    page_num = int(page_el.inner_text().strip())
                    max_page = max(max_page, page_num)
                except Exception as e:
                    print(f"Error: {str(e)}")
                    continue

            return current_page == max_page

        except Exception as e:
            print(f"Error checking last page: {str(e)}")
            return True

    def process_edition(self, page, edition_info: dict) -> int:
        try:
            edition_name = edition_info['name']
            edition_url = edition_info['url']
            edition_date = edition_info['date']

            date_obj = datetime.strptime(edition_date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%Y-%m-%d')

            print(
                f"\nProcessing {edition_name} edition for date {edition_date}...")

            # Navigate to the edition URL
            page.goto(edition_url, wait_until='networkidle', timeout=10000)
            time.sleep(3)  # Wait for page to load

            # Create the edition folder
            edition_folder = self.create_edition_folder(
                                                        edition_name)

            successful_downloads = 0
            current_page = 1

            while True:
                try:
                    # Wait for the download button to be available
                    download_button = page.wait_for_selector(
                        '#downloadCurrentPDF',
                        timeout=2000)
                    if not download_button:
                        print(
                            f"Download button not found for page {current_page}")
                        break

                    # Set up download path
                    filepath = os.path.join(edition_folder,
                                            f"daily_udaan_{formatted_date}"
                                            f"_{current_page}.pdf")

                    # Set up download listener
                    with page.expect_download() as download_info:
                        # Click the download button
                        download_button.click()
                        download = download_info.value

                        # Wait for the download to complete and save the file
                        download.save_as(filepath)
                        print(
                            f"Downloaded page {current_page} for {edition_name} edition")
                        successful_downloads += 1

                    # Check if this is the last page
                    if self.is_last_page(page):
                        print(
                            f"Reached last page ({current_page}) for {edition_name}")
                        break

                    # Click the next button
                    next_button = page.query_selector('#nextPage')
                    if not next_button:
                        print("Next page button not found")
                        break

                    next_button.click()
                    time.sleep(2)  # Wait for page to load
                    current_page += 1

                except Exception as e:
                    print(f"Error processing page {current_page}: {str(e)}")
                    break

            print(
                f"Completed downloading {successful_downloads} pages for {edition_name}")
            return successful_downloads

        except Exception as e:
            print(f"Error processing edition: {str(e)}")
            return 0

    def create_edition_folder(self, edition_name: str) -> str:

        os.makedirs(self.output_dir, exist_ok=True)

        edition_name = edition_name.replace('/', '-').strip()
        edition_folder = os.path.join(self.output_dir, edition_name.lower())
        os.makedirs(edition_folder, exist_ok=True)

        return edition_folder

    def process_all_editions(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                accept_downloads=True  # Enable downloads
            )
            page = context.new_page()

            try:
                # Navigate to the main page
                page.goto(self.base_url)
                time.sleep(3)

                current_date = datetime.now().strftime('%Y-%m-%d')
                print(f"\nFetching editions for {current_date}")
                self.editions = self.get_available_editions(page)

                if not self.editions:
                    print(f"No editions found for {current_date}!")
                    return False

                total_downloads = 0
                failed_editions = []

                for edition_info in self.editions:
                    try:
                        downloads = self.process_edition(page, edition_info)
                        if downloads > 0:
                            total_downloads += downloads
                        else:
                            failed_editions.append(edition_info['name'])

                    except Exception as edition_error:
                        print(
                            f"Failed to process edition {edition_info['name']}: {str(edition_error)}")
                        failed_editions.append(edition_info['name'])

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
    base_url = "https://epaper.dailyudaan.com/"
    crawler = DailyUdaanEpaperCrawler(base_url)

    print("Starting Daily Udaan download process...")
    success = crawler.process_all_editions()

    if success:
        print("Process completed successfully.")
    else:
        print("Process completed with errors.")


if __name__ == "__main__":
    main()

