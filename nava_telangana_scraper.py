import json
import os
from datetime import datetime

import requests
from playwright.sync_api import sync_playwright


class NavaTelanganaEpaperCrawler:
    def __init__(self):
        self.base_url = "https://epaper.navatelangana.com"
        self.newspaper_name = "nava_telangana"
        self.edition_api = "https://epaper.navatelangana.com/Home/GetDefaultFirstpagesListServiceDynamic"

        self.output_dir = os.path.join("downloads", self.newspaper_name)
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"Output directory: {self.newspaper_name}")

    def process_all_editions(self):
        str_date = datetime.now().strftime("%d/%m/%Y")
        date_path = datetime.now().strftime("%Y_%m_%d")
        request_data = requests.get(
            self.edition_api + f"?currenteditiondate={str_date}"
        )
        json_data = json.loads((request_data.json()))
        for data in json_data.get(str(0), []):
            with sync_playwright() as p:
                edition_type = data["Location"]
                edition_name = "_".join(data["Location"].split()).lower()
                newspaper_folder = os.path.join(self.output_dir, edition_name)
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()
                try:
                    location = edition_type.replace(
                        " ", "" if edition_type == "HYDERABAD MAIN" else "%20"
                    )
                    page.goto(
                        self.base_url + f"/{location}?pgid={data['PageId']}")
                    page.wait_for_selector("#edition_download")

                    # Listen for download while clicking
                    with page.expect_download() as download_info:
                        page.click("#edition_download")
                    download = download_info.value
                    file_name = f"{edition_name}_{date_path}.pdf"
                    file_path = os.path.join(newspaper_folder, file_name)
                    # Save the file
                    download.save_as(file_path)
                    print(f"Downloaded as {file_path}")

                except Exception as e:
                    print(f"Error in main process: {e}")
                finally:
                    browser.close()
        return True


if __name__ == "__main__":
    crawler = NavaTelanganaEpaperCrawler()
    print("Starting newspaper download process...")
    success = crawler.process_all_editions()
    if success:
        print("Process completed successfully.")
    else:
        print("Process completed with errors.")
