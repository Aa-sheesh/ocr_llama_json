"""Multiple Images of pages - {publication_name}/{date}/({publication_name}{date}{page_number}.png)s
"""

import os
import time
import requests
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# ====== Config ======
EMAIL = "sahananewspapers@gmail.com"
PASSWORD = "Sahana@1301#"
CAPTCHA_API_KEY = "bd9495e9ce0b356f189274f82089e7a7"

# ====== Captcha Solver ======
def solve_captcha(api_key, image_path):
    with open(image_path, 'rb') as img:
        files = {'file': img}
        response = requests.post("http://2captcha.com/in.php", files=files, data={
            'key': api_key,
            'method': 'post'
        })
    if 'OK|' not in response.text:
        raise Exception(f"2Captcha error: {response.text}")

    captcha_id = response.text.split('|')[1]

    for _ in range(20):
        time.sleep(5)
        result = requests.get(f"http://2captcha.com/res.php?key={api_key}&action=get&id={captcha_id}")
        if 'OK|' in result.text:
            return result.text.split('|')[1]
        elif 'CAPCHA_NOT_READY' in result.text:
            continue
        else:
            raise Exception(f"2Captcha solving failed: {result.text}")

# ====== Login ======
def login_and_get_cookies():
    options = Options()
    options.add_argument("--headless")  # You can enable this if you don't need to see browser
    driver = webdriver.Chrome(options=options)

    driver.get("https://epaper.dainiknavajyoti.com/login")
    time.sleep(3)

    driver.find_element(By.ID, "login-username").send_keys(EMAIL)
    driver.find_element(By.ID, "login-password").send_keys(PASSWORD)

    captcha_img = driver.find_element(By.ID, "login-captcha-image")
    captcha_path = "captcha.png"
    captcha_img.screenshot(captcha_path)

    captcha_text = solve_captcha(CAPTCHA_API_KEY, captcha_path)
    driver.find_element(By.ID, "login-captcha").send_keys(captcha_text)
    driver.find_element(By.NAME, "login-button").click()
    time.sleep(3)

    if "dashboard" not in driver.current_url and "logout" not in driver.page_source.lower():
        driver.quit()
        raise Exception("Login failed, please check credentials or captcha solver.")

    cookies = driver.get_cookies()
    driver.quit()

    return {c['name']: c['value'] for c in cookies}

# ====== Scraper ======
def scrape_pages(cookies):
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium import webdriver

    publication_name = "dainik_navjyoti"
    today = datetime.now().strftime("%Y%m%d")
    edition_name = "jaipur"
    output_dir = 'downloads' / Path(publication_name) / edition_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # Setup Selenium to reuse login session
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)

    driver.get("https://epaper.dainiknavajyoti.com")
    for name, value in cookies.items():
        driver.add_cookie({'name': name, 'value': value})

    driver.get("https://epaper.dainiknavajyoti.com")
    time.sleep(3)

    # Extract edition ID
    body_classes = driver.find_element(By.TAG_NAME, 'body').get_attribute('class').split()
    edition_id = None
    for cls in body_classes:
        if "edition-" in cls:
            edition_id = cls.split("-")[1]
            break

    if not edition_id:
        driver.quit()
        raise Exception("❌ Edition ID not found. Possibly login failed.")

    # Navigate to today's paper
    base_url = f"https://epaper.dainiknavajyoti.com/view/{edition_id}/jaipur-city/"
    driver.get(base_url)
    time.sleep(3)

    # Find all page links
    page_links = driver.find_elements(By.CLASS_NAME, 'epaper-thumb-link')
    page_urls = [elem.get_attribute('href') for elem in page_links if elem.get_attribute('href')]

    if not page_urls:
        driver.quit()
        raise Exception("❌ No pages found.")

    session = requests.Session()
    session.cookies.update(cookies)

    for i, url in enumerate(page_urls, 1):
        driver.get(url)
        time.sleep(2)
        try:
            img_tag = driver.find_element(By.CSS_SELECTOR, ".page-image img")
            img_url = img_tag.get_attribute("src")
            if img_url:
                filename = f"{publication_name}_{today}_{i}.png"
                save_path = output_dir / filename
                img_data = session.get(img_url).content
                with open(save_path, 'wb') as f:
                    f.write(img_data)
                print(f"✅ Downloaded: {save_path}")
            else:
                print(f"⚠️ Page {i}: Image src missing.")
        except Exception as e:
            print(f"❌ Failed to download page {i}: {e}")

    driver.quit()

# ====== Main ======
def main():
    try:
        print("🔐 Logging in...")
        cookies = login_and_get_cookies()
        print("✅ Login successful. Starting download...")
        scrape_pages(cookies)
        print("🎉 All pages downloaded successfully. Exiting now.")
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()

