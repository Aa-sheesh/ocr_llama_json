import datetime
import os
import time
from urllib.parse import urlparse, parse_qs

import requests
from playwright.sync_api import sync_playwright


class NewspaperDownloader:
    def __init__(self, api_key, edition_name="hyderabad"):
        self.api_key = api_key
        self.today = datetime.datetime.today().strftime('%Y_%m_%d')
        self.edition_name = edition_name
        self.base_url = "https://epaper.v6velugu.com/"
        self.site_key = None
        self.token = None
        self.page = None
        self.browser = None

    def solve_recaptcha_with_2captcha(self, site_key, url):
        """Solve the reCAPTCHA using 2Captcha service."""
        print("Sending reCAPTCHA to 2Captcha...")
        response = requests.post("http://2captcha.com/in.php", data={
            'key': self.api_key,
            'method': 'userrecaptcha',
            'googlekey': site_key,
            'pageurl': url,
            'json': 1
        }).json()

        if response.get("status") != 1:
            print("2Captcha submission failed:", response)
            return None

        captcha_id = response["request"]
        print("Captcha ID:", captcha_id)

        print("Waiting for CAPTCHA solution...")
        for _ in range(24):  # Wait up to 2 minutes
            time.sleep(5)
            res = requests.get("http://2captcha.com/res.php", params={
                'key': self.api_key,
                'action': 'get',
                'id': captcha_id,
                'json': 1
            }).json()
            if res.get("status") == 1:
                print("CAPTCHA solved.")
                return res["request"]

        print("Failed to get CAPTCHA solution in time.")
        return None

    def initialize_browser(self):
        """Initialize the browser and page."""
        self.browser = sync_playwright().start().chromium.launch(
            headless=True)
        self.page = self.browser.new_page()

    def navigate_to_newspaper(self):
        """Navigate to the epaper and handle page loading."""
        self.page.goto(self.base_url)
        self.page.wait_for_load_state("networkidle")

        hyderabad_main_link = self.page.query_selector(
            'a:text("Hyderabad Main")')
        if not hyderabad_main_link:
            print("Hyderabad Main link not found")
            return False
        hyderabad_main_link.click()
        self.page.wait_for_load_state("load")
        return True

    def download_paper(self):
        """Download the newspaper PDF."""
        image_element = self.page.query_selector('div.papr-img > amp-img')
        if not image_element:
            print("Newspaper image not found")
            return False
        image_element.click()
        self.page.wait_for_load_state("load")

        download_button = self.page.query_selector(
            'div#epaper-box > a.btn.btn-default.btn-sm.download-pdf')
        if not download_button:
            print("Download button not found")
            return False
        download_button.click()
        time.sleep(5)

        return True

    def handle_recaptcha(self):
        """Handle reCAPTCHA and return the token."""
        print("Waiting for reCAPTCHA to load...")
        for _ in range(30):
            iframe = self.page.query_selector('iframe[src*="api2/anchor"]')
            if iframe:
                src = iframe.get_attribute("src")
                parsed = urlparse(src)
                self.site_key = parse_qs(parsed.query).get("k", [None])[0]
                if self.site_key:
                    break
            time.sleep(1)

        if not self.site_key:
            print("Could not extract sitekey.")
            return False

        print(f"Extracted sitekey: {self.site_key}")
        self.token = self.solve_recaptcha_with_2captcha(self.site_key,
                                                        self.page.url)
        if not self.token:
            print("Failed to solve CAPTCHA.")
            return False

        print("Injecting token into DOM...")
        self.page.evaluate(f'''
            document.getElementById("g-recaptcha-response").value = "{self.token}";
            const event = new Event('change', {{ bubbles: true }});
            document.getElementById("g-recaptcha-response").dispatchEvent(event);
        ''')

        # Find and execute reCAPTCHA callback
        callback_name = self.page.evaluate('''() => {
                            const recaptchaDiv = document.querySelector('.g-recaptcha');
                            return recaptchaDiv ? recaptchaDiv.getAttribute('data-callback') : null;
                        }''')

        if callback_name:
            print(f"Triggering reCAPTCHA callback: {callback_name}")
            self.page.evaluate(f'''() => {{
                                if (window.{callback_name}) {{
                                    window.{callback_name}("{self.token}");
                                }}
                            }}''')
        else:
            print("No reCAPTCHA callback found")

        return True

    def handle_download_modal(self):
        """Handle the modal that appears after clicking download."""
        print("Waiting for download link...")
        download_link = self.page.wait_for_selector(
            'a.fullpdflink.log-btn:has-text("Download full Newspaper")',
            state="visible",
            timeout=60000
        )

        with self.page.expect_download() as download_info:
            download_link.click()

            # Wait for the modal to appear with the "I Accept" button
            accept_button = self.page.wait_for_selector(
                'button.btn-success.bootbox-accept', timeout=5000)
            if not accept_button:
                print("Accept button not found in modal")
                return None

            # Click the "I Accept" button
            accept_button.click()
        return download_info.value

    def save_pdf(self, download):
        """Save the downloaded PDF to the specified location."""
        output_dir = os.path.join("downloads", "velugu")
        os.makedirs(output_dir, exist_ok=True)
        file_path = f"{output_dir}/{self.edition_name}/{self.edition_name}_{self.today}.pdf"
        download.save_as(file_path)
        print(f"PDF downloaded to: {file_path}")

    def close_browser(self):
        """Close the browser."""
        if self.browser:
            self.browser.close()

    def download_newspaper(self):
        """Main function to download the newspaper."""
        try:
            self.initialize_browser()
            if not self.navigate_to_newspaper():
                return
            if not self.download_paper():
                return
            if not self.handle_recaptcha():
                return
            download = self.handle_download_modal()
            if download:
                self.save_pdf(download)
        except Exception as e:
            print("Error during download:", e)
        finally:
            self.close_browser()


# Usage
API_KEY = "bd9495e9ce0b356f189274f82089e7a7"
downloader = NewspaperDownloader(API_KEY)
downloader.download_newspaper()
