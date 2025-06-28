#output dire: {publication_name}/{date}/({publication_name}{date}{page_number}{
# article{n}}.png)s


import os
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import time

# --------------------------- CONFIG ---------------------------

EMAIL = ""  # your email
PASSWORD = ""  # your password
BASE_URL = "https://epaper.punyanagari.in"
CITY = "Mumbai"
EDITION_CODE = "PNAGARI_PM"

# --------------------- SETUP SELENIUM -------------------------


def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    service = Service()
    return webdriver.Chrome(service=service, options=chrome_options)


# --------------------- LOGIN FUNCTION -------------------------


def login(driver, wait):
    driver.get(f"{BASE_URL}/login")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="email"]')))
    password_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]')))
    login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]')))

    email_input.send_keys(EMAIL)
    password_input.send_keys(PASSWORD)
    login_button.click()

    try:
        ok_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.swal2-confirm.swal2-styled"))
        )
        ok_button.click()
        time.sleep(2)
    except TimeoutException:
        pass

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.epaper-common-card-container")))
        driver.get(BASE_URL)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.epaper-common-card-container")))
    except TimeoutException:
        driver.save_screenshot("login_failed.png")
        raise


# --------------- GET TODAY'S DATE AND SETUP -------------------


def get_today():
    return datetime.now().strftime("%Y%m%d")


def get_edition_url(date, page=1):
    return f"{BASE_URL}/edition/{CITY}/{EDITION_CODE}/{EDITION_CODE}_{date}/page/{page}"


# ---------------- GET TOTAL PAGE COUNT ------------------------


def get_total_pages(driver, wait):
    try:
        driver.get(get_edition_url(get_today(), 1))
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.page-item button.page-link")))
        page_buttons = driver.find_elements(By.CSS_SELECTOR, "li.page-item button.page-link")
        return max([int(btn.text) for btn in page_buttons if btn.text.isdigit()])
    except:
        return 1


# ----------------- EXTRACT ARTICLE LINKS ----------------------


def extract_articles(driver, wait):
    try:
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.overlay")))
        overlays = driver.find_elements(By.CSS_SELECTOR, "div.overlay")
        return [div.get_attribute("id") for div in overlays if div.get_attribute("id")]
    except TimeoutException:
        return []


# ------------------ DOWNLOAD AN ARTICLE -----------------------


def download_article(driver, wait, article_id, date, page, output_dir, filename):
    article_url = f"{BASE_URL}/editionname/{CITY}/{EDITION_CODE}/page/{page}/article/{article_id}"
    driver.get(article_url)

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.epaper-header-actions img")))
        download_img = driver.find_element(By.CSS_SELECTOR, "div.epaper-header-actions img")
        img_url = download_img.get_attribute("src")

        response = requests.get(img_url)
        if response.status_code == 200:
            file_path = os.path.join(output_dir, filename)
            with open(file_path, "wb") as f:
                f.write(response.content)
            print(f"✅ Downloaded: {file_path}")
        else:
            print(f"❌ Failed to download image: {img_url}")
    except (NoSuchElementException, TimeoutException):
        print(f"⚠️ Failed to load/download article {article_id}")


# ------------------ MAIN SCRIPT FUNCTION ----------------------


def main():
    today = get_today()
    publication_name = "punyanagari"
    base_dir = os.path.join(publication_name, today)
    os.makedirs(base_dir, exist_ok=True)

    driver = setup_driver()
    wait = WebDriverWait(driver, 10)
    downloaded_articles = set()

    try:
        login(driver, wait)
        total_pages = get_total_pages(driver, wait)
        print(f"📄 Total pages: {total_pages}")

        for page in range(1, total_pages + 1):
            print(f"\n📄 Processing Page {page}/{total_pages}")
            driver.get(get_edition_url(today, page))
            time.sleep(2)

            # Scroll to load all articles
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            article_ids = extract_articles(driver, wait)
            print(f"📰 Found {len(article_ids)} articles on page {page}")

            for idx, article_id in enumerate(article_ids, start=1):
                if article_id in downloaded_articles:
                    continue
                downloaded_articles.add(article_id)

                ext = ".jpg"  # Assuming jpg, could be improved by checking URL extension if needed
                filename = f"{publication_name.lower()}{today}page{page}article{idx}{ext}"

                download_article(driver, wait, article_id, today, page, base_dir, filename)

    finally:
        driver.quit()
        print("\n✅ Done! All articles downloaded and organized by page.")


# -------------------------- RUN -------------------------------

if __name__ == "__main__":
    main()


