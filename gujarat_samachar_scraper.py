#!/usr/bin/env python
"""
Gujarat Samachar • e-paper article scraper (output in edition folder, PNG)
──────────────────────────────────────────────────────────────────────────
Saves clipped articles as:

    GujaratSamachar/{EDITION}/(GujaratSamachar{DATE}{page:02d}article{idx}).png

for each article on each page.
"""

import io, pathlib, re, sys, time
from datetime import date
from urllib.parse import urljoin

import requests
from PIL import Image
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
try:
    # Selenium 4.x
    from selenium.webdriver.chrome.service import Service
except ImportError:
    # Selenium 3.x
    from selenium.webdriver.chrome.service import _S
    Service = _S.Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ───────── user settings ─────────
DATE       = "02-06-2025"                # format in URL (DD-MM-YYYY)
EDITION    = "ahmedabad"                 # e.g., "Ahmedabad", "Surat", etc.
LAST_PAGE  = 10                          # number of pages in this edition
HEADLESS   = True
DOWNLOADS = 'downloads'
PUB        = "gujarat_samachar"
SAVE_ROOT  = pathlib.Path(DOWNLOADS) / PUB / EDITION  # changed: top-level/PUB/EDITION
# ─────────────────────────────────

# CSS selectors
OVERLAY_CSS = "a.test-anchore.anchor_click"
IMG_CSS     = "img#current_artical"

def make_driver(headless=True):
    opts = Options()
    opts.add_argument("--window-size=1920,1080")
    if headless:
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=opts
    )

def save_png(src_url, dest_path):
    """
    Download src_url and save as PNG at dest_path.
    """
    if src_url.startswith("//"):
        src_url = "https:" + src_url
    r = requests.get(src_url, timeout=(60, 60))
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest_path, "PNG", quality=90)

def main(date_str: str, last_page: int):
    driver = make_driver(HEADLESS)
    wait   = WebDriverWait(driver, 20)

    try:
        for page in range(1, last_page + 1):
            page_url = f"https://epaper.gujaratsamachar.com/{EDITION}/{date_str}/{page}"
            print("→", page_url)
            driver.get(page_url)

            # 1) wait until at least one overlay appears
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, OVERLAY_CSS)))
            except TimeoutException:
                print(f"No overlays on page {page} → skipping")
                continue

            overlays = driver.find_elements(By.CSS_SELECTOR, OVERLAY_CSS)
            if not overlays:
                print(f"No overlays found on page {page} → skipping")
                continue

            print(f"Found {len(overlays)} overlays on page {page}")

            for idx, overlay in enumerate(overlays, 1):
                href = overlay.get_attribute("href")
                # open in new tab/window
                main_handle = driver.current_window_handle
                driver.execute_script("window.open(arguments[0], '_blank');", href)
                # switch to new window
                WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > 1)
                new_handle = [h for h in driver.window_handles if h != main_handle][0]
                driver.switch_to.window(new_handle)

                # wait for clipped article image
                try:
                    img_el = WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, IMG_CSS))
                    )
                except TimeoutException:
                    print(f" Article {idx} on page {page}: image not found → closing")
                    driver.close()
                    driver.switch_to.window(main_handle)
                    continue

                img_src = img_el.get_attribute("src")
                print(f"  Article {idx}: found image")

                # save as PNG with new naming scheme
                filename = f"(GujaratSamachar{date_str}{page:02d}article{idx}).png"
                dest = SAVE_ROOT / filename
                save_png(img_src, dest)
                print(f"   ✓ saved {filename}")

                # close article window and switch back
                driver.close()
                driver.switch_to.window(main_handle)
                time.sleep(0.2)

            # small pause before next page
            time.sleep(0.5)

    finally:
        driver.quit()
        print("\nDone. Images saved under:", SAVE_ROOT.resolve())

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        DATE = sys.argv[1]
    if len(sys.argv) == 3:
        LAST_PAGE = int(sys.argv[2])
    main(DATE, LAST_PAGE)


