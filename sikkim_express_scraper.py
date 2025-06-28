import os
from datetime import datetime

import img2pdf
import requests
from bs4 import BeautifulSoup


class SikkimExpressCrawler:
    def __init__(self, base_url):
        self.base_url = base_url
        self.newspaper_name = "sikkim_express"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )
        self.news_paper_page_dir = "news_paper_page"
        self.news_clip_dir = "news_clip"
        self.image_clip_base_url = "http://www.sikkimexpress.com/"

        if not os.path.exists("downloads/" + self.newspaper_name):
            os.makedirs("downloads/" + self.newspaper_name)
            print(f"Created output directory: {self.newspaper_name}")

    def create_folder(self, output_dir, new_dir):
        new_folder = os.path.join(output_dir, new_dir)
        if not os.path.exists(new_folder):
            os.makedirs(new_folder)
            print(f"Created folder: {new_folder}")
        return new_folder

    def get_latest_pdf_url(self, max_attempts=7):

        today = datetime.now()

        for i in range(max_attempts):
            formatted_date = today.strftime("%Y-%m-%d")

            pdf_url = f"{self.base_url}/date/{formatted_date}"

            try:
                response = self.session.head(pdf_url)

                if response.status_code == 200:
                    print(f"Found PDF for date: {formatted_date}")
                    return pdf_url, formatted_date
                else:
                    print(f"No PDF found for date: {formatted_date}")

            except Exception as e:
                print(f"Error checking PDF for date {formatted_date}: {str(e)}")

        print(f"No PDF found after checking {max_attempts} days")
        return None, None

    def download_pdf_data(self, pdf_url, date_str):
        try:
            # date_folder = self.create_folder(self.newspaper_name, date_str)
            date_folder = os.path.join("downloads/" + self.newspaper_name)
            os.makedirs(date_folder, exist_ok=True)
            response = self.session.get(pdf_url)

            soup = BeautifulSoup(response.text, "html.parser")
            news_paper = soup.find("div", attrs={"class": "all-paper"})
            page_number = 0
            for news_paper_page in news_paper.find_all(
                    "div", attrs={"class": "main-news-paper"}
            ):
                page_number += 1
                page = news_paper_page.get("id")
                # filename = f"{self.newspaper_name} -- {date_str} -- {page}.pdf"
                # file_path = os.path.join(news_paper_folder, filename)
                image_url = news_paper_page.find("img").get("src")
                response = self.session.get(image_url)
                # print(
                #     f"Downloading PDF Page: {page} | filename: {filename} | Image URL: {image_url}"
                # )
                # with open(file_path, "wb") as f:
                #     f.write(img2pdf.convert(response.content))

                # news_clip_page_folder = self.create_folder(news_clip_folder, page)
                clip_number = 0
                for news_clip in news_paper_page.find_all("area"):
                    news_clip_link = news_clip.get("href", "")
                    if news_clip_link:
                        clip_number += 1
                        news_clip_url = news_clip_link.replace("%2F", "/")
                        news_clip_response = self.session.get(
                            f"{self.image_clip_base_url}{news_clip_url}"
                        )
                        news_clip_filename = (f"{self.newspaper_name}_"
                                              f"{date_str}_page_"
                                              f"{page_number}_article"
                                              f"_{clip_number}.pdf")
                        news_clip_file_path = os.path.join(
                            date_folder, news_clip_filename
                        )
                        with open(news_clip_file_path, "wb") as f:
                            f.write(img2pdf.convert(news_clip_response.content))
                        print(f"Downloaded: {news_clip_filename}")

            return True

        except Exception as e:
            print(f"Error downloading PDF {pdf_url}: {str(e)}")
            return None, None

    def process_latest_newspaper(self):
        pdf_url, date_str = self.get_latest_pdf_url()
        print("News url: ", pdf_url, date_str)

        if not pdf_url:
            print("Could not find any available newspaper PDF")
            return False

        pdf_response = self.download_pdf_data(pdf_url, date_str)

        return True


def main():
    base_url = "http://epaper.sikkimexpress.com"
    crawler = SikkimExpressCrawler(base_url)

    print("Processing latest available newspaper...")
    crawler.process_latest_newspaper()


if __name__ == "__main__":
    main()
