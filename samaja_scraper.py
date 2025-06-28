import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from playwright.sync_api import sync_playwright


class SamajaCrawler:
    def __init__(self, base_url: str, output_dir: str = "downloads/samaja"):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self._setup_logging()
        self._create_output_dir()

    def _setup_logging(self):
        self.logger = logging.getLogger("SamajaCrawler")
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)

    def _create_output_dir(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Output directory ready: {self.output_dir}")

    def get_editions(self, page) -> List[Dict[str, str]]:
        """
        Extract list of editions from homepage based on the provided HTML structure.
        Returns a list of dicts: [{'name': edition_name, 'url': edition_url}, ...]
        """
        self.logger.info("Extracting editions from homepage...")
        editions = []
        try:
            # Find all edition containers
            edition_divs = page.query_selector_all('div.col-sm-4.mp-col')
            if not edition_divs:
                self.logger.warning(
                    "No edition containers found with div.col-sm-4.mp-col")

            for div in edition_divs:
                # Extract edition name
                name_span = div.query_selector('span.edspan')
                edition_name = name_span.inner_text().strip() if name_span else None

                # Extract edition url from the first <a> inside this div
                a_tag = div.query_selector('a')
                edition_url = a_tag.get_attribute('href') if a_tag else None

                edition_date = None
                if edition_url:
                    match = re.search(r'\d{4}-\d{2}-\d{2}', edition_url)
                    if match:
                        edition_date = match.group(0)
                        # Optional: Parse and format date (e.g., "May 27, 2025")
                        edition_date = datetime.strptime(edition_date,
                                                         '%Y-%m-%d').strftime(
                            '%B %d, %Y')

                if edition_name and edition_url:
                    editions.append({'name': edition_name, 'url':
                        edition_url, 'date': edition_date
                                     })

            self.logger.info(f"Found {len(editions)} editions.")
        except Exception as e:
            self.logger.error(f"Error extracting editions: {e}")

        return editions

    def get_total_pages(self, page) -> int:
        """
        Determine total pages available for the current edition using page DOM.
        """
        try:
            # Try to get total pages from hidden input
            totalpages_input = page.query_selector('input#totalpages')
            if totalpages_input:
                value = totalpages_input.get_attribute('value')
                if value and value.isdigit():
                    total = int(value)
                    self.logger.info(
                        f"Total pages found from hidden input: {total}")
                    return total

            # Fallback: count options in select#tpgnumber
            options = page.query_selector_all('select#tpgnumber option')
            if options:
                total = len(options)
                self.logger.info(
                    f"Total pages found by counting select options: {total}")
                return total

        except Exception as e:
            self.logger.error(f"Error getting total pages: {e}")

        # Default to 1 page if nothing found
        return 1

    def _create_edition_folder(self, edition_name: str) -> Path:
        date_folder = self.output_dir

        edition_name_clean = edition_name.replace('/', '-').strip()
        edition_folder = date_folder / edition_name_clean.lower()

        edition_folder.mkdir(parents=True, exist_ok=True)
        return edition_folder

    def download_pdf(self, page, page_number: int,
                     edition_folder: Path,date_str) -> bool:
        try:
            date_obj = datetime.strptime(date_str, '%B %d, %Y')
            formatted_date = date_obj.strftime('%Y-%m-%d')

            self.logger.info(f"Downloading PDF for page {page_number}...")
            with page.expect_download() as download_info:
                page.click('span.teIcoImg img[title="Download Page"]')

            download = download_info.value
            save_path = edition_folder / f"samaja_{formatted_date}_{page_number}.pdf"
            download.save_as(save_path)
            self.logger.info(f"PDF saved: {save_path}")
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to download PDF for page {page_number}: {e}")
            return False

    def download_clips(self, page, page_number: int,
                       edition_folder: Path,date_str) -> int:
        """
        Download all clip images for the current page using the onclick attributes of area tags.
        Returns the number of clips downloaded.
        """
        self.logger.info(f"Downloading clips for page {page_number}...")
        clips_downloaded = 0
        date_obj = datetime.strptime(date_str, '%B %d, %Y')
        formatted_date = date_obj.strftime('%Y-%m-%d')

        try:
            # Locate all area elements
            map_name = f"enewspaper{page_number}"
            area_elements = page.query_selector_all(
                f'map[name="{map_name}"] area.borderimage')
            if not area_elements:
                self.logger.warning(
                    f"No clip areas found for page {page_number}")
                return 0

            for idx, area in enumerate(area_elements, start=1):
                onclick_value = area.get_attribute('onclick')
                if not onclick_value:
                    continue

                match = re.search(r"show_pop\('(\d+)','(\d+)','(\d+)'\)",
                                  onclick_value)
                if not match:
                    self.logger.warning(
                        f"Could not parse onclick JS: {onclick_value}")
                    continue

                page_type, clip_id, extra = match.groups()

                self.logger.info(f"Fetching clip {idx} with clip_id={clip_id}")

                with page.context.expect_page() as new_page_info:
                    page.evaluate(
                        f"show_pop('{page_type}','{clip_id}','{extra}')")
                new_page = new_page_info.value

                new_page.wait_for_load_state('load', timeout=5000)
                # Fetch the image element inside the popup
                img_element = new_page.query_selector(
                    '.rDivImgouterBox img')

                if not img_element:
                    self.logger.warning(
                        f"No image found in popup for clip {clip_id}")
                    continue

                # Extract the image source (URL)
                img_url = img_element.get_attribute('src')
                if not img_url:
                    self.logger.warning(
                        f"Image source URL missing for clip {clip_id}")
                    continue

                response = new_page.request.get(img_url)
                if response.status != 200:
                    self.logger.warning(
                        f"Failed to download image: HTTP {response.status}")
                    new_page.close()
                    continue

                new_page.close()

                clip_path = edition_folder / (f"samaja_{formatted_date}_"
                                              f"{page_number}_article"
                                              f"_{idx}.png")
                with open(clip_path, 'wb') as f:
                    f.write(response.body())
                self.logger.info(
                    f"Downloaded clip {idx} for page {page_number}: {clip_path}")
                clips_downloaded += 1


        except Exception as e:
            self.logger.error(
                f"Error downloading clips for page {page_number}: {e}")

        return clips_downloaded

    def run(self) -> bool:
        self.logger.info("Starting Samaja e-paper crawler")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()

            try:
                # Go to homepage
                page.goto(self.base_url)
                time.sleep(2)

                # Get editions
                editions = self.get_editions(page)
                if not editions:
                    self.logger.error("No editions found, exiting...")
                    return False

                success_count = 0
                failure_count = 0

                for edition in editions:
                    self.logger.info(f"Processing edition: {edition['name']}")

                    page.goto("https://samajaepaper.in/" + edition['url'])
                    time.sleep(2)

                    edition_folder = self._create_edition_folder(
                                                                 edition[
                                                                     'name'])
                    total_pages = self.get_total_pages(page)

                    for pnum in range(1, total_pages + 1):
                        # Select the page if there's a dropdown or navigation
                        try:
                            page.select_option('select#tpgnumber', str(pnum))
                            time.sleep(2)
                        except Exception as e:
                            print(f"Error:{e}")

                        pdf_ok = self.download_pdf(page, pnum, edition_folder,edition[
                                                                     'date'])
                        clips_count = self.download_clips(page, pnum,
                                                          edition_folder,edition[
                                                                     'date'])

                        if pdf_ok:
                            self.logger.info(
                                f"Page {pnum} downloaded with {clips_count} clips.")
                            success_count += 1
                        else:
                            self.logger.warning(
                                f"Page {pnum} failed to download.")
                            failure_count += 1

                self.logger.info(
                    f"Completed crawling with {success_count} successful and {failure_count} failed downloads.")
                return success_count > 0

            except Exception as e:
                self.logger.error(f"Critical error: {e}")
                return False

            finally:
                browser.close()


def main():
    base_url = "https://samajaepaper.in/"
    crawler = SamajaCrawler(base_url)
    success = crawler.run()
    exit_code = 0 if success else 1
    print(f"Process completed with exit code: {exit_code}")
    return exit_code


if __name__ == "__main__":
    exit(main())
