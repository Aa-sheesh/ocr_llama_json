#!/usr/bin/env python
"""
Deccan Chronicle – e-paper article scraper (edition‐specific folders)
────────────────────────────────────────────────────────────────────
Extracts every clipped article image from each page of the
Chennai and Hyderabad editions at http://epaper.deccanchronicle.com

Saves files under:
  DeccanChronicle/{EditionName}/(DeccanChronicle{DATE}{EditionName}{page:02d}article{idx}).png
"""

import io, pathlib, re, sys, time
from datetime import date

import requests
from PIL import Image
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
try:
    # Selenium 4.x
    from selenium.webdriver.chrome.service import Service
except ImportError:
    # Selenium 3.x fallback
    from selenium.webdriver.chrome import service as _svc
    Service = _svc.Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ───────── user settings ─────────
DATE          = date.today().strftime("%Y-%m-%d")
EDITIONS      = [("CHN", "chennai"), ("HYD", "hyderabad")]
LAST_PAGE     = 10
HEADLESS      = True
BASE_SAVE_DIR = pathlib.Path("downloads/deccan_chronicle")
PUB           = "DeccanChronicle"
# ─────────────────────────────────

# CSS/XPath selectors
SELECT_CSS  = "select#ddl_ecode"
THUMB_CSS   = "input[title='{page_num}']"
OVERLAY_CSS = "a[href*='articledetailpage.aspx?id=']"
IMG_CSS     = "img#Image1"

def make_driver(headless=True):
    opts = Options()
    opts.add_argument("--window-size=1920,1080")
    if headless:
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=opts
    )

def save_png(src_url, dest_path):  # changed: save as PNG
    if src_url.startswith("//"):
        src_url = "https:" + src_url
    r = requests.get(src_url, timeout=(60,60))
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest_path, "PNG", quality=90)

def scrape_edition(driver, wait, edition_name):
    """
    After selecting edition, loop pages 1…LAST_PAGE by clicking the thumbnail
    with title="{page}", then extracting all clipped article images.
    Saves into BASE_SAVE_DIR/edition_name/ with filenames including edition.
    """
    edition_dir = BASE_SAVE_DIR / edition_name                   # changed: no date directory
    for page in range(1, LAST_PAGE + 1):
        print(f"  {edition_name} Page {page}")

        # a) Click thumbnail to navigate if page > 1
        if page > 1:
            thumb_selector = THUMB_CSS.format(page_num=page)
            try:
                thumb = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, thumb_selector)))
            except TimeoutException:
                print(f"   Thumbnail for page {page} not found → stopping {edition_name}.")
                break
            thumb.click()
            time.sleep(1)  # allow page to load

        # b) wait for overlays
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, OVERLAY_CSS)))
        except TimeoutException:
            print(f"   No overlays on {edition_name} page {page} → skipping.")
            continue

        overlays = driver.find_elements(By.CSS_SELECTOR, OVERLAY_CSS)
        if not overlays:
            print(f"   No overlays found on {edition_name} page {page} → skipping.")
            continue

        print(f"   Found {len(overlays)} overlays on {edition_name} page {page}")

        # c) process each overlay
        for idx, overlay in enumerate(overlays, 1):
            href = overlay.get_attribute("href")
            main_handle = driver.current_window_handle
            driver.execute_script("window.open(arguments[0], '_blank');", href)
            wait.until(lambda d: len(d.window_handles) > 1)
            new_handle = [h for h in driver.window_handles if h != main_handle][0]
            driver.switch_to.window(new_handle)

            # wait for clipped image
            try:
                img_el = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, IMG_CSS))
                )
            except TimeoutException:
                print(f"    • Article {idx}: image not found → closing")
                driver.close()
                driver.switch_to.window(main_handle)
                continue

            img_src = img_el.get_attribute("src")
            # filename includes edition inside parentheses, save as PNG
            filename = f"({PUB}{DATE}{edition_name}{page:02d}article{idx}).png"  # changed: .png extension
            dest = edition_dir / filename
            save_png(img_src, dest)
            print(f"    • Saved {filename}")

            driver.close()
            driver.switch_to.window(main_handle)
            time.sleep(0.2)

        time.sleep(0.5)  # brief pause before next page

def main():
    driver = make_driver(HEADLESS)
    wait   = WebDriverWait(driver, 20)

    try:
        driver.get("http://epaper.deccanchronicle.com/epaper_main.aspx#2840765")
        # wait for edition selector
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, SELECT_CSS)))
        except TimeoutException:
            print("Edition selector not found → exiting.")
            return

        select_elem = driver.find_element(By.CSS_SELECTOR, SELECT_CSS)
        select = Select(select_elem)

        for code, edition_name in EDITIONS:
            print(f"Selecting edition: {edition_name} ({code})")
            select.select_by_value(code)
            time.sleep(2)  # allow postback
            scrape_edition(driver, wait, edition_name)
            print(f"Finished edition {edition_name}\n")
            time.sleep(1)

    finally:
        driver.quit()
        print("All done. Images saved under:", BASE_SAVE_DIR.resolve())  # changed: no date in path

if __name__ == "__main__":
    main()




