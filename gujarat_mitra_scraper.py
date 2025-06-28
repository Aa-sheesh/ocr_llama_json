"""
Single Page Multiple PDFs
"""
import datetime
import os
import urllib.parse

import requests
from bs4 import BeautifulSoup


class GujaratMitraCrawler:
    def __init__(self, base_url="https://epaper.gujaratmitra.in/"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })

    @staticmethod
    def create_date_folder(section):
        folder_path = os.path.join("downloads","gujarat_mitra", section)
        os.makedirs(folder_path, exist_ok=True)
        return folder_path

    def get_states_and_ids(self):
        response = self.session.get(self.base_url)
        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.find_all("article")
        results = []

        for article in articles:
            link_tag = article.find("a", href=True)
            img_tag = article.find("img", src=True)
            category_tag = article.find("li", class_="article-category")

            if link_tag and img_tag and category_tag:
                href = link_tag["href"]
                query = dict(
                    urllib.parse.parse_qsl(urllib.parse.urlsplit(href).query))
                result = {
                    "section": category_tag.get_text(strip=True).replace('/',
                                                                         '-').replace(
                        ' ', '-'),
                    "date": query.get("d"),
                    "link": self.base_url + href.
                    replace('edview.php', 'preview1.php').
                    replace(' ', '%20'),
                }
                results.append(result)

        today = datetime.date.today().isoformat()
        return [item for item in results if item["date"] == today][:4]

    def download_single_page(self, page_url, section, page_number,
                             folder_path, date):
        resp = self.session.get(page_url)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        download_btn = soup.select_one("a[href$='.pdf']")
        if not download_btn:
            return None

        pdf_url = urllib.parse.urljoin(self.base_url, download_btn['href'])
        pdf_name = f"{section}{date}{page_number}.pdf"
        pdf_path = os.path.join(folder_path, pdf_name)

        file_resp = self.session.get(pdf_url)
        if file_resp.status_code == 200:
            with open(pdf_path, 'wb') as f:
                f.write(file_resp.content)
            print(f"Downloaded {pdf_name}")
            return pdf_path

        print(f"Failed to download page {page_number} for {section}")
        return None

    def download_section_pdfs(self, filtered_papers):
        for paper in filtered_papers:
            section = paper['section'].lower().replace("-", "_").replace(".",
                                                                         "")
            date = paper['date'].replace("-", "_")
            base_link = paper['link']
            folder_path = self.create_date_folder(section)

            page_number = 1
            downloaded_files = []

            while True:
                page_url = base_link.replace('&p=1', f'&p={page_number}')
                pdf_path = self.download_single_page(page_url, section,
                                                     page_number, folder_path,
                                                     date)
                if not pdf_path:
                    break
                downloaded_files.append(pdf_path)
                page_number += 1

    def process_newspapers(self):
        filtered_papers = self.get_states_and_ids()
        if not filtered_papers:
            print("No states found on main page. Exiting.")
            return

        self.download_section_pdfs(filtered_papers)


def main():
    crawler = GujaratMitraCrawler()
    crawler.process_newspapers()


if __name__ == "__main__":
    main()
