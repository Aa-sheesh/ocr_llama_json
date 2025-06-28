import requests
from bs4 import BeautifulSoup
import os
import re
from datetime import datetime
from urllib.parse import urljoin
from PIL import Image


class NiyomiyaBartaCrawler:
    def __init__(self):
        self.base_url = "https://niyomiyabarta.com/epaper/"
        self.newspaper_name = "niyomiya_barta"
        # os.makedirs(self.newspaper_name, exist_ok=True)

    def create_date_folder(self):
        date_folder = os.path.join("downloads",self.newspaper_name)
        os.makedirs(date_folder, exist_ok=True)
        return date_folder

    def download_image(self, img_url, page_num, date_folder, formatted_date):
        try:
            response = requests.get(img_url, stream=True)
            if response.status_code == 200:
                file_name = f"{self.newspaper_name}_{formatted_date}_{page_num}.gif"
                image_path = os.path.join(date_folder, file_name)

                with open(image_path, "wb") as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                print(f"Downloaded: {image_path}")

                self.convert_gif_to_pdf(
                    image_path, page_num, date_folder, formatted_date
                )

                os.remove(image_path)
                print(f"Deleted original GIF: {image_path}")

                return True
            else:
                print(
                    f"Failed to download {img_url}, status code: {response.status_code}"
                )
                return False
        except Exception as e:
            print(f"Error downloading {img_url}: {str(e)}")
            return False

    def convert_gif_to_pdf(self, image_path, page_num, date_folder, formatted_date):
        try:
            pdf_filename = (f"{self.newspaper_name}_{formatted_date}_page_{page_num}.pdf")
            pdf_path = os.path.join(date_folder, pdf_filename)

            img = Image.open(image_path).convert("RGB")
            img.save(pdf_path)
            print(f"Converted to PDF: {pdf_path}")
            return pdf_path
        except Exception as e:
            print(f"Error converting GIF to PDF: {str(e)}")
            return None

    def get_page_image_urls(self, page_url):
        try:
            response = requests.get(page_url)
            if response.status_code != 200:
                print(
                    f"Failed to fetch page {page_url}, status code: {response.status_code}"
                )
                return []

            soup = BeautifulSoup(response.text, "html.parser")

            images = []

            main_img = soup.select_one('img[src*="main.gif"]')
            if main_img and "src" in main_img.attrs:
                img_url = urljoin(page_url, main_img["src"])
                images.append(img_url)

            if not images:
                for img in soup.find_all("img"):
                    if "src" in img.attrs and img["src"].endswith(".gif"):
                        img_url = urljoin(page_url, img["src"])
                        images.append(img_url)

            return images
        except Exception as e:
            print(f"Error fetching images from {page_url}: {str(e)}")
            return []

    def get_page_links(self, date):
        """Extract all page links from the e-paper index"""
        try:
            date_format = date.strftime("%d%m%Y")
            url = f"{self.base_url}{date_format}/index.php"
            print(f"Processing URL: {url}")
            response = requests.get(url)
            if response.status_code != 200:
                print(f"Failed to get page: {url}")
                return []

            soup = BeautifulSoup(response.text, "html.parser")

            page_links = []
            div_soup = soup.find("ul", attrs={"id": "flexiselDemo3"})
            for link in div_soup.find_all("a", href=True):
                full_url = link.get("href")
                if full_url not in page_links:
                    page_links.append(full_url)

            return page_links

        except Exception as e:
            print(f"Error extracting page links: {str(e)}")
            return [], None, None

    def crawl_newspaper(self):
        date = datetime.now().date()

        page_links = self.get_page_links(date)

        if not page_links:
            print(f"No pages found date: {date}")
            return False

        for i, page_url in enumerate(page_links, 1):
            print(f"Processing page {i}/{len(page_links)}: {page_url}")

            page_match = re.search(r"page(\d+)\.php", page_url)
            if page_match:
                page_num = int(page_match.group(1))
            elif "index.php" in page_url:
                page_num = 1
            else:
                page_num = i

            image_urls = self.get_page_image_urls(page_url)

            if not image_urls:
                print(f"No images found on page {page_url}")
                continue
            formatted_date = date.strftime("%Y_%m_%d")
            date_folder = self.create_date_folder()
            for img_url in image_urls:
                success = self.download_image(
                    img_url, page_num, date_folder, formatted_date
                )
        return True


if __name__ == "__main__":
    crawler = NiyomiyaBartaCrawler()
    status = crawler.crawl_newspaper()
    if status:
        print("Process Complete")
    else:
        print("Process Failed")
