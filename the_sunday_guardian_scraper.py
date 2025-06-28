import os
from datetime import datetime, timedelta

import img2pdf
import requests
from bs4 import BeautifulSoup


class TheSundayGuardianCrawler:
    def __init__(self):
        self.base_url = "https://epaper.sundayguardianlive.com"
        self.news_paper_name = "the_sunday_guardian"
        self.session = requests.Session()
        self.output_dir = os.path.join("downloads", self.news_paper_name)
        os.makedirs(self.output_dir, exist_ok=True)

    def get_image_urls(self):
        try:
            response = self.session.get(self.base_url)
            soup = BeautifulSoup(response.text, "html.parser")
            div_tag_paper = soup.find("div",
                                      class_="row frame0 name_of_posts_class")
            a_tag_paper = div_tag_paper.find_all("a")
            if not a_tag_paper:
                print("No paper found.")
                return []
            news_paper_url = a_tag_paper[0].get("href")
            print("Processing newspaper url: ", news_paper_url)
            response = self.session.get(news_paper_url)
            soup = BeautifulSoup(response.text, "html.parser")
            div_tag = soup.find("div", attrs={"class": "overlay-content row"})
            if not div_tag:
                print("No images found on the page")
                return []
            image_url_list = []
            for image_tag in div_tag.find_all("img"):
                image_url = image_tag.get("src")
                if not image_url:
                    continue
                name_to_replace = image_url.split("-")[-1].split(".")[0]
                image_url = image_url.replace(name_to_replace, "scaled")
                image_url_list.append(image_url)
            print(f"{len(image_url_list)} images found")
            return image_url_list
        except Exception as e:
            print("Exception in get_image_urls", e)
            return []

    def download_and_save_pdf(self, img_urls, date):
        global output_pdf_path
        try:
            date_str = date.strftime("%Y_%m_%d")
            page_number = 0
            for image_url in img_urls:
                print("processing image", image_url)
                img_resp = self.session.get(image_url)
                if img_resp.status_code != 200:
                    print(
                        f"Failed to download image: {image_url} | status: {img_resp.status_code}"
                    )
                    continue
                page_number += 1
                output_pdf_path = os.path.join(
                    self.output_dir,
                    f"{self.news_paper_name}_{date_str}_{page_number}.pdf",
                )

                with open(output_pdf_path, "wb") as f:
                    f.write(img2pdf.convert(img_resp.content))
                # merger.append(BytesIO(img2pdf.convert(img_resp.content)))
                print(f"Image download successfully: {image_url}")
            return output_pdf_path
        except Exception as e:
            print("Exception in get_image_urls", e)
            return False

    def process_newspapers(self):
        sunday_date = (
                datetime.today() - timedelta(
            days=(datetime.today().weekday() + 1) % 7)
        ).date()
        print("Processing newspaper date:", sunday_date)

        image_urls = self.get_image_urls()
        if not image_urls:
            print("No images found on the page")
            return False

        pdf_status = self.download_and_save_pdf(image_urls, sunday_date)
        if pdf_status:
            print("PDF saved: ", pdf_status)
        else:
            print("PDF NOT saved: ", pdf_status)
        return None


def main():
    crawler = TheSundayGuardianCrawler()
    crawler.process_newspapers()


if __name__ == "__main__":
    main()
