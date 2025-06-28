import datetime
import os
import time

import requests
from playwright.sync_api import sync_playwright


class HitavadaScraper:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.today_date = datetime.datetime.today().strftime('%Y-%m-%d')
        self.formatted_date = datetime.datetime.strptime(self.today_date,
                                                         "%Y-%m-%d").strftime(
            "%Y_%m_%d")
        self.base_dir = os.path.join("downloads", "the_hitavada")

    def close_custom_popup(self, page):
        """Close the custom popup if it appears"""
        try:
            page.wait_for_selector(".custom-popup span", timeout=5000)
            page.click(".custom-popup span")
            print("Custom popup closed.")
        except Exception as e:
            print("No custom popup found or unable to close it:", str(e))

    def download_article_image(self, article_page, page_number, article_index,
                               edition_name):
        """Download the article image from the article page"""
        try:
            article_page.wait_for_selector("#download2", timeout=10000)
            img_url = article_page.locator("#download2").get_attribute('href')

            if img_url:
                full_img_url = img_url if img_url.startswith(
                    "http") else f"https://www.ehitavada.com/{img_url.lstrip('/')}"
                folder_path = os.path.join(self.base_dir, edition_name)
                os.makedirs(folder_path, exist_ok=True)
                file_path = os.path.join(folder_path,
                                         f'{edition_name}_'
                                         f'{self.formatted_date}_page_{page_number}_article_{article_index + 1}.png')

                with requests.get(full_img_url) as response:
                    if response.status_code == 200:
                        with open(file_path, 'wb') as f:
                            f.write(response.content)
                        print(
                            f"✅ Saved article {article_index + 1} image to {file_path}")
                        return True
                    else:
                        print(
                            f"❌ Failed to download article image {article_index + 1}, HTTP status {response.status_code}")
            else:
                print(
                    f"⚠️ No download link found for article {article_index + 1}")
        except Exception as e:
            print(
                f"❌ Error downloading article {article_index + 1} image: {e}")
        return False

    def process_article_page(self, main_page, href, edition_name, page_number,
                             article_index):
        """Process a single article page"""
        article_url = href if href.startswith(
            "http") else f"https://www.ehitavada.com/{href.lstrip('/')}"
        print(f"Opening article {article_index + 1}: {article_url}")

        browser = main_page.context.browser
        context = browser.new_context()
        article_page = context.new_page()

        try:
            article_page.goto(article_url)
            article_page.wait_for_load_state("networkidle")

            # Close custom popup if present
            try:
                article_page.wait_for_selector(".custom-popup span",
                                               timeout=5000)
                article_page.click(".custom-popup span")
                print("Custom popup closed on article page.")
                time.sleep(1)
            except:
                print("No custom popup found on article page.")

            # Download the article image
            self.download_article_image(article_page, page_number,
                                        article_index, edition_name)

        except Exception as e:
            print(f"Error processing article {article_index + 1}: {e}")
        finally:
            article_page.close()
            context.close()

    def download_articles_from_page(self, main_page, edition_name,
                                    page_number):
        """Download all articles from a single page"""
        try:
            main_page.wait_for_selector(
                'img[usemap="#ImageMapContainer"], map#ImageMapContainer',
                state='attached', timeout=60000)
            print("Map element is attached in the DOM!")

            areas = main_page.locator("map#ImageMapContainer area")
            total_areas = areas.count()
            print(f"Found {total_areas} article areas on page {page_number}.")

            for i in range(total_areas):
                href = areas.nth(i).get_attribute('href')
                if href:
                    self.process_article_page(main_page, href, edition_name,
                                              page_number, i)

        except Exception as e:
            print(
                f"❌ Unexpected error in download_articles_from_page for page {page_number}: {e}")

    def download_pdf(self, pdf_url, edition_name):
        """Download a PDF file for a specific edition"""
        base_path = os.path.join(self.base_dir, edition_name)
        os.makedirs(base_path, exist_ok=True)

        page_number = pdf_url.split('_')[-1].split('.')[0]
        filename = (
            f"{edition_name}_{self.formatted_date}_page_{page_number}.pdf")
        file_path = os.path.join(base_path, filename)

        print(f"Downloading PDF from {pdf_url} to {file_path}")
        response = requests.get(pdf_url)

        if response.status_code == 200:
            with open(file_path, 'wb') as file:
                file.write(response.content)
            print(f"Downloaded PDF saved to {file_path}")
            return True
        else:
            print(
                f"Failed to download PDF from {pdf_url}. Status code: {response.status_code}")
            return False

    def process_edition_page(self, page, edition_name, page_index):
        """Process a single page of an edition"""
        try:
            # Get the PDF URL directly from the "href" attribute
            pdf_url = page.locator("#pdf_btn a").get_attribute("href")
            print(f"Downloading page {page_index + 1} from {pdf_url}")

            self.download_pdf(pdf_url, edition_name)

            # if self.download_pdf(pdf_url, edition_name):
            #     # Download all articles from the page after PDF download
            #     self.download_articles_from_page(page, edition_name,
            #                                      page_index + 1)
            return True
        except Exception as e:
            print(f"Error processing edition page {page_index + 1}: {e}")
            return False

    def download_pages_for_edition(self, page, edition_name):
        """Download all pages for a specific edition"""
        page.wait_for_selector(".owl-stage", timeout=10000)
        pages = page.locator(".owl-item")
        page.wait_for_timeout(1000)  # Wait for pages to render

        num_pages = pages.count()
        print(f"Found {num_pages} pages for edition {edition_name}.")

        for i in range(num_pages):
            pages.nth(i).click()
            page.wait_for_selector("#pdf_btn", timeout=10000)
            self.process_edition_page(page, edition_name, i)

    def should_skip_edition(self, edition_name):
        """Determine if an edition should be skipped"""
        edition_list = ["Madhyapardesh Line", "Insight"]
        normalized_list = [name.lower().replace(" ", "_") for name in
                           edition_list]
        return edition_name.lower().replace(" ", "_") in normalized_list

    def scrape_editions(self):
        """Main method to scrape all editions"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                # Step 1: Login
                page.goto("https://www.ehitavada.com/dashboard/login.php")
                page.fill("#login_email", self.username)
                page.fill("#login_pass", self.password)
                page.click("button[onclick='val_login(this)']")
                page.wait_for_load_state('networkidle')
                print("Login completed.")
                self.close_custom_popup(page)

                # Step 2: Process editions
                edition_select = page.locator("#edition_selector")
                editions = edition_select.locator("option")
                num_editions = editions.count()
                print(f"Found {num_editions} editions in the dropdown.")

                for i in range(num_editions):
                    edition_name = "_".join(editions.nth(i).inner_text(

                    ).split()).lower()
                    if self.should_skip_edition(edition_name):
                        print(f"Skipping edition: {edition_name}")
                        continue

                    print(f"Selecting edition: {edition_name}")
                    edition_select.select_option(index=i)
                    page.wait_for_selector(".owl-item", timeout=10000)
                    self.close_custom_popup(page)
                    self.download_pages_for_edition(page, edition_name)

            except Exception as e:
                print(f"Error during scraping: {e}")
            finally:
                browser.close()


# Usage example
if __name__ == "__main__":
    username = "Subscriptions@AAIZELTECH.com"
    password = "A@izel@123"

    scraper = HitavadaScraper(username=username, password=password)
    scraper.scrape_editions()
