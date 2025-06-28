import io, pathlib, re, time
from urllib.parse import urlencode, urljoin

import requests
from PIL import Image
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    from selenium.webdriver.chrome.service import Service
except ImportError:
    from selenium.webdriver.chrome.service import Service

from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ────── CONFIG ──────
HEADLESS = True
PUB = "the_sangai_express"
DOWNLOADS = "downloads"
EDITION_CODES = {
    "English": "Mpage",
    "Manipuri": "Mnppage"
}
# ───────────────────

IMG_CSS = "img.ui-draggable.ui-draggable-handle"
ZOOM_CSS = "button#zoom_btn"
CLOSE_CSS = "button#close_btn"

def make_driver(headless=True):
    opts = Options()
    opts.add_argument("--window-size=1920,1080")
    if headless:
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=opts
    )

def save_png(src_url, dest_path):
    if src_url.startswith("//"):
        src_url = "https:" + src_url
    r = requests.get(src_url, timeout=(60, 60))
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest_path, "PNG", quality=90)

def get_latest_info():
    url = "https://epaper.thesangaiexpress.com/"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        info = {}
        for lang, code in EDITION_CODES.items():
            regex = rf'<option\s+value="{code}"\s+data-pages="(\d+)"\s+data-date="([\d-]+)">'
            match = re.search(regex, r.text)
            if match:
                pages = int(match.group(1))
                date_str = match.group(2)
                info[lang] = (date_str, pages)
                print(f"🗓️  {lang} Edition → Date: {date_str}, Pages: {pages}")
        return info
    except Exception as e:
        print("❌ Failed to fetch edition info:", e)
    return {}

def download_edition(language, edition_code, date_str, last_page):
    print(f"\n📥 Downloading {language} Edition")

    IMG_PATTERN = re.compile(rf"{edition_code}_\d+\.(?:jpg|png)$", re.I)
    
    if language == "English":
        SAVE_ROOT = pathlib.Path(DOWNLOADS) / PUB /'imphal_english'
    else:
        SAVE_ROOT = pathlib.Path(DOWNLOADS) / PUB / 'imphal_meitei'

    driver = make_driver(HEADLESS)
    wait = WebDriverWait(driver, 20)

    try:
        for page in range(1, last_page + 1):
            dest = SAVE_ROOT / f"({PUB}_{language}_{date_str}_pg{page:02d}).png"
            if dest.exists():
                print(f"skip {page:02d} (already downloaded)")
                continue

            params = {"edition": edition_code, "date": date_str, "page": page}
            page_url = "https://epaper.thesangaiexpress.com/index.php?" + urlencode(params)
            print("→", page_url)
            driver.get(page_url)

            try:
                zoom_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ZOOM_CSS)))
            except TimeoutException:
                print(f"zoom button missing on page {page} → stopping")
                break
            zoom_btn.click()

            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                img_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, IMG_CSS)))
            except TimeoutException:
                print(f"No full-page image on page {page} → stopping")
                break

            src = img_el.get_attribute("src")
            if not src or "undefined" in src or not IMG_PATTERN.search(src):
                print(f"unexpected src on page {page}: {src} → skipping")
                continue

            print(f"found image: {src.split('/')[-1]}")
            save_png(urljoin(page_url, src), dest)
            print(f"✓ saved page {page:02d}")

            try:
                close_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, CLOSE_CSS)))
                close_btn.click()
                try:
                    wait.until(EC.invisibility_of_element(close_btn))
                except TimeoutException:
                    pass
            except TimeoutException:
                pass

            time.sleep(0.3)
    finally:
        driver.quit()
        print("✔️ Completed:", SAVE_ROOT.resolve())

if __name__ == "__main__":
    info = get_latest_info()
    for lang, (date_str, total_pages) in info.items():
        edition_code = EDITION_CODES[lang]
        download_edition(lang, edition_code, date_str, total_pages)
