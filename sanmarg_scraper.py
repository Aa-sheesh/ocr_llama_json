import datetime
import os
import time

from playwright.sync_api import sync_playwright

EMAIL = "Subscriptions@AAIZELTECH.com"
PASSWORD = "A@izel@123"


class SanmargScraper:
    def __init__(self):
        self.base_dir = os.path.join("downloads", "sanmarg")
        self.browser = None
        self.page = None
        self.context = None
        self.edition_name = ""
        self.date_str = self.get_today_date_str()
        self.target_folder = ""

    def get_today_date_str(self):
        return datetime.datetime.now().strftime("%Y_%m_%d")

    def create_directory_structure(self):
        full_path = os.path.join(self.base_dir, self.edition_name)
        os.makedirs(full_path, exist_ok=True)
        self.target_folder = full_path

    def handle_active_session_prompt(self):
        try:
            self.page.wait_for_selector("#btnyes", timeout=5000)
            print(
                "Detected active session prompt. Clicking 'Yes' to continue...")
            self.page.click("#btnyes")
            self.page.wait_for_timeout(3000)
        except Exception:
            print("No active session prompt detected. Continuing normally.")

    def login(self):
        print("Navigating to Sanmarg ePaper...")
        self.page.goto("https://epaper.sanmarg.in")

        print("Waiting for login form...")
        self.page.wait_for_selector("#txtNumber1")
        self.page.fill("#txtNumber1", EMAIL)
        self.page.fill("#txtPassword", PASSWORD)
        self.page.check("#chkSignIn")
        self.page.click("button.btn-custom.btn_login")
        print("Submitted login form.")
        self.page.wait_for_timeout(8000)
        self.handle_active_session_prompt()

    def download_main_edition(self):
        self.page.wait_for_selector("#span_Edition", timeout=10000)
        self.edition_name = self.page.inner_text(
            "#span_Edition").strip().lower()
        print("Edition name:", self.edition_name)

        self.page.wait_for_load_state("load", timeout=120000)
        time.sleep(5)

        print("Waiting for download to start...")
        with self.page.expect_download() as download_info:
            self.page.click("#downloadEditiontoolbar")
        download = download_info.value

        self.create_directory_structure()
        pdf_filename = f"{self.edition_name}_{self.date_str}.pdf"
        full_pdf_path = os.path.join(self.target_folder, pdf_filename)
        download.save_as(full_pdf_path)
        print(f"✅ PDF downloaded successfully at: {full_pdf_path}")

    def switch_to_article_view(self):
        try:
            print("Switching to Page List View...")
            self.page.wait_for_selector("#lnkarticle", timeout=10000)
            self.page.click("#lnkarticle")
            print("✅ Successfully switched to Page List View.")
        except Exception as e:
            print("❌ Failed to switch to Page List View:", e)

    def scrape_article_clips(self):
        try:
            self.page.wait_for_selector(
                "div.col_sidebar ul#UlPages li.has-sub.active ul.pg_thumb li",
                timeout=15000
            )
            thumbnails = self.page.query_selector_all(
                "div.col_sidebar ul#UlPages li.has-sub.active ul.pg_thumb li div.pg_thumb_main_div img"
            )
            print(f"Found {len(thumbnails)} page thumbnails.")

            for i, thumb in enumerate(thumbnails):
                page_number = i + 1
                try:
                    print(f"Clicking page thumbnail {page_number}...")
                    thumb.scroll_into_view_if_needed()
                    thumb.click()
                    self.page.wait_for_timeout(3000)

                    articles = self.page.query_selector_all(
                        '#ImageContainer .pagerectangle')
                    print(
                        f"Found {len(articles)} articles on page {page_number}.")

                    for j, article in enumerate(articles):
                        article_number = j + 1
                        try:
                            article.scroll_into_view_if_needed()

                            self.page.evaluate('''(element) => {
                                element.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
                                element.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                            }''', article)

                            self.page.wait_for_load_state('load',
                                                          timeout=60000)

                            download_button = self.page.wait_for_selector(
                                '#downloadImage', timeout=10000)
                            if download_button:
                                download_button.scroll_into_view_if_needed()
                                download_button.evaluate('btn => btn.click()')
                                download = self.page.wait_for_event('download')

                                clip_name = f"{self.edition_name}_{self.date_str}_page_{page_number}_clip_{article_number}.png"
                                clip_path = os.path.join(self.target_folder,
                                                         clip_name)
                                download.save_as(clip_path)
                                print(f"Saved article clip: {clip_path}")

                        except Exception as e:
                            print(
                                f"  !! Could not click article {article_number} on page {page_number}: {e}")

                except Exception as e:
                    print(
                        f"!! Error clicking page thumbnail {page_number}: {e}")

        except Exception as e:
            print(f"!! Error iterating page thumbnails or articles: {e}")

    def run(self):
        with sync_playwright() as p:
            self.browser = p.chromium.launch(headless=True)
            self.context = self.browser.new_context(accept_downloads=True)
            self.page = self.context.new_page()

            try:
                self.login()
                self.download_main_edition()
                # self.switch_to_article_view()
                # self.scrape_article_clips()
            finally:
                self.browser.close()


if __name__ == "__main__":
    scraper = SanmargScraper()
    scraper.run()
