import logging
import os
import re
import shutil
import time
import traceback
from datetime import datetime

from PIL import Image
from playwright.sync_api import sync_playwright


class NewspaperDownloader:
    def __init__(self):
        self.setup_logging()
        self.today_date = datetime.now().strftime("%Y-%m-%d")
        self.today = datetime.strptime(self.today_date, "%Y-%m-%d").strftime(
            "%Y_%m_%d")
        self.edition_name = "ahmedabad"

        self.pages_dir, self.output_dir = self.create_directories()
        self.crop_box = (300, 360, 2680, 4100)  # Default crop coordinates

    @staticmethod
    def setup_logging():
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s"
        )

    def create_directories(self):

        base_dir = os.path.join("downloads","nav_gujarat_samay")

        pages_dir = os.path.join(base_dir, self.edition_name)  # raw full-page
        # screenshots
        output_dir = os.path.join(base_dir,
                                  self.edition_name)  # for cropped images + PDF

        os.makedirs(pages_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        return pages_dir, output_dir

    def wait_for_full_scroll_load(self, page, page_number,
                                  max_scroll_attempts=10, scroll_step=1000):
        prev_height = -1
        attempt = 0

        while attempt < max_scroll_attempts:
            current_height = page.evaluate(
                "() => document.documentElement.scrollHeight")
            logging.info(
                f"[Page {page_number}] Scroll Attempt {attempt + 1} - Height: {current_height}")

            if current_height == prev_height:
                logging.info(
                    f"[Page {page_number}] No more content detected. Stopping scroll.")
                break

            prev_height = current_height

            for pos in range(0, current_height, scroll_step):
                page.evaluate(f"window.scrollTo(0, {pos})")
                time.sleep(1)

            page.evaluate(f"window.scrollTo(0, {current_height})")
            time.sleep(0.5)
            attempt += 1

    def save_images_from_viewer(self, page, page_number):
        screenshot_path = os.path.join(self.pages_dir,
                                       f"{self.edition_name}_{self.today}_page_{page_number}.png")
        logging.info(f"🔄 Processing page {page_number}")

        try:
            zoom_button = page.wait_for_selector("button.zoomin", timeout=5000)
            for _ in range(3):
                zoom_button.click()
                logging.info("🔍 Zoomed in")
            time.sleep(3)
        except Exception as e:
            logging.warning(f"Zoom failed: {e}")

        try:
            page.wait_for_selector("#de-page-container", state="visible",
                                   timeout=15000)
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(1)

            self.wait_for_full_scroll_load(page, page_number)
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(1)

            # Hide overlays
            page.evaluate("""() => {
                document.querySelectorAll(
                    '.clipbtn, .toolbar, .header, .footer, .ad-container, #page-level-nav'
                ).forEach(el => el.style.display = 'none');
            }""")

            page.screenshot(path=screenshot_path, full_page=True, type="png",
                            omit_background=True)
            logging.info(f"✅ Saved full-page screenshot: {screenshot_path}")

            try:
                self.zoom_out_if_visible(page)
            except Exception as e:
                logging.warning(f"Zoom out failed: {e}")

            # self.download_clips_from_sidebar(page,page_number)  # ✅ <-- Inserted here


        except Exception as e:
            logging.error(
                f"❌ Error on page {page_number}: {e}\n{traceback.format_exc()}")

        finally:
            page.evaluate("""() => {
                document.querySelectorAll(
                    '.clipbtn, .toolbar, .header, .footer, .ad-container, #page-level-nav'
                ).forEach(el => el.style.display = '');
            }""")

    def zoom_out_if_visible(self, page):
        try:
            # Restore visibility of hidden elements
            page.evaluate("""() => {
                document.querySelectorAll(
                    '.clipbtn, .toolbar, .header, .footer, .ad-container, #page-level-nav'
                ).forEach(el => el.style.display = '');
            }""")

            zoom_out_btn = page.query_selector("button.zoomout")

            if not zoom_out_btn:
                logging.warning("⚠️ Zoom Out button not found.")
                return

            # Check visibility and enable state
            is_visible = page.evaluate("(el) => el.offsetParent !== null",
                                       zoom_out_btn)
            is_disabled = page.evaluate(
                "(el) => el.classList.contains('disablebtn')", zoom_out_btn)

            # If not visible, try hiding overlays and check again
            if not is_visible:
                logging.info(
                    "🔍 Zoom Out button not visible — hiding overlays to reveal it...")
                page.evaluate("""() => {
                    document.querySelectorAll(
                        '.clipbtn, .toolbar, .header, .footer, .ad-container, #page-level-nav'
                    ).forEach(el => el.style.display = 'none');
                }""")
                time.sleep(1)
                is_visible = page.evaluate("(el) => el.offsetParent !== null",
                                           zoom_out_btn)

            if not is_visible:
                logging.warning(
                    "⚠️ Zoom Out button is still not visible after hiding overlays.")
                return

            if is_disabled:
                logging.warning("⚠️ Zoom Out button is disabled.")
                return

            # All checks passed, click the button
            logging.info("🔍 Zooming out...")
            zoom_out_btn.click()
            time.sleep(1)

        except Exception as e:
            logging.warning(f"⚠️ Zoom out failed: {e}")

    def crop_all_images(self):
        """Crop all image files in the pages directory"""
        logging.info(f"✂️ Starting cropping of images in: {self.pages_dir}")

        try:
            image_files = [f for f in os.listdir(self.pages_dir)
                           if f.lower().endswith(('.png', '.jpg'))]

            for image_file in image_files:
                image_path = os.path.join(self.pages_dir, image_file)
                try:
                    with Image.open(image_path) as img:
                        cropped = img.crop(self.crop_box)
                        cropped.save(image_path)
                        logging.info(f"✂️ Cropped and saved: {image_path}")
                except Exception as crop_err:
                    logging.error(
                        f"❌ Failed to crop {image_file}: {crop_err}\n{traceback.format_exc()}")

        except Exception as e:
            logging.error(
                f"❌ Error processing directory {self.pages_dir}: {e}\n{traceback.format_exc()}")

    @staticmethod
    def natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower()
                for text in re.split(r'(\d+)', s)]

    def download_newspaper(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                java_script_enabled=True
            )
            page = context.new_page()

            try:
                self.navigate_to_newspaper(page)
                current_page = 1
                max_pages = 20

                while current_page <= max_pages:
                    self.process_page(page, current_page)

                    if not self.navigate_to_next_page(page, current_page):
                        break

                    current_page += 1

            finally:
                context.close()
                browser.close()

        self.post_processing()

    def navigate_to_newspaper(self, page):
        page.goto("https://epaper.navgujaratsamay.com/", timeout=60000)
        logging.info("✅ Main page loaded")
        page.wait_for_selector("div.papr-img", timeout=10000)
        page.click("div.papr-img >> nth=0")
        time.sleep(3)

    def process_page(self, page, page_number):
        self.wait_for_full_scroll_load(page, page_number)
        self.save_images_from_viewer(page, page_number)
        # self.download_clips_from_sidebar(page,page_number)  # ✅ <-- Inserted here

    def navigate_to_next_page(self, page, current_page):
        retry_count = 0
        while retry_count < 3:
            try:
                next_btn = page.wait_for_selector(
                    "button.nextpage:not([disabled])",
                    timeout=10000
                )
                next_btn.scroll_into_view_if_needed()
                time.sleep(1)
                next_btn.click(timeout=5000)
                time.sleep(3)

                new_page_num = page.evaluate("""() => {
                    const match = window.location.href.match(/page\/(\d+)/);
                    return match ? parseInt(match[1]) : 0;
                }""")

                if new_page_num > current_page:
                    logging.info(f"➡️ Navigated to page {new_page_num}")
                    return True

                retry_count += 1
                logging.info("↩️ Retrying same page")
                time.sleep(2)

            except Exception as e:
                logging.warning(f"Navigation failed: {e}")
                retry_count += 1
                time.sleep(2)

        logging.warning("📌 Stuck on same page after multiple retries")
        return False

    def post_processing(self):
        # Crop all images first
        self.crop_all_images()

        # Move cropped images from Pages to edition folder
        try:
            # Get all cropped images from the Pages directory
            image_files = [f for f in os.listdir(self.pages_dir)
                           if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

            for image_file in image_files:
                # Move cropped image to edition_name folder
                src_path = os.path.join(self.pages_dir, image_file)
                dst_path = os.path.join(self.output_dir, image_file)
                os.rename(src_path, dst_path)
                logging.info(
                    f"✅ Moved cropped image {image_file} to {dst_path}")

        except Exception as e:
            logging.error(f"❌ Failed to move cropped images: {e}")

        # Remove the Pages directory after everything is done
        try:
            shutil.rmtree(self.pages_dir)
            logging.info(
                f"✅ Successfully deleted Pages directory: {self.pages_dir}")
        except Exception as e:
            logging.error(
                f"❌ Failed to delete Pages directory: {self.pages_dir} - {e}")


if __name__ == "__main__":
    downloader = NewspaperDownloader()
    downloader.download_newspaper()