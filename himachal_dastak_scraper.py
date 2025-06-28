"""
Multiple Images of pages
"""
import os
import time
from datetime import date

import requests
from playwright.sync_api import sync_playwright


class HimachalDastakCrawler:
    def __init__(self, base_url="https://epaper.himachaldastak.com/",
                 output_dir=None):
        self.base_url = base_url
        self.today_str = f"{date.today():%Y_%m_%d}"
        default_dir = "downloads/himachal_dastak/shimla"

        self.folder = output_dir or default_dir

        os.makedirs(self.folder, exist_ok=True)

    @staticmethod
    def download_image(url: str, filename: str):
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        with open(filename, "wb") as f:
            f.write(r.content)

    def scrape(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto(self.base_url, wait_until="domcontentloaded")

            nav = page.locator(
                "div.container-fluid.navbar-collapse.collapse ul.nav.nav-justified li a"
            ).filter(has_text="upper-shimla")
            nav.first.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_selector("div.paper_single a")

            anchors = page.locator("div.paper_single a")
            count = anchors.count()

            for i in range(count):
                anchors = page.locator("div.paper_single a")
                anchors.nth(i).click()
                page.wait_for_selector(
                    "div.fancybox-inner img",
                    timeout=10000
                )
                anchor = page.locator(
                    "div.fancybox-inner img"
                )
                url = anchor.get_attribute("src")
                if url:
                    "({publication_name}_{date}_{page_number}.png)s"
                    file_name = f"himachal_dastak{self.today_str}{i + 1:02d}.jpg"
                    filepath = os.path.join(self.folder, file_name)
                    self.download_image(url, filepath)
                page.keyboard.press("Escape")
                time.sleep(1)

            browser.close()


if __name__ == "__main__":
    HimachalDastakCrawler().scrape()
