import os
import time
import requests
from bs4 import BeautifulSoup
from PIL import Image  # Still useful if you want to validate image files
import urllib3
from urllib.parse import urljoin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://epaper.sangbadpratidin.in"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
}
PUBLICATION_NAME = 'sangbad_pratidin'
EDITION_NAME = "kolkata"
session = requests.Session()
session.headers.update(HEADERS)

def sanitize_filename(name):
    return "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).rstrip()

def get_editions():
    print("🌐 Fetching editions list...")
    resp = session.get(BASE_URL, verify=False)
    soup = BeautifulSoup(resp.text, "html.parser")

    edition_links = []
    ul = soup.find("ul", class_="supptabs2")
    if ul:
        for li in ul.find_all("li"):
            a_tag = li.find("a")
            if a_tag and a_tag.get("href"):
                href = a_tag["href"]
                name = a_tag.text.strip()
                full_url = urljoin(BASE_URL, href)
                edition_links.append((sanitize_filename(name), full_url))
    return edition_links

def download_edition(edition_name, base_url, max_pages=100):
    today = time.strftime("%Y_%m_%d")
    base_img_dir = os.path.join( 'downloads',PUBLICATION_NAME, EDITION_NAME)
    os.makedirs(base_img_dir, exist_ok=True)

    print(f"\n📖 Downloading edition: {edition_name}")
    for page_num in range(1, max_pages + 1):
        page_url = f"{base_url}/page/{page_num}" if page_num > 1 else base_url
        print(f"➡️  Page {page_num}: {page_url}")

        try:
            resp = session.get(page_url, timeout=15, verify=False)
            if resp.status_code != 200:
                print(f"❌ Page {page_num} not found. Stopping.")
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            img_tag = soup.find("img", {"id": "print_img"})

            if not img_tag or not img_tag.get("src"):
                print(f"⚠️ No image found on page {page_num}.")
                break

            img_url = img_tag["src"]
            img_data = session.get(img_url, timeout=15, verify=False)
            if img_data.status_code == 200:
                filename = os.path.join(
                    base_img_dir, f"sangbadpratidin_{today}_page_{page_num:03d}.jpg"
                )
                with open(filename, "wb") as f:
                    f.write(img_data.content)
                print(f"✅ Saved: {filename}")
            else:
                print(f"❌ Failed to download image for page {page_num}")
                break

            time.sleep(1)

        except Exception as e:
            print(f"⚠️ Error on page {page_num}: {e}")
            break

def main():
    editions = get_editions()
    print(f"\n🔍 Found {len(editions)} editions.")
    for name, url in editions:
        download_edition(name, url)

if __name__ == "__main__":
    main()
