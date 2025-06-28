"""Clipped Article Images - {publication_name}/{edition}/({publication_name}_{date}_{page_number}{article{n}}.png)s
"""

import os
import time
import requests
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 🆕 Get today's date in YYYYMMDD format
DATE = datetime.now().strftime("%Y%m%d")
PUBLICATION_NAME = "vartha_bharati"
BASE_PAGE_URL = f"https://epaper.varthabharati.in/edition/Mangalore/VARTABARTI_MAN/VARTABARTI_MAN_{DATE}/page/"
ARTICLE_URL = "https://epaper.varthabharati.in/editionname/Mangalore/VARTABARTI_MAN/page/"
edition_name = "mangalore"  # Change as needed
SAVE_DIR = os.path.join( 'downloads', PUBLICATION_NAME, edition_name)
os.makedirs(SAVE_DIR, exist_ok=True)

# Selenium Setup
options = Options()
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
driver = webdriver.Chrome(options=options)

def download_image(img_url, save_path):
    try:
        img_data = requests.get(img_url).content
        with open(save_path, 'wb') as handler:
            handler.write(img_data)
        print(f"✅ Downloaded: {save_path}")
    except Exception as e:
        print(f"❌ Failed to download {img_url}: {e}")

def is_valid_article_id(id_str):
    return bool(re.match(rf"VARTABARTI_MAN_{DATE}_\d+_\d+$", id_str))

def safe_get_clipped_image(clip_url, page_num, article_num, retries=2):
    for attempt in range(retries):
        try:
            driver.get(clip_url)

            # Optional: scroll to ensure lazy-loaded content appears
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.epaper-article-image-container'))
            )
            img_tags = driver.find_elements(By.CSS_SELECTOR, 'div.epaper-article-image-container img')
            if not img_tags:
                print(f"⚠️ No image tag found in {clip_url}")
                return False

            img_src = img_tags[0].get_attribute('src')
            if not img_src or not img_src.endswith(('.jpg', '.png')):
                print(f"⚠️ Invalid or missing image src in {clip_url}")
                return False

            filename = f"{PUBLICATION_NAME}_{DATE}_page{page_num}article{article_num}.png"
            save_path = os.path.join(SAVE_DIR, filename)
            download_image(img_src, save_path)
            return True

        except Exception as e:
            print(f"❌ Attempt {attempt+1} failed for {clip_url}: {e}")
            if attempt == retries - 1:
                print(f"⏩ Skipping after {retries} attempts.")
    return False

def scrape_page(page_num):
    page_url = BASE_PAGE_URL + str(page_num)
    print(f"\n📄 Processing Page {page_num}")
    driver.get(page_url)

    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.overlay'))
        )
    except:
        print(f"⚠️ No overlays loaded on page {page_num}")

    clip_links = []
    overlay_divs = driver.find_elements(By.CSS_SELECTOR, 'div.overlay')
    for div in overlay_divs:
        id_attr = div.get_attribute("id")
        if id_attr and is_valid_article_id(id_attr):
            clip_links.append(f"{ARTICLE_URL}{page_num}/article/{id_attr}")

    clip_links = list(set(clip_links))
    print(f"🔍 Checking {len(clip_links)} clipped overlays on page {page_num}")

    valid_count = 0
    for link in clip_links:
        success = safe_get_clipped_image(link, page_num, valid_count + 1)
        if success:
            valid_count += 1

    if valid_count == 0:
        print(f"⚠️ No valid clipped images. Trying full-page fallback.")
        try:
            img_tag = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.carousel-item.active img'))
            )
            img_src = img_tag.get_attribute('src')
            filename = f"{PUBLICATION_NAME}{DATE}{page_num}full.png"
            save_path = os.path.join(SAVE_DIR, filename)
            download_image(img_src, save_path)
        except Exception as e:
            print(f"❌ Fallback failed on page {page_num}: {e}")

# Run for all pages
for page in range(1, 13):
    scrape_page(page)

driver.quit()

