import json
from io import BytesIO

import img2pdf
import requests
from bs4 import BeautifulSoup
import os
import re
from datetime import datetime
from urllib.parse import urljoin


class PraharCrawler:
    def __init__(self):
        self.base_url = "https://epaper.prahaar.in/"
        self.newspaper_name = "prahar"
        self.session = requests.Session()
        self.news_page = "news_page"
        self.news_clip = "news_clip"
        self.output_dir =os.path.join("downloads",self.newspaper_name)
        os.makedirs(self.output_dir,exist_ok=True)

    def create_folder(self, output_dir, new_dir):
        new_folder = os.path.join(output_dir, new_dir)
        os.makedirs(new_folder, exist_ok=True)
        return new_folder

    def download_image(self, url, file_path):
        try:
            response = requests.get(url)
            with open(file_path, "wb") as f:
                f.write(img2pdf.convert(BytesIO(response.content)))
            print(f"Image saved: {file_path}")
            return True
        except Exception as e:
            print(f"Error downloading {url}: {str(e)}")
            return False

    def get_edition_dict(self, date):
        try:
            response = requests.get(self.base_url)
            if response.status_code != 200:
                print(f"Failed to get edition: {self.base_url}")
                return {}
            soup = BeautifulSoup(response.text, "html.parser")
            div_soup = soup.find("div", attrs={"class": "centerBody"}).find(
                "div", attrs={"class": "edition"}
            )
            url = urljoin(self.base_url, div_soup.find("a").get("href"))
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract <script> content containing edition_info
            script_tag = soup.find("script", string=re.compile(r"edition_info\s*="))
            if not script_tag:
                return {}

            match = re.search(
                r"edition_info\s*=\s*(\{.*?\});", script_tag.string, re.DOTALL
            )
            if not match:
                return {}

            edition_info = json.loads(match.group(1))
            return edition_info
        except Exception as e:
            print(f"Error extracting page links: {str(e)}")
            return {}

    def process_story(
        self,
        edition_name,
        page_number,
        story_number,
        story_data,
        clip_page_dir,
        path_date,
    ):
        try:
            print(
                f"Processing story: {edition_name} | Page: {page_number} | Story: {story_number}"
            )
            url = urljoin(self.base_url, story_data["Image"])
            file_path = os.path.join(
                clip_page_dir,
                f"{edition_name}_{path_date}_page_{page_number}_article"
                f"_{story_number}.pdf",
            )
            self.download_image(url, file_path)
        except Exception as e:
            print(f"Error in process_page for {edition_name}: {str(e)}")

    def process_page(
        self, edition_name, page_number, page_info, edition_dir, path_date
    ):
        try:
            print(f"Processing page: {edition_name} | Page: {page_number}")
            url = urljoin(self.base_url, page_info["Image"])
            # page_dir = self.create_folder(edition_dir, self.news_page)
            # file_path = os.path.join(
            #     page_dir,
            #     f"{self.newspaper_name}-{edition_name}-{path_date}-page {str(page_number).zfill(2)}.pdf",
            # )
            # self.download_image(url, file_path)
            if "Stories" not in page_info:
                print(f"Page {page_number} has no stories")
                return True
            print(f"Found {len(page_info['Stories'])} stories in page {page_number}")
            # clip_dir = self.create_folder(edition_dir, self.news_clip)
            # clip_page_dir = self.create_folder(
            #     clip_dir, f"Page {str(page_number).zfill(2)}"
            # )
            for story_number, story_data in page_info["Stories"].items():
                self.process_story(
                    edition_name,
                    page_number,
                    int(story_number),
                    story_data,
                    edition_dir,
                    path_date,
                )
            return True
        except Exception as e:
            print(f"Error in process_page for {edition_name}: {str(e)}")

    def process_edition(self, edition_name, edition_data, path_date):
        try:
            print(f"Processing edition: {edition_name}")
            page_info = edition_data.get("Main", {}).get("Pages", {})
            if not page_info:
                print(f"No page info found: {edition_name}")
                return False
            print(f"Found {len(page_info)} pages")
            edition_name = "_".join(edition_name.split()).lower()
            edition_dir = os.path.join(self.output_dir, edition_name)
            os.makedirs(edition_dir, exist_ok=True)
            for page_number, page_data in page_info.items():
                self.process_page(
                    edition_name, int(page_number), page_data, edition_dir, path_date
                )
            return True
        except Exception as e:
            print(f"Error in process_edition")
            return False

    def crawl_newspaper(self):
        date = datetime.now().date()

        edition_dict = self.get_edition_dict(date)
        date_str = date.strftime("%d%m%Y")
        if not edition_dict and date_str not in edition_dict:
            print(f"No editions found for {date}")
            return False
        edition_data_dict = edition_dict[date_str]
        print(f"Found {len(edition_data_dict)} editions for {date}")
        path_date = date.strftime("%Y_%m_%d")
        # date_dir = self.create_folder(self.newspaper_name, path_date)
        for edition_name, edition_data in edition_data_dict.items():
            self.process_edition(edition_name, edition_data, path_date)
        return True


if __name__ == "__main__":
    crawler = PraharCrawler()
    status = crawler.crawl_newspaper()
    if status:
        print("Process Complete")
    else:
        print("Process Failed")
