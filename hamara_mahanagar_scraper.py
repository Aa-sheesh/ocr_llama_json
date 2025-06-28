import os
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup


class EpaperCrawler:
    def __init__(self, base_url):

        self.base_url = base_url
        self.newspaper_name = "hamara_mahanagar"
        self.session = requests.Session()
        self.headers = {}

    def get_formatted_date(self):
        return datetime.now().strftime("%Y_%m_%d")

    def get_page(self, url):

        try:
            response = self.session.get(url, headers=self.headers)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def get_editions(self):

        soup = self.get_page(self.base_url)
        if not soup:
            return []

        editions = []
        for div in soup.find_all("div", class_="category-title"):
            link = div.find("a")
            if link and "href" in link.attrs:
                edition_name = link.text.strip().lower()
                edition_url = (
                    self.base_url + link["href"]
                    if link["href"].startswith("/")
                    else link["href"]
                )
                editions.append((edition_name, edition_url))
                print(f"Found edition: {edition_name} at {edition_url}")

        return editions

    def get_pdf_url(self, edition_url):

        soup = self.get_page(edition_url)
        if not soup:
            return None

        pdf_link = soup.find("a", class_="btn-pdfdownload")
        if pdf_link and "href" in pdf_link.attrs:
            pdf_url = pdf_link["href"]
            if pdf_url.startswith("/"):
                pdf_url = self.base_url + pdf_url
            print(f"Found PDF URL: {pdf_url}")
            return pdf_url

        print(f"No PDF download link found on {edition_url}")
        return None

    def download_pdf(self, pdf_url, edition_name):

        try:
            formatted_date = self.get_formatted_date()
            date_folder = os.path.join("downloads", self.newspaper_name)
            os.makedirs(date_folder, exist_ok=True)
            output_dir = os.path.join(date_folder, edition_name)
            os.makedirs(output_dir, exist_ok=True)
            filename = f"{edition_name}_{formatted_date}.pdf"
            file_path = os.path.join(output_dir, filename)

            if os.path.exists(file_path):
                print(f"File already exists: {file_path}")
                return file_path

            print(f"Downloading {pdf_url} to {file_path}")
            response = self.session.get(pdf_url, headers=self.headers,
                                        stream=True)
            response.raise_for_status()

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"Downloaded {file_path}")
            return file_path

        except requests.exceptions.RequestException as e:
            print(f"Error downloading {pdf_url}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error downloading {pdf_url}: {e}")
            return None

    def process_all_editions(self):

        editions = self.get_editions()
        print(f"Found {len(editions)} editions")

        for edition_name, edition_url in editions:
            print(f"Processing edition: {edition_name}")

            pdf_url = self.get_pdf_url(edition_url)
            if not pdf_url:
                print(f"Skipping edition {edition_name}: no PDF URL found")
                continue

            pdf_path = self.download_pdf(pdf_url, edition_name)
            if not pdf_path:
                print(f"Skipping edition {edition_name}: PDF download failed")
                continue

            time.sleep(2)

        return True


if __name__ == "__main__":
    base_url = "https://epaper.hamaramahanagar.net"
    crawler = EpaperCrawler(base_url)

    print("Starting Hamara Mahanagar crawler")
    results = crawler.process_all_editions()

    if results:
        print("Data get successfully.")
    else:
        print("Data not found.")
