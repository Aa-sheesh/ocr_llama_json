"""Multiple Images of pages - {publication_name}/{edition_name}/({publication_name}_{date}_{page_number}.png)s"""


from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
from pathlib import Path
import time
import requests

def download_all_epaper_images():
    publication_name = "samachar_jagat"
    edition_name = "jaipur"  # Change as needed
    today_date = datetime.now().strftime("%Y%m%d")
    edition = 8  # 5 for Jaipur-evening, 8 for Jaipur-city, 9 for Daak, etc.

    url = f"https://www.samacharjagat.com/home/epaperview?edition={edition}&date={datetime.now().strftime('%Y-%m-%d')}&page=1"
    output_dir = Path.cwd() / 'downloads' /publication_name / edition_name
    output_dir.mkdir(parents=True, exist_ok=True)

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920x1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    print(f"🔗 Opening main page: {url}")
    driver.get(url)
    time.sleep(3)

    try:
        img_tags = driver.find_elements(By.CSS_SELECTOR, "li.bjqs-slide img#full-image")
        print(f"🖼️ Found {len(img_tags)} image elements")

        for idx, img in enumerate(img_tags, start=1):
            img_url = img.get_attribute("src")
            if img_url:
                filename = f"{publication_name}_{today_date}_{idx}.png"
                file_path = output_dir / filename
                img_data = requests.get(img_url).content
                with open(file_path, "wb") as f:
                    f.write(img_data)
                print(f"✅ Downloaded: {file_path}")
            else:
                print(f"⚠️ Skipped page {idx}, no image URL found.")
    except Exception as e:
        print(f"❌ Error parsing image elements: {e}")
    finally:
        driver.quit()

    print("✅ All images downloaded.")

# Run the downloader
download_all_epaper_images()
