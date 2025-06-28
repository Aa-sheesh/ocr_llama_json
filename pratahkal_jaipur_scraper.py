"""
Multiple Images of pages
"""
import os
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup


class PratahkalJaipurCrawler:
    BASE_URL = "https://epaper.pratahkal.com/index.php"

    def __init__(self, edition="JPpage"):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        })
        self.edition = edition
        self.date_str = datetime.now()
        self.output_dir = "downloads/pratahkal/jaipur"
        os.makedirs(self.output_dir, exist_ok=True)

    def _get_total_pages(self) -> int:
        try:
            response = self.session.get(
                f"{self.BASE_URL}?edition={self.edition}&date={self.date_str.strftime('%Y-%m-%d')}&page=1",
                timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                options = soup.select("#edition_selector option")
                for option in options:
                    if option.get("value") == self.edition:
                        return int(option.get("data-pages", '0'))
        except requests.RequestException:
            pass
        return 0

    def _get_page_html(self, page_num: int) -> str | None:
        params = {
            "edition": self.edition,
            "date": self.date_str.strftime("%Y-%m-%d"),
            "page": page_num,
        }
        try:
            response = self.session.get(self.BASE_URL, params=params,
                                        timeout=15)
            if response.status_code == 200:
                return response.text
        except requests.RequestException:
            pass
        return None

    @staticmethod
    def _extract_image_url_from_js(html: str, page_num: int) -> str | None:
        full_match = re.search(
            r'(https?://[^"\']*JPpage_' + str(page_num) + r'\.jpg)', html)
        if full_match:
            return full_match.group(1)

        rel_match = re.search(
            r'src\s*:\s*"([^"]*JPpage_' + str(page_num) + r'\.jpg)"', html)
        if rel_match:
            return "https://epaper.pratahkal.com" + rel_match.group(1)
        return None

    def _download_image(self, url: str, filename: str) -> bool:
        try:
            response = self.session.get(url, timeout=20)
            if response.status_code == 200 and response.headers.get(
                    "Content-Type", "").startswith("image/"):
                with open(filename, "wb") as f:
                    f.write(response.content)
                return True
        except requests.RequestException:
            pass
        return False

    def run(self) -> None:
        total_pages = self._get_total_pages()
        if total_pages == 0:
            print("Could not determine total number of pages. Exiting.")
            return

        image_files = []
        for page_num in range(1, total_pages + 1):
            html = self._get_page_html(page_num)
            if not html:
                print(f"No HTML content for page {page_num}, skipping.")
                continue

            image_url = self._extract_image_url_from_js(html, page_num)
            if not image_url:
                print(f"No image found for page {page_num}, skipping.")
                continue

            filename = os.path.join(self.output_dir,
                                    f"pratahkal{self.date_str.strftime('%d_%m_%Y')}{page_num}.jpg")
            if self._download_image(image_url, filename):
                print(f"Downloaded page {page_num} image.")
                image_files.append(filename)
            else:
                print(f"Failed to download image from {image_url}, skipping.")


def main() -> None:
    crawler = PratahkalJaipurCrawler()
    crawler.run()


if __name__ == "__main__":
    main()
