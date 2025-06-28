#!/usr/bin/env python
"""
prameya_pages_scraper.py – FINAL (output in Prameya/{edition}/(...).png)
--------------------------------
• Goes to https://www.prameyaepaper.com
• Loops through every edition tab (Bhubaneswar, Cuttack, …)
• For each edition:
      – finds the viewer (direct or inside the single iframe)
      – clicks “Next” until the #next-btn is disabled / missing
      – saves the full-page PNG   <img id="map_area_img">
        as (Prameya{DATE}{page:02d}).png in a folder:
           Prameya/{edition}/

Folder layout
└── Prameya/
    ├── BHUBANESWAR/
    │   ├── (Prameya2025-05-3101).png
    │   ├── (Prameya2025-05-3102).png
    │   └── …
    ├── CUTTACK/
    │   └── …
"""

import io, time, pathlib
from datetime import date
from urllib.parse import urljoin
import requests
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

ROOT_URL  = "https://www.prameyaepaper.com"
HEADLESS  = True
WAIT_S    = 20
TODAY     = date.today().isoformat()
PUB       = "prameya"
DOWNLOADS_FOLDER = "downloads"
OUT_DIR   = pathlib.Path(DOWNLOADS_FOLDER)

# ────────── browser helper ──────────
def new_driver(headless=True):
    opts = Options()
    opts.add_argument("--window-size=1920,1080")
    if headless:
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=opts
    )

# ────────── file saver ──────────
def save_png(src_url: str, dest_path: pathlib.Path):
    if src_url.startswith("//"):
        src_url = "https:" + src_url
    r = requests.get(src_url, timeout=20)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(dest_path), "PNG", quality=90)

# ────────── viewer detection ──────────
def get_inside_viewer(driver, wait):
    """
    Return True when <img id="map_area_img"> is reachable.
    Handles: (a) viewer inline, (b) viewer in a single iframe.
    """
    # inline?
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "img#map_area_img[src]")))
        return True
    except TimeoutException:
        pass
    # iframe?
    try:
        iframe = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='/prameya/document']"))
        )
        driver.switch_to.frame(iframe)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "img#map_area_img[src]"))
        )
        return True
    except TimeoutException:
        driver.switch_to.default_content()
        return False

# ────────── scrape one edition ──────────
def scrape_edition(driver, wait, edition_name, ed_href):
    edition_dir = OUT_DIR / PUB / edition_name.lower()
    driver.get(urljoin(ROOT_URL, ed_href))

    if not get_inside_viewer(driver, wait):
        print("    viewer not found – skipped")
        return

    page = 1
    while True:
        img_tag = driver.find_element(By.CSS_SELECTOR, "img#map_area_img[src]")
        src = img_tag.get_attribute("src")
        # filename format: (Prameya{DATE}{page:02d}).png
        filename = f"(Prameya{TODAY}{page:02d}).png"
        dest = edition_dir / filename

        if not dest.exists():
            try:
                save_png(src, dest)
                print(f"   ✓ saved page {page:02d}")
            except Exception as e:
                print(f"   ✗ page {page:02d}  {e}")

        # Next?
        try:
            nxt = driver.find_element(By.CSS_SELECTOR, "button#next-btn")
            disabled = nxt.get_attribute("disabled") or \
                       "disabled" in (nxt.get_attribute("class") or "").lower()
        except NoSuchElementException:
            disabled = True

        if disabled:
            print("   last page reached.")
            break

        old_src = src
        nxt.click()
        try:
            WebDriverWait(driver, WAIT_S).until(
                lambda d: d.find_element(By.CSS_SELECTOR, "img#map_area_img").get_attribute("src") != old_src
            )
        except TimeoutException:
            print("    next page not loaded – stop")
            break
        page += 1

    driver.switch_to.default_content()  # ready for next edition

# ────────── main loop ──────────
def main():
    drv = new_driver(HEADLESS)
    wait = WebDriverWait(drv, WAIT_S)
    try:
        drv.get(ROOT_URL)
        wait.until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "a.nav-link[href^='/edition/']")))
        editions = [(el.text.strip().upper() or f"ED{ix+1}", el.get_attribute("href"))
                    for ix, el in enumerate(
                        drv.find_elements(By.CSS_SELECTOR, "a.nav-link[href^='/edition/']"))]

        print("Editions:", ", ".join(name for name, _ in editions))

        for name, href in editions:
            print(f"\n {name}")
            scrape_edition(drv, wait, name, href)

    finally:
        drv.quit()
        print("\nDone. Images are in:", OUT_DIR.resolve())

if __name__ == "__main__":
    main()





