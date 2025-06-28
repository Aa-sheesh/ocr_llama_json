import logging
import os
import re
import shutil
import time
import traceback
from datetime import datetime

from PIL import Image
from fpdf import FPDF
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


class NewspaperDownloader:
    # ───────────────────────── SET-UP ────────────────────────── #
    def __init__(self):
        self.setup_logging()

        # Publication slug used everywhere in filenames/folders
        self.publication_name = "ahmedabad_mirror"
        self.edition_name = "ahmedabad"

        # Dates
        self.today_date = datetime.now().strftime("%Y-%m-%d")      # 2025-06-04
        self.today = datetime.strptime(self.today_date, "%Y-%m-%d").strftime("%Y_%m_%d")  # 2025_06_04

        # Create folder hierarchy
        self.output_dir = self.create_directories()
        self.pages_dir = self.output_dir  # Use same path for saving pages

        # Crop box tuned for this paper (adjust if needed)
        self.crop_box = (300, 350, 1700, 2540)

    # ───────────────────────── UTILITIES ─────────────────────── #
    @staticmethod
    def setup_logging():
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s"
        )

    def create_directories(self):
        """
        ahmedabad_mirror/ahmedabad/
            *.png       ← cropped pages + clips
            *.pdf
        """
        output_dir = os.path.join('downloads', self.publication_name, self.edition_name)
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    # ───────────────────────── PAGE LOAD ─────────────────────── #
    def wait_for_full_scroll_load(self, page, page_number,
                                  max_scroll_attempts=10, scroll_step=1000):
        prev_height = -1
        attempt = 0

        while attempt < max_scroll_attempts:
            current_height = page.evaluate("() => document.documentElement.scrollHeight")
            logging.info(f"[Page {page_number}] Scroll Attempt {attempt + 1} – Height: {current_height}")

            if current_height == prev_height:
                logging.info(f"[Page {page_number}] No more content detected. Stopping scroll.")
                break

            prev_height = current_height
            for pos in range(0, current_height, scroll_step):
                page.evaluate(f"window.scrollTo(0, {pos})")
                time.sleep(0.4)

            page.evaluate(f"window.scrollTo(0, {current_height})")
            time.sleep(0.5)
            attempt += 1

    # ───────────────────────── SCREENSHOTS ───────────────────── #
    def save_images_from_viewer(self, page, page_number):
        screenshot_path = os.path.join(
            self.pages_dir,
            f"{self.publication_name}{self.today}_page_{page_number}.png"
        )
        logging.info(f"🔄 Processing page {page_number}")

        try:
            # Attempt to zoom in twice
            try:
                zoom_button = page.wait_for_selector("button.zoomin", timeout=5000)
                zoom_button.click()
                time.sleep(1)  # short delay between zooms
                zoom_button.click()
                logging.info("🔍 Zoomed in twice")
                time.sleep(3)
            except Exception as e:
                logging.warning(f"Zoom failed: {e}")

            # Ensure page container is visible
            page.wait_for_selector("#de-page-container", state="visible", timeout=15000)
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(1)

            # Scroll entire page to force lazy-load of images
            self.wait_for_full_scroll_load(page, page_number)
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(1)

            # Hide overlays before taking screenshot
            page.evaluate("""() => {
                document.querySelectorAll(
                    '.clipbtn, .toolbar, .header, .footer, .ad-container, #page-level-nav'
                ).forEach(el => el.style.display = 'none');
            }""")

            # Full-page screenshot
            page.screenshot(path=screenshot_path, full_page=True, type="png", omit_background=True)
            logging.info(f"✅ Saved full-page screenshot: {screenshot_path}")

            # Restore zoom
            try:
                self.zoom_out_if_visible(page)
            except Exception as e:
                logging.warning(f"Zoom out failed: {e}")

            # 🛑 Clip downloads removed intentionally

        except Exception as e:
            logging.error(f"❌ Error on page {page_number}: {e}\n{traceback.format_exc()}")

        finally:
            # Unhide overlays after capture
            page.evaluate("""() => {
                document.querySelectorAll(
                    '.clipbtn, .toolbar, .header, .footer, .ad-container, #page-level-nav'
                ).forEach(el => el.style.display = '');
            }""")


    def zoom_out_if_visible(self, page):
        try:
            zoom_out_btn = page.query_selector("button.zoomout")
            if not zoom_out_btn:
                logging.warning("⚠️ Zoom Out button not found.")
                return

            is_visible = page.evaluate("(el) => el.offsetParent !== null", zoom_out_btn)
            is_disabled = page.evaluate("(el) => el.classList.contains('disablebtn')", zoom_out_btn)

            if not is_visible:
                page.evaluate("""() => {
                    document.querySelectorAll(
                        '.clipbtn, .toolbar, .header, .footer, .ad-container, #page-level-nav'
                    ).forEach(el => el.style.display = 'none');
                }""")
                time.sleep(1)
                is_visible = page.evaluate("(el) => el.offsetParent !== null", zoom_out_btn)

            if not is_visible or is_disabled:
                logging.warning("⚠️ Zoom Out button not usable.")
                return

            logging.info("🔍 Zooming out…")
            zoom_out_btn.click()
            time.sleep(1)
        except Exception as e:
            logging.warning(f"⚠️ Zoom out failed: {e}")

    # ───────────────────────── CLIPS ─────────────────────────── #
    def download_clips_from_sidebar(self, page, page_number):
        logging.info(f"🔍 Fetching clips for page {page_number}…")

        self._show_clips_panel(page)
        self._activate_clips_tab(page)

        clip_links = page.query_selector_all("#page-thumbs.clips.pageclips a")
        total_clips = len(clip_links)

        if total_clips == 0:
            logging.info(f"ℹ️ No clips found on page {page_number}")
            return

        logging.info(f"🧾 Found {total_clips} clips on page {page_number}")

        for idx in range(total_clips):
            try:
                self._download_single_clip(page, page_number, idx)
            except PlaywrightTimeoutError as te:
                logging.warning(f"⚠️ Timeout processing clip {idx + 1} on page {page_number}: {te}")
                self._close_modal_safe(page)
            except Exception as e:
                logging.error(f"❌ Error processing clip {idx + 1} on page {page_number}: {e}")
                self._close_modal_safe(page)

    def _show_clips_panel(self, page):
        page.evaluate("""() => {
            const panel = document.querySelector('#page-left-panel');
            if (panel) panel.style.visibility = 'visible';
        }""")

    def _activate_clips_tab(self, page):
        clips_tab_selector = "#left-panel-topclips a"
        page.wait_for_selector(clips_tab_selector, timeout=5000)
        page.click(clips_tab_selector, force=True)
        time.sleep(2)

    def _download_single_clip(self, page, page_number, idx):
        clip_links = page.query_selector_all("#page-thumbs.clips.pageclips a")
        if idx >= len(clip_links):
            return

        logging.info(f"🖱 Clicking clip {idx + 1} on page {page_number}")
        clip_links[idx].click()
        page.wait_for_selector("#modal-bg", timeout=10000)
        time.sleep(2)

        page.wait_for_selector(".clipactions a.downloadclip:visible", timeout=10000)
        download_buttons = [btn for btn in page.query_selector_all(".clipactions a.downloadclip") if btn.is_visible()]
        if not download_buttons:
            logging.warning("No visible download buttons found")
            self._close_modal_safe(page)
            return

        download_btn = download_buttons[0]
        logging.info(f"⬇️ Downloading clip {idx + 1} on page {page_number}")
        with page.expect_download() as download_info:
            download_btn.click()

        download = download_info.value
        clip_filename = f"{self.publication_name}{self.today}_page_{page_number}_clip_{idx + 1}.png"
        clip_path = os.path.join(self.output_dir, clip_filename)
        download.save_as(clip_path)
        logging.info(f"✅ Clip {idx + 1} saved as {clip_filename}")

        self._close_modal_safe(page)

        # Ensure sidebar stays visible for next clip
        page.evaluate("""() => {
            const panel = document.querySelector('#page-left-panel');
            if (panel) panel.style.visibility = 'visible';
        }""")
        time.sleep(1)

    def _close_modal_safe(self, page):
        try:
            close_btn = page.query_selector("#modal-close-btn")
            close_btn.click() if close_btn else page.keyboard.press("Escape")
            page.wait_for_selector("#modal-bg", state="hidden", timeout=5000)
        except Exception:
            pass

    # ───────────────────────── NAVIGATION ────────────────────── #
    def navigate_to_newspaper(self, page):
        page.goto("https://epaper.ahmedabadmirror.com/", timeout=60000)
        logging.info("✅ Main page loaded")
        page.wait_for_selector("div.papr-img", timeout=10000)
        page.click("div.papr-img >> nth=0")
        time.sleep(3)

    def process_page(self, page, page_number):
        self.wait_for_full_scroll_load(page, page_number)
        self.save_images_from_viewer(page, page_number)

    def navigate_to_next_page(self, page, current_page):
        retry_count = 0
        while retry_count < 3:
            try:
                next_btn = page.wait_for_selector("button.nextpage:not([disabled])", timeout=10000)
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

    # ───────────────────────── POST-PROCESS ──────────────────── #
    def crop_all_images(self):
        logging.info(f"✂️ Starting cropping of images in: {self.pages_dir}")
        image_files = [f for f in os.listdir(self.pages_dir) if f.lower().endswith(('.png', '.jpg'))]

        for image_file in image_files:
            image_path = os.path.join(self.pages_dir, image_file)
            try:
                with Image.open(image_path) as img:
                    cropped = img.crop(self.crop_box)
                    cropped.save(image_path)
                    logging.info(f"✂️ Cropped and saved: {image_path}")
            except Exception as crop_err:
                logging.error(f"❌ Failed to crop {image_file}: {crop_err}\n{traceback.format_exc()}")

    @staticmethod
    def natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

    def create_pdf(self):
        logging.info("📄 Creating PDF…")
        pdf = FPDF(unit="mm", format="A4")
        a4_width, a4_height = 210, 297

        images = [f for f in os.listdir(self.pages_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        images.sort(key=self.natural_sort_key)

        for image_file in images:
            image_path = os.path.join(self.pages_dir, image_file)
            with Image.open(image_path) as img:
                img_width, img_height = img.size
                aspect = img_width / img_height

                if a4_width / a4_height > aspect:
                    h = a4_height
                    w = h * aspect
                else:
                    w = a4_width
                    h = w / aspect

                x = (a4_width - w) / 2
                y = (a4_height - h) / 2
                pdf.add_page()
                pdf.image(image_path, x=x, y=y, w=w, h=h)

        pdf_output_path = os.path.join(self.output_dir, f"{self.today}_{self.publication_name}.pdf")
        pdf.output(pdf_output_path)
        logging.info(f"✅ PDF created: {pdf_output_path}")

        return pdf_output_path

    # ───────────────────────── MAIN FLOW ─────────────────────── #
    def download_newspaper(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1920, "height": 1080}, java_script_enabled=True)
            page = context.new_page()

            try:
                self.navigate_to_newspaper(page)
                current_page = 1
                max_pages = 20  # adjust if you need more

                while current_page <= max_pages:
                    self.process_page(page, current_page)

                    if not self.navigate_to_next_page(page, current_page):
                        break

                    current_page += 1

            finally:
                context.close()
                browser.close()

        self.post_processing()

    def post_processing(self):
        self.crop_all_images()
        pdf_output_path = self.create_pdf()

        # Move cropped images (now ready) to main folder and delete Pages/
        try:
            image_files = [f for f in os.listdir(self.pages_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            for image_file in image_files:
                src_path = os.path.join(self.pages_dir, image_file)
                dst_path = os.path.join(self.output_dir, image_file)
                os.rename(src_path, dst_path)
                logging.info(f"✅ Moved cropped image {image_file} → {dst_path}")
        except Exception as e:
            logging.error(f"❌ Failed to move cropped images: {e}")

        try:
            os.remove(pdf_output_path)
            logging.info(f"✅ Removed E-Paper PDF at: {pdf_output_path}")
        except Exception as e:
            logging.error(f"❌ Failed to delete E-Paper PDF: {e}")


# ───────────────────────── ENTRY POINT ───────────────────────── #
if __name__ == "__main__":
    NewspaperDownloader().download_newspaper()

