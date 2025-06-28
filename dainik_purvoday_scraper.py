"""Clipped images - DainikPurvoday/20250531/Guwahati/DainikPurvoday202505311article1.jpg
"""

import os
import re
import time
import requests
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ----------- CONFIGURATION -----------
BASE_URL = "https://epaper.dainikpurvoday.com"
EDITION_KEY = "4f16fe56-1ea8-425a-970c-986c95b30e74"  # Guwahati edition
EDITION_NAME = "guwahati"
PUBLICATION_NAME = "dainik_purvoday"
WAIT_TIMEOUT = 15  # seconds

# ----------- SETUP CHROMEDRIVER -----------
options = Options()
options.add_argument("--start-maximized")
options.add_argument("--headless=new")
service = Service()
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, WAIT_TIMEOUT)

def download_image(url, save_path):
    try:
        r = requests.get(url, stream=True, timeout=10)
        if r.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            print(f"[Downloaded] {save_path}")
        else:
            print(f"[Failed] HTTP {r.status_code} - {url}")
    except Exception as ex:
        print(f"[Error] Failed to download {url} => {ex}")

try:
    today_str = datetime.today().strftime('%Y%m%d')
    base_output_dir =  Path.cwd() / 'downloads' /PUBLICATION_NAME / EDITION_NAME

    print("[INFO] Opening homepage...")
    driver.get(BASE_URL)

    print("[INFO] Waiting for page thumbnails to load...")
    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#pagenav .page-thumbnail")))

    print("[INFO] Extracting UUIDs from thumbnail styles...")
    thumbnails = driver.find_elements(By.CSS_SELECTOR, "#pagenav .page-thumbnail")
    uuids = []
    for thumb in thumbnails:
        style = thumb.get_attribute("style")
        match = re.search(r'url\("/pages/([a-f0-9\-]+)_sml\.jpg"\)', style)
        if match:
            uuids.append(match.group(1))

    print(f"[INFO] Found {len(uuids)} pages.")

    for idx, uuid in enumerate(uuids, 1):
        page_url = f"{BASE_URL}/index.aspx?p={uuid}&e={EDITION_KEY}"
        print(f"\n[INFO] Opening Page {idx}: {page_url}")
        driver.get(page_url)

        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "map area[data-area]")))
            time.sleep(1)
            areas = driver.find_elements(By.CSS_SELECTOR, "map area[data-area]")
            print(f"[INFO] Found {len(areas)} clipped regions on page {idx}")

            for j, area in enumerate(areas, 1):
                data_area = area.get_attribute("data-area")
                img_url = f"{BASE_URL}/pages/{data_area}.jpg"
                filename = f"{PUBLICATION_NAME}_{today_str}_page{idx}article{j}.jpg"
                img_path = base_output_dir / filename
                base_output_dir.mkdir(parents=True, exist_ok=True)
                download_image(img_url, img_path)

        except Exception as e:
            print(f"[ERROR] Could not process page {idx}: {e}")

finally:
    driver.quit()
    print("\n[INFO] Done. Browser closed.")
