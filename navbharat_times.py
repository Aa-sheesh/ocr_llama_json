import os
import re
from datetime import datetime

import img2pdf
import requests
from bs4 import BeautifulSoup


class NavBharatTimesCrawler:
    def __init__(
        self,
        base_url="https://epaper.navbharattimes.com/",
        output_dir="navbharat_times",
    ):
        self.base_url = base_url
        self.output_dir = os.path.join("downloads", output_dir)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )
        os.makedirs(self.output_dir, exist_ok=True)

    def create_date_folder(self, state):
        folder_path = os.path.join(self.output_dir, state)
        os.makedirs(folder_path, exist_ok=True)
        return folder_path

    def get_states_and_ids(self):
        response = self.session.get(self.base_url)
        soup = BeautifulSoup(response.text, "html.parser")
        nav_items = soup.select("ul.nav_hds > li")
        state_map = {}

        for li in nav_items:
            a_tag = li.find("a")
            if not a_tag:
                continue

            state_name = (
                a_tag.get_text(strip=True).replace("/", "-").replace(" ",
                                                                     "-").lower()
            )
            onclick_attr = a_tag.get("onclick", "")
            match = re.search(r"/epaper/1/(\d+)/", onclick_attr)
            if match:
                state_id = match.group(1)
                state_map[state_name] = state_id

        return state_map

    def get_page_images(self, state, state_id, str_date):
        url = f"{self.base_url}{state}/{str_date}/{state_id}/page-1.html"
        response = self.session.get(url)

        if response.status_code != 200:
            print(f"Failed to fetch main page for {state}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        pages = soup.select("div.flipbook img")
        img_urls = [img.get("src") for img in pages if img.get("src")]

        return img_urls

    def download_and_save_pdf(self, img_urls, folder_path, state, date_str):
        pdf_path = os.path.join(folder_path, f"{state}_{date_str}.pdf")
        img_bytes = []
        for idx, img_url in enumerate(img_urls, start=1):
            try:
                print(f"Downloading {state} page {idx}: {img_url}")
                resp = self.session.get(img_url)
                if resp.status_code == 200:
                    img_bytes.append(resp.content)
                else:
                    print(f"Failed to download image {img_url}")
            except Exception as e:
                print(f"Error downloading {img_url}: {str(e)}")

        if img_bytes:
            with open(pdf_path, "wb") as f:
                f.write(img2pdf.convert(img_bytes))
            print(f"Saved PDF: {pdf_path}")
        else:
            print(f"No images downloaded for {state}")

    def process_newspapers(self):
        # date_str = datetime.now().strftime("%Y-%m-%d")
        states = self.get_states_and_ids()
        print(states)
        if not states:
            print("No states found on main page. Exiting.")
            return

        today_date = datetime.now()
        str_date = today_date.strftime("%Y-%m-%d")
        date_path = datetime.now().strftime("%Y_%m_%d")

        for state, state_id in states.items():
            folder_path = self.create_date_folder(state)
            img_urls = self.get_page_images(state, state_id, str_date)
            if img_urls:
                self.download_and_save_pdf(img_urls, folder_path, state, date_path)
            else:
                print(f"No pages found for {state} on {str_date}")


def main():
    crawler = NavBharatTimesCrawler()
    crawler.process_newspapers()


if __name__ == "__main__":
    main()
