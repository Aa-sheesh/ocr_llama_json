#!/usr/bin/env python3
"""
Rozana Spokesman — Chandigarh edition
Robust article-clipping downloader (scrapes <area class="getArea"> markers).

• Saves files as:  rozana_spokesman_YYYY-MM-DD_pp_article_nn.jpg
• Skips duplicates automatically
• Logs missing images at the end for easy auditing
"""
from __future__ import annotations

import logging
import time
import pathlib
from datetime import datetime
from urllib.parse import urljoin
from typing import Optional, Dict, Any

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --------------------------------------------------------------------------- #
#  CONFIGURATION                                                              #
# --------------------------------------------------------------------------- #
BASE_URL              = "https://www.rozanaspokesman.com"
EDITION               = "chandigarh"          # hard-wired – only want Chandigarh
EDITION_ID_FALLBACK   = "21"                  # 21 = Punjab in <input id="ediAlias21">
HEADLESS              = True
REQUEST_TIMEOUT       = 5                    # sec per GET
MAX_RETRIES           = 3
RETRY_BACKOFF         = 3                     # sec base back-off (multiplied by attempt)
HEAD_CHECK            = False                 # True → fast HEAD probe before GET
LOG_LEVEL             = "INFO"                # DEBUG / INFO / WARNING / ERROR

# --------------------------------------------------------------------------- #
#  LOGGING SETUP                                                              #
# --------------------------------------------------------------------------- #
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("rozana-crawler")

# --------------------------------------------------------------------------- #
#  HELPER FUNCTIONS                                                           #
# --------------------------------------------------------------------------- #
def today_str_ist() -> tuple[str, str]:
    """Return today's date as ('DD-MM-YYYY', 'YYYY-MM-DD')."""
    now = datetime.now().astimezone()        # assume host TZ is IST
    return now.strftime("%d-%m-%Y"), now.strftime("%Y-%m-%d")


