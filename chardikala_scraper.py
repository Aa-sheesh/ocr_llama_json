import os
import time
from datetime import datetime

import requests
from playwright.sync_api import sync_playwright


class ChardikalaEpaperCrawler:
    def __init__(self, base_url, output_dir="downloads/chardikala"):
        self.base_url = base_url
        self.output_dir = output_dir
        self.newspaper_name = "Chardikala"
        self.editions = []

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"Created output directory: {self.output_dir}")

    def get_available_editions(self, page) -> list:
        """Get available editions from the website"""
        editions = []
        try:
            # Wait for the editions to load
            page.wait_for_selector('.category-thumb-box', timeout=2000)
            current_date = datetime.now().strftime('%Y-%m-%d')
            print(f"Getting editions for current date: {current_date}")

            # Get all edition boxes
            edition_boxes = page.query_selector_all('.category-thumb-box')

            for box in edition_boxes:
                try:
                    # Get edition name from the category title
                    title_element = box.query_selector('.category-title a')
                    if not title_element:
                        continue

                    edition_name = title_element.inner_text().strip()
                    if not edition_name:
                        continue

                    # Get the href attribute
                    href = title_element.get_attribute('href')
                    if not href:
                        continue

                    # Construct full URL if needed
                    if href.startswith('/'):
                        href = f"{self.base_url.rstrip('/')}{href}"

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

    def process_edition(self, page, edition_info: dict) -> int:
        try:
            edition_name = edition_info['name']
            edition_url = edition_info['url']
            edition_date = edition_info['date']
            print(
                f"\nProcessing {edition_name} edition for date {edition_date}...")

            if "magazine" in edition_name.lower():
                print(f"Skipping {edition_name} as it is a magazine.")
                return 0

            # Navigate to the edition URL
            page.goto(edition_url, wait_until="networkidle", timeout=10000)

            # Create the folder for the edition
            edition_folder = self.create_edition_folder(
                                                        edition_name)

            # Wait for the PDF download button
            pdf_button = page.wait_for_selector('.btn-pdfdownload',
                                                timeout=2000)

            # Extract the href attribute of the download button
            pdf_url = pdf_button.get_attribute('href')
            if not pdf_url:
                print(f"No PDF URL found for {edition_name}")
                return 0

            # Download the PDF
            self.download_pdf(pdf_url, edition_folder, edition_name,edition_date)
            print(f"Downloaded PDF for {edition_name}")
            return 1

        except Exception as e:
            print(f"Error processing edition : {str(e)}")
            return 0

    def download_pdf(self, pdf_url: str, edition_folder: str,
                     edition_name: str,date_str):
        print(date_str)

        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%Y-%m-%d')

        response = requests.get(pdf_url)
        if response.status_code == 200:
            filepath = os.path.join(edition_folder, f"cha"
                                                    f"rdi"
                                                    f"kal"
                                                    f"a_{formatted_date}.pdf")
            with open(filepath, "wb") as pdf_file:
                pdf_file.write(response.content)
        else:
            raise Exception(f"Failed to download PDF from {pdf_url}")

    def create_edition_folder(self, edition_name: str) -> str:

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
                time.sleep(2)

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
                print(f"Total PDFs downloaded: {total_downloads}")
                if failed_editions:
                    print(f"Failed editions: {', '.join(failed_editions)}")
                return True

            except Exception as e:
                print(f"Error in main process: {str(e)}")
                return False

            finally:
                browser.close()


def main():
    base_url = "https://epaper.charhdikala.com/"
    crawler = ChardikalaEpaperCrawler(base_url)

    print("Starting Chardikala download process...")
    success = crawler.process_all_editions()

    if success:
        print("Process completed successfully.")
    else:
        print("Process completed with errors.")


if __name__ == "__main__":
    main()
