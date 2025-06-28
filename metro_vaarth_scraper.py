"""Clipped Article Images - {publication_name}/{date}/{edition_name}/({publication_name}{date}{page_number}{article{n}}.png)s
"""

import os
import time
import requests
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# === CONFIGURATION ===
today_str = datetime.today().strftime("%Y%m%d")  # Format: YYYYMMDD
PUBLICATION_NAME = "metro_vaartha"
EDITION_NAME = "metro_vaartha_ernakulam"
BASE_URL = f"https://epaper.metrovaartha.com/edition/MetroVaarthaErnakulam/MVART_ERN/MVART_ERN_{today_str}/page/"
ARTICLE_URL_PREFIX = f"https://epaper.metrovaartha.com/editionname/MetroVaarthaErnakulam/MVART_ERN/page/"

# === Output path ===
base_output_path = Path.cwd() / 'downloads' / PUBLICATION_NAME / EDITION_NAME
base_output_path.mkdir(parents=True, exist_ok=True)

# === SELENIUM SETUP ===
options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument("--window-size=1920,1080")
driver = webdriver.Chrome(options=options)

# === FUNCTION TO DETECT TOTAL PAGES ===
def get_total_pages():
    driver.get(BASE_URL + "1")
    time.sleep(3)
    page_buttons = driver.find_elements(By.CSS_SELECTOR, "nav.pagination-primary li.page-item button.page-link")
    pages = [btn.text for btn in page_buttons if btn.text.isdigit()]
    return max(map(int, pages)) if pages else 1

# === FUNCTION TO EXTRACT ONLY VISIBLE CLIPPED IMAGE IDs ===
def extract_clip_ids_from_page(page_no):
    url = BASE_URL + str(page_no)
    driver.get(url)
    time.sleep(3)
    try:
        carousel = driver.find_element(By.CSS_SELECTOR, "div.carousel-item.active")
        clips = carousel.find_elements(By.CSS_SELECTOR, "div.epaper-article-container > div.overlay")
        ids = [clip.get_attribute("id") for clip in clips if clip.get_attribute("id")]
        return ids
    except Exception as e:
        print(f"❌ Failed to load clips on page {page_no}: {str(e)}")
        return []

# === FUNCTION TO DOWNLOAD CLIPPED IMAGE FROM ARTICLE PAGE ===
def download_clipped_image(article_id, page_no, article_index):
    article_url = f"{ARTICLE_URL_PREFIX}{page_no}/article/{article_id}"
    try:
        driver.get(article_url)
        time.sleep(3)
        img_tag = driver.find_element(By.CSS_SELECTOR, "div.epaper-article-image-container img")
        img_url = img_tag.get_attribute("src")
        img_data = requests.get(img_url).content

        filename = f"{PUBLICATION_NAME}_{today_str}_page{page_no}article{article_index}.png"
        filepath = base_output_path / filename
        with open(filepath, "wb") as f:
            f.write(img_data)
        print(f"✅ Saved: {filepath}")
    except Exception as e:
        print(f"❌ Failed to download {article_id}: {str(e)}")

# === MAIN EXECUTION FLOW ===
total_pages = get_total_pages()
print(f"\n🔎 Total Pages Found: {total_pages}\n")

for page in range(1, total_pages + 1):
    print(f"➡️ Processing Page {page}...")
    clip_ids = extract_clip_ids_from_page(page)
    print(f"🧩 Found {len(clip_ids)} clipped images on page {page}")
    for idx, article_id in enumerate(clip_ids, start=1):
        download_clipped_image(article_id, page, idx)

driver.quit()
print("🧹 Browser closed. Script finished.")
