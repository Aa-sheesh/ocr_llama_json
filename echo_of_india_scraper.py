import requests
from datetime import datetime
import os
from bs4 import BeautifulSoup
from PyPDF2 import PdfMerger


class TheEchoOfIndiaCrawler:
    def __init__(self):
        self.base_url = "http://www.echoofindia.com/ePaper/index.aspx?page=VEVPSQ=="
        self.page_url = (
            "http://www.echoofindia.com/WebService/Master.asmx/GetPdfDocument"
        )
        self.pdf_download_url = "http://www.echoofindia.com/Documents/PDF/"
        self.newspaper_name = "echo_of_india"
        self.session = requests.Session()
        self.news_paper = "news_paper"
        self.news_page = "news_page"

    def create_folder(self, *paths):
        """Creates a folder hierarchy and returns the final path."""
        folder_path = os.path.join("downloads",self.newspaper_name, *paths)
        os.makedirs(folder_path, exist_ok=True)
        return folder_path

    def merge_pdfs(self,pdf_files, output_path):
        """Merge all PDFs into one and delete individual files"""
        merger = PdfMerger()
        for pdf in pdf_files:
            try:
                merger.append(pdf)
            except Exception as e:
                print(f"Error merging {pdf}: {str(e)}")
                continue

        try:
            merger.write(output_path)
            merger.close()
            print(f"Merged PDF created: {output_path}")

            # Delete individual PDFs
            for pdf in pdf_files:
                try:
                    os.remove(pdf)
                    print(f"Deleted temporary file: {pdf}")
                except Exception as e:
                    print(f"Error deleting {pdf}: {str(e)}")

            return True
        except Exception as e:
            print(f"Error saving merged PDF: {str(e)}")
            return False

    def download_pdf_data(self, page_name_list, date_str, addition_name):
        try:
            # output_folder_paper = self.create_folder(
            #     date_str, addition_name, self.news_paper
            # )
            output_folder_page = self.create_folder(addition_name)

            # merger = PdfMerger()
            for page_name in page_name_list:
                pdf_url = f"{self.pdf_download_url}/{page_name}"
                print(f"Processing pdf_url: {pdf_url}")

                filename = (
                    f"{addition_name}_{date_str}_{page_name.split('_')[-1]}"
                )
                file_path = os.path.join(output_folder_page, filename)
                response = requests.get(pdf_url)
                print(f"News page saved: {file_path}")

                with open(file_path, "wb") as f:
                    f.write(response.content)

                # merger.append(file_path)

            # filename = f"{self.newspaper_name}-{addition_name}-{date_str}.pdf"
            # file_path = os.path.join(output_folder_paper, filename)
            # print(f"News paper saved: {file_path}")
            # merger.write(file_path)
            # merger.close()

            return True

        except Exception as e:
            print(f"Error downloading PDF: {str(e)}")
            return None, None

    def get_page_details(self, addition_id):
        response = requests.post(
            self.page_url, json={"company_key": 1, "edition_key": addition_id}
        )
        if response.status_code == 200:
            return response.json()["d"]
        else:
            return None

    def process_latest_newspaper(self, addition_dict: dict):
        date_str = datetime.now().strftime("%Y_%m_%d")
        for addition_name, addition_id in addition_dict.items():
            print(
                f"Processing | addition_name: {addition_name} | addition_id: {addition_id}"
            )
            page_data_list = self.get_page_details(addition_id=addition_id)
            if not page_data_list:
                print("Page not found")
                continue
            for page_data in page_data_list:
                page_name_list = page_data["PDF_DOCUMENT"].split("|")
                page_name_list = list(filter(None, page_name_list))
                print(f"Found {len(page_name_list)} pages")
                if page_name_list:
                    self.download_pdf_data(
                        page_name_list=page_name_list,
                        date_str=date_str,
                        addition_name=addition_name,
                    )
        return True

    def get_addition_list(self):
        try:
            response = self.session.post(self.base_url)
            soup = BeautifulSoup(response.text, "html.parser")
            addition_dict = {}
            for addition in soup.find("ul", attrs={"id": "edition-ul"}).find_all("li"):
                addition = addition.find("a")
                addition_dict["_".join(addition.get("title").split()).lower()] = addition.get("value")
            return addition_dict
        except Exception as ex:
            return {}


def main():
    crawler = TheEchoOfIndiaCrawler()

    print("Processing latest available newspaper...")
    addition_dict = crawler.get_addition_list()
    print(f"addition_dict = {addition_dict}")
    if not addition_dict:
        print("No addition available")
        exit()
    print(f"{len(addition_dict)} addition found.")

    response = crawler.process_latest_newspaper(addition_dict=addition_dict)

    if response:
        print("News PDF created successfully")
    else:
        print("Failed to process latest newspaper")


if __name__ == "__main__":
    main()
