"""Clipped article images from Daily Excelsior ePaper"""

import time, json
from pathlib import Path
from datetime import datetime

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

class DailyExcelsiorScraper:
    def __init__(self):
        self.email         = 'Subscriptions@AAIZELTECH.com'
        self.password      = 'A@izel@123'
        self.login_url     = 'https://epaper.dailyexcelsior.com/login/loginpage'
        self.base_url      = 'https://epaper.dailyexcelsior.com'
        self.session       = requests.Session()
        self.driver        = None
        self.wait          = None

    def setup_driver(self):
        opts = Options()
        opts.add_argument('--no-sandbox')
        opts.add_argument('--headless=new')
        opts.add_argument('--disable-dev-shm-usage')
        opts.add_argument('--disable-blink-features=AutomationControlled')
        opts.add_argument('--disable-extensions')
        opts.add_argument('--window-size=1920,1080')
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option('useAutomationExtension', False)
        opts.add_argument(
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
        opts.add_experimental_option("prefs", {
            "download.prompt_for_download": False,
            "safebrowsing.enabled": True
        })

        try:
            self.driver = webdriver.Chrome(options=opts)
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            self.wait = WebDriverWait(self.driver, 30)
            print("✅ WebDriver ready")
            return True
        except WebDriverException as e:
            print(f"❌ WebDriver init failed: {e}")
            return False

    def login(self):
        print("🔐 Logging in...")
        self.driver.get(self.login_url)
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)

        email_field = self.wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "input[type='email'], #txtNumber1")
        ))
        email_field.clear()
        email_field.send_keys(self.email)

        password_field = self.wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "input[type='password'], #txtPassword")
        ))
        password_field.clear()
        password_field.send_keys(self.password)

        btn = self.wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button[type='submit'], .lrbtn")
        ))
        btn.click()
        time.sleep(5)

        if "login" not in self.driver.current_url.lower():
            print("✅ Logged in")
            return True
        print("❌ Login failed")
        return False

    def discover_pages(self, date_str=None):
        if not date_str:
            date_str = datetime.now().strftime("%d/%m/%Y")
        url = (
            f"{self.base_url}/JAMMU?eid=1&edate={date_str}"
            "&device=desktop&view=2&pgid=0"
        )
        self.driver.get(url)
        self.wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "img.lozad[data-index][pageid]")
        ))
        time.sleep(3)

        imgs = self.driver.find_elements(By.CSS_SELECTOR, "img.lozad[data-index][pageid]")
        pages, base = [], self.driver.current_url.split("&pgid=")[0]

        for img in imgs:
            try:
                idx = int(img.get_attribute("data-index"))
                pgid = img.get_attribute("pageid")
                pages.append({
                    "index": idx,
                    "page_id": pgid,
                    "url": f"{base}&pgid={pgid}"
                })
            except Exception as e:
                print(f"⚠️ Error processing image: {e}")
                continue

        pages.sort(key=lambda x: x["index"])
        print(f"📄 Found {len(pages)} pages (0…{pages[-1]['index']})")
        return pages

    def scrape_page_images(self, page_info):
        idx, pid = page_info["index"], page_info["page_id"]
        print(f"→ Page {idx} (pgid={pid})")
        self.driver.get(page_info["url"])
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)

        self.driver.execute_script("""
            let h = document.getElementById('main_menu') || document.querySelector('.nav_action_bar');
            if (h) h.style.display = 'none';
        """)
        time.sleep(1)

        rects = self.wait.until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "#ImageContainer .pagerectangle")
        ))
        rects = [r for r in rects if r.get_attribute("objtype") == "2"]
        print(f"🔍 {len(rects)} story rectangles found")

        clips = []
        for n, rect in enumerate(rects, start=1):
            print(f"  ▶ Processing rectangle {n}")
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", rect)
                time.sleep(1)

                original_tabs = self.driver.window_handles
                self.driver.execute_script("arguments[0].click();", rect)
                time.sleep(1)

                WebDriverWait(self.driver, 10).until(lambda d: len(d.window_handles) > len(original_tabs))
                new_tabs = self.driver.window_handles
                new_tab = [tab for tab in new_tabs if tab not in original_tabs][0]
                self.driver.switch_to.window(new_tab)

                try:
                    img = self.wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "#imgView img")
                    ))
                    src = img.get_attribute("src").strip()

                    if src and src not in [c["src"] for c in clips]:
                        clips.append({"src": src, "page_id": pid, "clip_index": n})
                        print(f"✅ Found clip #{n}: {src}")
                    else:
                        print(f"⚠️ Duplicate or empty src")

                except TimeoutException:
                    print(f"❌ Timeout: no image found in new tab")

                self.driver.close()
                self.driver.switch_to.window(original_tabs[0])
                time.sleep(0.5)

            except Exception as e:
                print(f"    ❌ Error processing rectangle: {e}")
                try:
                    self.driver.switch_to.window(self.driver.window_handles[0])
                except:
                    pass
                continue

        print(f"  ✅ Total clips found: {len(clips)}")
        return clips

    def download_image(self, clip, date_str, edition_name="srinagar", publication_name="daily_excelsior"):
        url, pid, idx = clip["src"], clip["page_id"], clip["clip_index"]

        date_obj = datetime.strptime(date_str, "%d/%m/%Y")
        date_folder = date_obj.strftime("%Y%m%d")

        folder_path = Path.cwd() / 'downloads' / publication_name / edition_name
        filename = f"{publication_name}_{date_folder}_page{pid}article{idx}.png"
        out = folder_path / filename

        cookies = {c["name"]: c["value"] for c in self.driver.get_cookies()}
        headers = {
            "Referer": self.driver.current_url,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            r = self.session.get(url, cookies=cookies, headers=headers, timeout=30)
            r.raise_for_status()

            folder_path.mkdir(parents=True, exist_ok=True)
            out.write_bytes(r.content)
            print(f"💾 Downloaded clip {idx} → {out}")
            return True
        except Exception as e:
            print(f"⚠️ Download failed {idx}: {e}")
            return False

    def scrape_date(self, date_str=None):
        if not date_str:
            date_str = datetime.now().strftime("%d/%m/%Y")

        total = downloaded = 0
        try:
            pages = self.discover_pages(date_str)
            for pg in pages:
                clips = self.scrape_page_images(pg)
                for clip in clips:
                    total += 1
                    if self.download_image(clip, date_str):
                        downloaded += 1
        except Exception as e:
            print(f"❌ Error during scraping: {e}")

        print(f"\n📊 Done: {downloaded}/{total} images downloaded")

    def cleanup(self):
        if self.driver:
            self.driver.quit()

def main():
    scraper = DailyExcelsiorScraper()
    if not scraper.setup_driver():
        return
    try:
        if not scraper.login():
            scraper.cleanup()
            return
        scraper.scrape_date(None)
        print("🎉 All done!")
    except Exception as e:
        print(f"❌ Error in main execution: {e}")
    finally:
        input("Press Enter to exit...")
        scraper.cleanup()

if __name__ == "__main__":
    main()
