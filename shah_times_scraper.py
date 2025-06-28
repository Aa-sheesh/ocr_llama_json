import os
import re
from datetime import datetime

import requests
from playwright.sync_api import sync_playwright


class ShahTimesEpaperDownloader:
    def __init__(self, edition_name=None, base_folder="shah_times"):
        self.edition_name = edition_name
        self.base_folder = os.path.join("downloads", base_folder)
        self.today_date = datetime.now().strftime("%Y_%m_%d")

    def download_pdf(self, pdf_url, save_path):
        """Download the PDF from the URL and save it to the specified path."""
        response = requests.get(pdf_url)
        response.raise_for_status()

        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'wb') as file:
            file.write(response.content)
        print(f"✅ Saved: {save_path}")

    @staticmethod
    def extract_edition_name(link_text):
        """
        Extract a normalized edition name from the link text.
        Example: "Shah Times New Delhi 3 June 2025" -> "new_delhi"
        """
        match = re.search(r"Shah Times (.+?) \d{1,2} \w+ \d{4}", link_text,
                          re.IGNORECASE)
        if match:
            return match.group(1).strip().lower().replace(" ", "_")
        return "unknown_edition"

    def process_editions(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto("https://shahtimesnews.com/category/epaper")
            page.wait_for_selector('article#post-82108')
            page.click('article#post-82108 a')
            page.wait_for_load_state('domcontentloaded')

            page.wait_for_selector('div.wp-block-file')
            edition_blocks = page.query_selector_all('div.wp-block-file')

            for block in edition_blocks:
                link_element = block.query_selector('a[href$=".pdf"]')
                if not link_element:
                    continue

                pdf_url = link_element.get_attribute("href")
                link_text = link_element.inner_text().strip()
                edition = self.extract_edition_name(link_text)

                folder_path = os.path.join(self.base_folder, edition)
                file_name = f"{edition}_{self.today_date}.pdf"
                save_path = os.path.join(folder_path, file_name)

                if self.edition_name is None or self.edition_name == edition:
                    print(f"🔍 Download: {edition} -> {pdf_url}")
                    self.download_pdf(pdf_url, save_path)

            browser.close()


if __name__ == "__main__":
    downloader = ShahTimesEpaperDownloader(edition_name="new_delhi")  # or set to None to download all
    downloader.process_editions()
