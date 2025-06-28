import os
import time
import json
import logging
import hashlib
import requests
import urllib3
from datetime import datetime
from shutil import rmtree
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure retry session
session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount('https://', HTTPAdapter(max_retries=retries))
session.mount('http://', HTTPAdapter(max_retries=retries))


class NewspaperDownloader:
    def __init__(self):
        self.driver = self._initialize_driver()
        self.today = datetime.now().strftime("%d/%m/%Y")
        self.publication_name = "namasthe_telangana"
        self.edition_name = "Hyderabad_Main"
        self.base_dir = os.path.join(self.publication_name)
        self.articles_dir = os.path.join(self.base_dir, self.edition_name, "articles")
        self.action_chains = ActionChains(self.driver)

    def _initialize_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")  # ✅ Headless mode
        chrome_options.add_argument("--window-size=1920x1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            })
            return driver
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise

    def _create_directory(self, path):
        os.makedirs(path, exist_ok=True)

    def _download_image(self, url, filepath, referer=None):
        if "ShareImage" in url and "Pictureid=" not in url:
            logger.warning(f"Skipping invalid-looking URL: {url}")
            return False

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Referer': referer or 'https://epaper.ntnews.com/'
            }

            response = session.get(url, headers=headers, stream=True, timeout=10, verify=False)

            if not response.ok or 'image' not in response.headers.get('Content-Type', ''):
                logger.warning(f"Bad response or not an image: {url}")
                return False

            with open(filepath, 'wb') as f:
                f.write(response.content)

            if os.path.getsize(filepath) < 1024:
                os.remove(filepath)
                logger.warning(f"Downloaded image too small: {filepath}")
                return False

            logger.info(f"Downloaded image: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return False

    def _get_page_data(self):
        try:
            dropdown = WebDriverWait(self.driver, 15).until(EC.element_to_be_clickable((By.ID, "ddl_Pages")))
            options = dropdown.find_elements(By.TAG_NAME, "option")
            pages = [{
                'value': opt.get_attribute("value"),
                'pgno': opt.get_attribute("pgno"),
                'highres': opt.get_attribute("highres"),
                'xhighres': opt.get_attribute("xhighres"),
                'pageid': opt.get_attribute("value")
            } for opt in options]
            return pages
        except Exception as e:
            logger.error(f"Failed to get page data: {e}")
            return []

    def _extract_articles_from_page(self, page_data):
        try:
            time.sleep(2)
            elements = WebDriverWait(self.driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.pagerectangle"))
            )
            articles = []
            for el in elements:
                style = el.get_attribute("style")
                styles = [s.split(':')[-1].strip() for s in style.split(';') if ':' in s][:4]
                article = {
                    'storyid': el.get_attribute('storyid'),
                    'orgid': el.get_attribute('orgid'),
                    'pageid': page_data['pageid'],
                    'page_number': page_data['pgno'],
                    'position': dict(zip(['top', 'left', 'width', 'height'], styles)),
                    'url': f"https://epaper.ntnews.com/Home/ShareArticle?OrgId={el.get_attribute('orgid')}&eid=1&imageview=1"
                }
                articles.append(article)
            return articles
        except Exception as e:
            logger.error(f"Error extracting articles: {e}")
            return []

    def _download_article_image(self, article):
        try:
            page_number = article['page_number']
            article_number = article['storyid']
            page_dir = os.path.join(self.articles_dir, f"page_{page_number}")
            self._create_directory(page_dir)

            filename = os.path.join(
                page_dir,
                f"{self.publication_name}_{self.edition_name}_{page_number}_{article_number}.jpg"
            )

            if os.path.exists(filename) and os.path.getsize(filename) > 1024:
                logger.info(f"Article already downloaded: {filename}")
                return True

            self.driver.get(article['url'])
            WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, "downloadImage")))

            try:
                img = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "img[src*='ntfs.avahan.net']"))
                )
                img_url = img.get_attribute("src")
                return self._download_image(img_url, filename, article['url'])
            except Exception:
                fallback_url = f"https://epaper.ntnews.com/Home/ShareImage?Pictureid={article['orgid']}"
                return self._download_image(fallback_url, filename, article['url'])

        except Exception as e:
            logger.error(f"Error downloading article: {e}")
            return False

    def _process_page(self, page):
        try:
            edition_dir = os.path.join(self.base_dir, self.edition_name)
            self._create_directory(edition_dir)

            img_url = page.get('xhighres') or page.get('highres')
            if img_url:
                url_hash = hashlib.md5(img_url.encode()).hexdigest()[:8]
                fullpage_path = os.path.join(edition_dir, f"page_{page['pgno']}_{url_hash}.jpg")
                if not os.path.exists(fullpage_path):
                    self._download_image(img_url, fullpage_path)

            self.driver.get(
                f"https://epaper.ntnews.com/Home/FullPage?eid={page.get('eid')}&edate={self.today}&pgid={page['pageid']}")
            time.sleep(2)

            articles = self._extract_articles_from_page(page)
            for article in articles:
                self._download_article_image(article)

        except Exception as e:
            logger.error(f"Error processing page: {e}")

    def process_edition(self, edition_id):
        try:
            logger.info(f"Processing edition: {self.edition_name}")
            self.driver.get(f"https://epaper.ntnews.com/Home/FullPage?eid={edition_id}&edate={self.today}")
            WebDriverWait(self.driver, 15).until(lambda d: d.execute_script('return document.readyState') == 'complete')

            pages = self._get_page_data()
            for page in pages:
                page['eid'] = edition_id
                self._process_page(page)
        except Exception as e:
            logger.error(f"Error processing edition {self.edition_name}: {e}")

    def run(self):
        self._create_directory(self.articles_dir)
        logger.info(f"Starting NTNews scraper for {self.today}")

        self.process_edition(edition_id=1)

        logger.info("Download complete.")

        # ✅ Delete edition folder after run
        try:
            edition_path = os.path.join(self.base_dir, self.edition_name)
            if os.path.exists(edition_path):
                rmtree(edition_path)
                logger.info(f"Deleted edition folder: {edition_path}")
        except Exception as e:
            logger.warning(f"Failed to delete folder {edition_path}: {e}")

        self.driver.quit()


if __name__ == "__main__":
    downloader = NewspaperDownloader()
    downloader.run()
