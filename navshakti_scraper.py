"""
Single Page Multiple PDFs
"""
import os
import re
from datetime import datetime
from typing import Optional, Dict

import requests
from playwright.sync_api import sync_playwright


class FreePressJournalCrawler:
    BASE_URL = "https://epaper.freepressjournal.in/"

    def __init__(self, output_dir="downloads/navshakti", max_editions=5,
                 headless=False):
        self.output_dir = output_dir
        self.max_editions = max_editions
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/91.0.4472.124 Safari/537.36"
        })
        os.makedirs(self.output_dir, exist_ok=True)
        self.master_dict: Dict[str, Dict[int, str]] = {}
        self.headless = headless

    @staticmethod
    def clean_name(name: str) -> str:
        return re.sub(r'[\\/*?:"<>|]', "_", name)

    @staticmethod
    def extract_uuid(url: str) -> Optional[str]:
        match = re.search(
            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
            url)
        return match.group(0) if match else None

    @staticmethod
    def extract_numeric_id(url: str) -> Optional[str]:
        match = re.search(r"\b(\d+)\b", url)
        return match.group(1) if match else None

    def create_folder(self) -> str:
        folder_path = os.path.join(self.output_dir, "maharashtra")
        os.makedirs(folder_path, exist_ok=True)
        return folder_path

    def download_pdf(self, url: str, path: str) -> bool:
        try:
            response = self.session.get(url, stream=True, timeout=30)
            if response.status_code == 200:
                with open(path, "wb") as f:
                    for chunk in response.iter_content(1024 * 1024):
                        f.write(chunk)
                print(f"Downloaded PDF: {path}")
                return True
            print(
                f"Failed to download {url} (status {response.status_code})")
            return False
        except requests.RequestException as e:
            print(f"Request error downloading {url}: {e}")
            return False

    def dismiss_popup(self, page) -> None:
        try:
            btn = page.locator("button.izooto-optin--cta-later")
            if btn.is_visible():
                btn.click(force=True)
                print("Popup dismissed.")
        except Exception:
            pass  # Ignore if no popup

    def scrape_edition(self, page, index: int) -> bool:
        try:
            holder = page.locator("div.epapers_holder").nth(1)
            card_boxes = holder.locator("div.card-box")
            total_editions = card_boxes.count()

            if index >= total_editions:
                print("No more editions available.")
                return False

            card = card_boxes.nth(index)
            a_tag = card.locator("a")

            a_tag.scroll_into_view_if_needed()
            with page.expect_navigation(timeout=20000):
                a_tag.click(force=True)

            current_url = page.url
            print(f"Navigated to edition: {current_url}")

            match = re.search(
                r"freepressjournal.in/\d+/([^/]+)/(\d{2}-\d{2}-\d{4})",
                current_url)
            edition_name = self.clean_name(
                match.group(1)).lower().replace("-",
                                                "_") if match else "unknown_edition"
            date_folder = match.group(2).replace("-",
                                                 "_") if match else datetime.now().strftime(
                "%d_%m_%Y")

            folder = self.create_folder()

            self.dismiss_popup(page)

            left_nav_bar = page.locator("#page-thumbs")
            a_tags = left_nav_bar.locator("a")
            page_count = a_tags.count()
            print(f"Found {page_count} page thumbnails.")

            paper_id = None
            paper_pages: Dict[int, str] = {}

            for j in range(page_count):
                a_tag = a_tags.nth(j)
                a_tag.scroll_into_view_if_needed()
                img_tag = a_tag.locator("img")

                # Scroll into view and wait for the actual src to load
                img_tag.scroll_into_view_if_needed()
                page.wait_for_timeout(300)

                for _ in range(10):
                    src = img_tag.get_attribute("src")
                    if src and not src.startswith("data:image/"):
                        break
                    page.wait_for_timeout(200)
                else:
                    print(
                        f"WARNING: Could not extract UUID or numeric ID from page {j + 1}, src: {src}")
                    continue

                uuid = self.extract_uuid(src)
                numeric_id = self.extract_numeric_id(src)
                if paper_id is None:
                    paper_id = numeric_id
                if uuid:
                    paper_pages[j + 1] = uuid

            if paper_id is None:
                print("Could not extract paper ID.")
                return False

            self.master_dict[paper_id] = paper_pages

            for page_num, uuid in paper_pages.items():
                pdf_url = f"{self.BASE_URL}download/issuepage/newspaper/{paper_id}/{uuid}/{page_num}.pdf"
                save_path = os.path.join(folder,
                                         f"{edition_name}{date_folder}{page_num}.pdf")
                if not os.path.exists(save_path):
                    if not self.download_pdf(pdf_url, save_path):
                        print(
                            f"Failed to download page {page_num} of {edition_name}")

            self.master_dict[paper_id].clear()
            return True

        except Exception as e:
            print(f"Error scraping edition {index + 1}: {e}")
            return False

    def run(self) -> None:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context()
            page = context.new_page()

            page.goto(self.BASE_URL, timeout=60000)
            page.wait_for_selector("div.epapers_holder")

            for i in range(self.max_editions):
                print(f"Processing edition {i + 1}")
                success = self.scrape_edition(page, i)
                if not success:
                    print("Stopping further edition processing.")
                    break
                page.goto(self.BASE_URL, timeout=30000)
                page.wait_for_selector("div.epapers_holder")

            browser.close()
            print("All done.")


def main():
    crawler = FreePressJournalCrawler(headless=True, max_editions=5)
    crawler.run()


if __name__ == "__main__":
    main()
