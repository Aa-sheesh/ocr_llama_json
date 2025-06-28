import os
from datetime import datetime
from io import BytesIO

import img2pdf
import requests
from bs4 import BeautifulSoup


class NavodayaTimesCrawler:
    def __init__(
        self,
    ):
        self.base_url = "https://epaper.navodayatimes.in"
        self.newspaper_name = "navodaya_times"
        self.session = requests.Session()
        self.news_paper = "news_paper"
        self.news_page = "news_page"

    def create_folder(self, *paths):
        folder_path = os.path.join("downloads",self.newspaper_name, *paths)
        os.makedirs(folder_path, exist_ok=True)
        return folder_path

    def get_additions(self):
        try:
            response = self.session.get(self.base_url)
            soup = BeautifulSoup(response.text, "html.parser")
            div_soup = soup.find("div", {"id": "ContentPlaceHolder1_dvAllEd"})
            addition_dict = {
                "_".join(a_tag.get_text(strip=True).split()).lower(): a_tag["href"]
                for a_tag in div_soup.find_all("a")
                if a_tag.get_text(strip=True) != "Magazine"
            }
            return addition_dict
        except Exception as e:
            print(f"Error get_additions: {str(e)}")
            return {}

    def get_addition_page_link(self, addition_url):
        try:
            response = self.session.get(addition_url)
            soup = BeautifulSoup(response.text, "html.parser")
            return list(
                filter(
                    None,
                    (
                        soup.find("input", attrs={"id": "hidxlImg"})
                        .get("value", "")
                        .split(",")
                    ),
                )
            )
        except Exception as e:
            print(f"Error get_addition_page_link: {str(e)}")
            return []

    def download_pdf_data(self, page_link_list, date_str, addition_name):
        try:
            # output_folder_paper = self.create_folder(
            #     date_str, addition_name, self.news_paper
            # )
            output_folder_page = self.create_folder( addition_name)
            # merger = PdfMerger()
            for page_number, page_link in enumerate(page_link_list):
                print(f"Downloading {addition_name} page {page_number}: {page_link}")
                filename = f"{addition_name}_{date_str}_{page_number+1}.pdf"
                file_path = os.path.join(output_folder_page, filename)
                response = requests.get(page_link)
                with open(file_path, "wb") as f:
                    f.write(img2pdf.convert(BytesIO(response.content)))
                print(f"News page saved: {file_path}")

                # merger.append(file_path)

            # filename = f"{self.newspaper_name}-{addition_name}-{date_str}.pdf"
            # file_path = os.path.join(output_folder_paper, filename)
            # print(f"News paper saved: {file_path}")
            # merger.write(file_path)
            # merger.close()
            return True
        except Exception as e:
            print(f"Error downloading PDF: {str(e)}")
            return False

    def process_newspapers(self):
        date_str = datetime.now().strftime("%Y_%m_%d")
        additions = self.get_additions()
        if not additions:
            print(f"No additions found")
            return False
        print(f"Found {len(additions)} additions")
        for addition_name, addition_url in additions.items():
            print(f"addition_name = {addition_name}")
            page_link_list = self.get_addition_page_link(addition_url)
            if not page_link_list:
                print(f"No page link for {addition_name}")
                continue
            print(f"{len(page_link_list)} page link found for {addition_name}")
            status = self.download_pdf_data(page_link_list, date_str, addition_name)
            if status:
                print(f"successfully downloaded: {addition_name}")
            else:
                print(f"failed to download: {addition_name}")
        return None


def main():
    crawler = NavodayaTimesCrawler()
    crawler.process_newspapers()


if __name__ == "__main__":
    main()