def make_output_dir(root: pathlib.Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    log.info("Output directory: %s", root.resolve().as_posix())


def setup_driver() -> webdriver.Chrome:
    """Headless Chrome with sane defaults."""
    opts = Options()
    if HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-extensions")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )
    svc   = Service(ChromeDriverManager().install())
    drv   = webdriver.Chrome(service=svc, options=opts)
    drv.set_page_load_timeout(15)
    return drv


def _head_ok(url: str) -> bool:
    if not HEAD_CHECK:
        return True
    try:
        r = requests.head(url, timeout=REQUEST_TIMEOUT)
        return r.status_code == 200
    except requests.RequestException:
        return False


def safe_request(url: str, dest: pathlib.Path) -> bool:
    """Download `url` → `dest`.  Returns True on success, False on final failure."""
    if HEAD_CHECK and not _head_ok(url):
        log.debug("HEAD %s → not 200; skipping download", url)
        return False

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with requests.get(url, timeout=REQUEST_TIMEOUT, stream=True) as r:
                r.raise_for_status()
                dest.parent.mkdir(parents=True, exist_ok=True)
                with open(dest, "wb") as fh:
                    for chunk in r.iter_content(chunk_size=8192):
                        fh.write(chunk)
            return True
        except requests.RequestException as exc:
            if attempt == MAX_RETRIES:
                log.warning("Giving up on %s (%s)", url, exc)
            else:
                time.sleep(RETRY_BACKOFF * attempt)
    return False


def parse_area_tag(area_tag) -> Optional[Dict[str, Any]]:
    """
    Convert one <area class="getArea"> element into a metadata dict.
    Expected `alt` format (pipe-separated, 9 fields):
        idx0 english_title
        idx1 punjabi_title
        idx2 id
        idx3 ""
        idx4 ""
        idx5 /epaperimages/markup/27-05-2025/1-punjab-4.jpg
        idx6 "0"
        idx7 edition_id
        idx8 slug
    """
    try:
        tokens = area_tag.get("alt", "").split("|")
        img_rel = tokens[5]
        edition_id = tokens[7] or EDITION_ID_FALLBACK
        slug = tokens[8] if len(tokens) > 8 and tokens[8] else pathlib.Path(img_rel).stem

        fname_core = pathlib.Path(img_rel).stem              # e.g. 1-punjab-4
        parts = fname_core.split("-")                        # ['1', 'punjab', '4']
        page_idx = int(parts[0])
        article_idx = int(parts[-1])

        return {
            "page": page_idx,
            "article": article_idx,
            "edition_id": edition_id,
            "slug": slug,
            "img_rel": img_rel,
            "ext": pathlib.Path(img_rel).suffix.lstrip("."),
        }
    except Exception as err:
        log.debug("Skipping malformed <area> tag: %s", err)
        return None

# --------------------------------------------------------------------------- #
#  MAIN CRAWLER CLASS                                                         #
# --------------------------------------------------------------------------- #
class PunjabImageCrawler:
    def __init__(self) -> None:
        self.driver = setup_driver()
        self.date_ddmmyyyy, self.date_iso = today_str_ist()
        self.base_page_url = f"{BASE_URL}/epaper/{self.date_ddmmyyyy}"
        self.output_root = pathlib.Path("downloads/rozana_spokesman") / EDITION
        make_output_dir(self.output_root)

        self.seen_images: set[str] = set()
        self.missing_images: list[str] = []

    # ---------- orchestration ---------- #
    def run(self) -> None:
        try:
            total_pages = self._detect_total_pages()
            log.info("Total pages detected: %d", total_pages)
            for page in range(1, total_pages + 1):
                self._process_page(page)
        finally:
            self.driver.quit()
            self._report_missing()

    # ---------- per-page logic ---------- #
    def _epaper_url(self, page_idx: int) -> str:
        return f"{self.base_page_url}/{page_idx}/{EDITION}"

    def _detect_total_pages(self) -> int:
        try:
            self.driver.get(self._epaper_url(1))
            self._wait_for_body()
            sel = self.driver.find_element(By.ID, "epaperPgId")
            vals = [int(opt.get_attribute("value")) for opt in sel.find_elements(By.TAG_NAME, "option")]
            return max(vals)
        except Exception as e:
            log.warning("Could not detect total pages (default → 10): %s", e)
            return 10

    def _process_page(self, page_idx: int) -> None:
        url = self._epaper_url(page_idx)
        log.info("Page %d → %s", page_idx, url)
        try:
            self.driver.get(url)
            self._wait_for_body()

            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            areas = soup.select("area.getArea")
            if not areas:
                log.info("No <area> tags on page %d", page_idx)
                return

            for area in areas:
                meta = parse_area_tag(area)
                if meta:
                    self._handle_article(meta)
        except (TimeoutException, WebDriverException) as e:
            log.error("Page %d skipped due to driver error: %s", page_idx, e)

    # ---------- per-article logic ---------- #
    def _handle_article(self, meta: Dict[str, Any]) -> None:
        img_url  = urljoin(BASE_URL, meta["img_rel"])
        filename = pathlib.Path(img_url).name

        if filename in self.seen_images:
            log.debug("Duplicate %s – skipped", filename)
            return
        self.seen_images.add(filename)

        # File naming:  rozana_spokesman_YYYY-MM-DD_pp_article_nn.ext
        fname = (
            f"rozana_spokesman_{self.date_iso}_{meta['page']:02d}"
            f"_article_{meta['article']:02d}.{meta['ext']}"
        )
        dest_file = self.output_root / fname

        if dest_file.exists():
            log.debug("Already on disk: %s", dest_file.name)
            return

        log.info("→ downloading %s", fname)
        if not safe_request(img_url, dest_file):
            self.missing_images.append(img_url)

    # ---------- utils ---------- #
    def _wait_for_body(self, timeout: int = 10) -> None:
        WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "area.getArea"))
        )

    def _report_missing(self) -> None:
        if self.missing_images:
            log.warning("\nMissing images (%d):", len(self.missing_images))
            for url in self.missing_images:
                log.warning("  - %s", url)
        else:
            log.info("All images downloaded successfully!")

# --------------------------------------------------------------------------- #
#  ENTRY POINT                                                                #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        PunjabImageCrawler().run()
    except KeyboardInterrupt:
        log.info("Interrupted by user – shutting down.")
    except Exception as ex:
        log.exception("Fatal error: %s", ex)
