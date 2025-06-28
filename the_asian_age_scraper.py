#!/usr/bin/env python
"""
asianage_article_scraper.py
———————————————
Downloads the main article image (<img id="Image1">) for **every** article
overlay on **every** page in an Asian Age e-paper edition.

Saves files under:
  AsianAge/{Edition}/(AsianAge{Date}{Page:02d}article{Idx}).png
"""

import io, time, pathlib, re, sys
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
from webdriver_manager.chrome import ChromeDriverManager

# ============= CONFIG =============
EDITION_URL = "http://onlineepaper.asianage.com/asianage-epaper.aspx#page2839139"
PUBLICATION = "the_asian_age"
EDITION     = "delhi"  # replace with actual edition name if known
DATE        = date.today().isoformat()  # e.g. "2025-05-29"
LAST_PAGE   = None  # will be determined dynamically
HEADLESS    = True
WAIT        = 10
# ==================================

OUT_ROOT = 'downloads' / pathlib.Path(PUBLICATION) / EDITION

def new_driver(headless=True):
    opt = Options()
    opt.add_argument("--window-size=1920,1080")
    if headless:
        opt.add_argument("--headless=new")
        opt.add_argument("--disable-gpu")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opt
    )

def wait_page_border(drv, page_num):
    WebDriverWait(drv, WAIT).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR,
             f"input[title='{page_num}'][style*='border: 2px solid rgb(232, 39, 44)']")))

def save_png(url, dest):
    if url.startswith("//"):
        url = "http:" + url
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "PNG", quality=90)

def scrape():
    drv = new_driver(HEADLESS)
    wait = WebDriverWait(drv, WAIT)
    try:
        print("opening edition…")
        drv.get(EDITION_URL)

        # how many pages?
        wait.until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "input[id^='DataList1_ImageButton1_']")))
        inputs = drv.find_elements(By.CSS_SELECTOR, "input[id^='DataList1_ImageButton1_']")
        total = len(inputs)
        print("pages:", total)

        for p in range(1, total + 1):
            # click page selector
            drv.find_element(By.CSS_SELECTOR, f"input[title='{p}']").click()
            wait_page_border(drv, p)
            time.sleep(0.3)

            overlays = drv.find_elements(
                By.CSS_SELECTOR, "a[href*='articledetailpage.aspx?id=']")
            if not overlays:
                print(f"page {p:02d}: no article overlays")
                continue

            print(f"page {p:02d}: {len(overlays)} articles")
            for idx, a in enumerate(overlays, start=1):
                art_url = a.get_attribute("href")
                art_id  = re.search(r"id=(\d+)", art_url).group(1)
                filename = f"({PUBLICATION}{DATE}{p:02d}article{idx}).png"
                dest     = OUT_ROOT / filename
                if dest.exists():
                    print("   •", filename, "(cached)")
                    continue

                # open in new tab
                main_tab = drv.current_window_handle
                drv.execute_script("window.open(arguments[0], '_blank');", art_url)
                drv.switch_to.window(drv.window_handles[-1])

                try:
                    img_tag = WebDriverWait(drv, WAIT).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "img#Image1[src]"))
                    )
                    img_url = urljoin(art_url, img_tag.get_attribute("src"))
                    save_png(img_url, dest)
                    print("   • saved", filename)
                except Exception as e:
                    print("   •", filename, "ERROR:", e)
                finally:
                    drv.close()
                    drv.switch_to.window(main_tab)

    finally:
        drv.quit()
        print("\nDone. Files in:", OUT_ROOT.resolve())

if __name__ == "__main__":
    scrape()





