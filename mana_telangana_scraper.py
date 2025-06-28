import os
import time
import requests
import urllib.parse
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from twocaptcha import TwoCaptcha
from webdriver_manager.chrome import ChromeDriverManager

# ─── CONFIG ────────────────────────────────────────────────────────────────────
TWO_CAPTCHA_API_KEY    = "bd9495e9ce0b356f189274f82089e7a7"
HOME_URL               = "https://epaper.manatelangana.news/"
DOWNLOAD_DIR           = os.path.join(os.getcwd(), "downloads", "mana_telangana")
CAPTCHA_POLL_INTERVAL  = 5   # seconds between 2Captcha polls
EDITION = "Hyderabad"

# ─── derive calendar date and create folder ───────────────────────────────────
date_str     = datetime.now().strftime("%Y-%m-%d")
date_folder  = os.path.join(DOWNLOAD_DIR, EDITION.lower())
os.makedirs(date_folder, exist_ok=True)

def main():
    # 1) Launch Chrome (maximized)
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--headless=new")
    service = Service(ChromeDriverManager().install())
    driver  = webdriver.Chrome(service=service, options=options)
    wait    = WebDriverWait(driver, 25)

    try:
        # 2) Go to homepage
        driver.get(HOME_URL)

        # 3) Click the Hyderabad edition using stable selector
        hyderabad_link = wait.until(EC.element_to_be_clickable((
            By.CSS_SELECTOR, 'a[href*="/edition/HYDERABAD"]'
        )))
        hyderabad_link.click()

        # 4) Handle possible new tab
        time.sleep(2)
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[1])

        # 5) Click “Read Now” (first /read/r/… link)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href*="/read/r/"]'))).click()

        # 6) Click the download-PDF button in the reader panel
        dl_btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#epaper-box a.download-pdf")))
        driver.execute_script("arguments[0].scrollIntoView(true);", dl_btn)
        driver.execute_script("arguments[0].click();", dl_btn)
        print("✅ Download button clicked — now on the CAPTCHA page.")

        # 7) Wait for reCAPTCHA widget & grab sitekey
        captcha_div = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.g-recaptcha[data-sitekey]")))
        sitekey = captcha_div.get_attribute("data-sitekey")
        print(f"[+] Found sitekey: {sitekey}")

        # 8) Solve with 2Captcha (with retry)
        solver = TwoCaptcha(TWO_CAPTCHA_API_KEY)
        for attempt in range(3):
            try:
                print("[+] Sending CAPTCHA to 2Captcha…")
                result = solver.recaptcha(
                    sitekey=sitekey,
                    url=driver.current_url,
                    polling_interval=CAPTCHA_POLL_INTERVAL
                )
                token = result["code"]
                print(f"[+] CAPTCHA solved: {token[:10]}…")
                break
            except Exception as e:
                print(f"[!] CAPTCHA solve attempt {attempt + 1} failed: {e}")
                time.sleep(10)
        else:
            raise RuntimeError("❌ Failed to solve CAPTCHA after 3 attempts")

        # 9) Inject token & invoke callback
        driver.execute_script("""
            document.getElementById('g-recaptcha-response').style.display = 'block';
            document.getElementById('g-recaptcha-response').value = arguments[0];
            window.captchaCallback(arguments[0]);
        """, token)

        # 10) Wait for “Download full Newspaper” link
        link_el = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.fullpdflink")))
        pdf_page_url = link_el.get_attribute("href")
        print(f"[+] PDF page URL: {pdf_page_url!r}")

    finally:
        time.sleep(2)
        driver.quit()

    # 11) Extract real PDF URL from token param
    parsed     = urllib.parse.urlparse(pdf_page_url)
    token_vals = urllib.parse.parse_qs(parsed.query).get("token", [])
    if not token_vals:
        raise RuntimeError("Couldn't extract token from PDF URL")
    real_pdf_url = urllib.parse.unquote(token_vals[0])
    print(f"[+] Real PDF URL: {real_pdf_url}")

    # 12) Download via requests
    pdf_name      = f"manatelangana_{date_str}.pdf"
    download_path = os.path.join(date_folder, pdf_name)
    print("[+] Downloading PDF via requests…")
    resp = requests.get(real_pdf_url, stream=True)
    resp.raise_for_status()
    with open(download_path, "wb") as f:
        for chunk in resp.iter_content(1024*64):
            f.write(chunk)
    print(f"[+] PDF saved to {download_path}")

if __name__ == "__main__":
    main()
