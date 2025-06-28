"""Single Page Multiple PDFs - {publication_name}/{date}/({publication_name}{date}{page_number}.pdf)s
"""
"""the only issue in the downloading of this epaper is that few pages are not available on the server, for example, if the epaper has 12 pages, then page 1,2,3,4,5,6,7,8 are available but page 9,10,11,12 does not load in the main site."""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from pathlib import Path
import os
import time
import re
import requests
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description='Suvarna Times of Karnataka Crawler')
    parser.add_argument('--notify', action='store_true', help='Send notification to gateway after crawling')
    args = parser.parse_args()

    # Setup WebDriver (headless)
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    driver = webdriver.Chrome(service=Service(), options=options)

    # Open website
    url = "http://suvarnatimesofkarnataka.com/"
    driver.get(url)

    # Wait for elements
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.newspapers.rbrd.shd b"))
        )
    except Exception as e:
        print("❌ Timeout waiting for page elements:", e)
        driver.quit()
        exit(1)

    # Extract PDF identifiers
    page_buttons = driver.find_elements(By.CSS_SELECTOR, "div.newspapers.rbrd.shd b")
    pdf_ids = []
    date_code = None
    for btn in page_buttons:
        onclick = btn.get_attribute("onclick")
        match = re.search(r"edn\('(\d+)',\s*(\d+)\)", onclick)
        if match:
            date_code = match.group(1)
            page_num = int(match.group(2))
            pdf_ids.append(page_num)

    driver.quit()

    if not pdf_ids or not date_code:
        raise Exception("Failed to extract PDF links or date code from page.")

    total_pages = sorted(set(pdf_ids))
    print(f"📰 Date Code Detected: {date_code}")
    print(f"📄 Total Pages Found: {len(total_pages)}")

    # Prepare output directory
    publication_name = "Suvarna_Times_of_Karnataka"
    today_str = datetime.today().strftime("%Y%m%d")
    
    # Set base directory for downloads - consistent with other crawlers
    base_dir = "downloads/suvarna_times_of_karnataka"
    output_dir = Path(base_dir) / today_str
    output_dir.mkdir(parents=True, exist_ok=True)

    # Headers for request
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "application/pdf,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "http://suvarnatimesofkarnataka.com/",
        "Connection": "keep-alive"
    }

    RETRY_COUNT = 3
    RETRY_DELAY = 5
    base_url = f"https://suvarnatimesofkarnataka.com/{date_code}"

    # Download PDFs
    downloaded_files = []
    for page in total_pages:
        pdf_url = f"{base_url}/p{page}.pdf"
        filename = f"{publication_name}{today_str}{page}.pdf"
        file_path = output_dir / filename

        for attempt in range(1, RETRY_COUNT + 1):
            try:
                print(f"⬇️ Attempt {attempt}: Downloading Page {page} from {pdf_url}")
                response = requests.get(pdf_url, headers=headers, stream=True, timeout=15)
                if response.status_code == 200:
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    print(f"✅ Saved: {file_path}")
                    downloaded_files.append(str(file_path))
                    break
                elif response.status_code == 404:
                    print(f"❌ Page {page} not found (HTTP 404) – skipping.")
                    break
                else:
                    print(f"⚠️ Failed Page {page} - HTTP {response.status_code}")
            except Exception as e:
                print(f"❌ Error downloading Page {page}: {e}")
            if attempt < RETRY_COUNT:
                time.sleep(RETRY_DELAY)

    print("🎉 All available PDFs have been downloaded.")
    
    # Convert PDFs to images and cleanup like epaperset2.py
    if downloaded_files:
        process_pdfs_to_images(downloaded_files, publication_name, today_str)
    
    # Process PDFs using universal processor
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from universal_pdf_processor import process_suvarna_times
        
        print("\n🔄 Processing downloaded PDFs to images...")
        success = process_suvarna_times(notify=args.notify)
        
        if success:
            print("✅ Successfully processed Suvarna Times PDFs")
            if args.notify:
                print("✅ Gateway notification sent")
        else:
            print("❌ Failed to process Suvarna Times PDFs")
            
    except Exception as e:
        print(f"❌ Error processing PDFs: {e}")
        import traceback
        traceback.print_exc()
    
    # Legacy notification code (kept for reference but not used)
    if False and args.notify:
        try:
            # Import and call the notification function (same as epaperset2.py)
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from notify_gateway import process_newspaper_directory
            from config import config
            
            # Path to the newspaper_images directory (same as epaperset2.py)
            is_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER')
            if is_docker:
                newspaper_images_dir = "/app/newspaper_images"
            else:
                newspaper_images_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "newspaper_images")
            
            if os.path.exists(newspaper_images_dir):
                # Get publication info for Suvarna Times
                publication_info = config.get("downloads/suvarna_times", {
                    "publicationName": "Suvarna Times of Karnataka",
                    "editionName": "Bangalore",
                    "languageName": "Kannada",
                    "zoneName": "South"
                })
                
                # Create newspaper_config dictionary
                newspaper_config = {"suvarna_times": publication_info}
                
                # Process the newspaper_images directory (same as epaperset2.py)
                success = process_newspaper_directory(newspaper_images_dir, newspaper_config)
                if success:
                    print("Successfully notified gateway")
                else:
                    print("Failed to notify gateway")
            else:
                print(f"Newspaper images directory not found: {newspaper_images_dir}")
        except Exception as e:
            print(f"Error notifying gateway: {e}")


def process_pdfs_to_images(pdf_files, publication_name, today_str):
    """Convert PDFs to images and delete originals, following epaperset2.py pattern"""
    try:
        # Import the PDF to image conversion function
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from pdf_to_image import convert_pdf_pages_to_images
        
        # Create common storage directory for images (same as epaperset2.py)
        is_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER')
        
        if is_docker:
            common_storage_dir = "/app/newspaper_images"
        else:
            common_storage_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "newspaper_images")
            
        os.makedirs(common_storage_dir, exist_ok=True)
        
        # Convert date format for images (YYYY-MM-DD)
        try:
            from datetime import datetime
            date_obj = datetime.strptime(today_str, "%Y%m%d")
            formatted_date = date_obj.strftime("%Y-%m-%d")
        except ValueError:
            formatted_date = datetime.today().strftime("%Y-%m-%d")
        
        print(f"Converting {len(pdf_files)} PDFs to images in {common_storage_dir}")
        
        for pdf_path in pdf_files:
            try:
                # Convert PDF to images
                image_paths = convert_pdf_pages_to_images(
                    pdf_path,
                    common_storage_dir,
                    "suvarna_times",  # edition_name
                    formatted_date,
                    "bangalore"  # edition_city
                )
                
                if image_paths:
                    print(f"Successfully converted {pdf_path} to {len(image_paths)} images")
                    
                    # Delete the original PDF file after conversion
                    try:
                        os.remove(pdf_path)
                        print(f"Deleted original PDF file: {pdf_path}")
                    except Exception as e:
                        print(f"Failed to delete original PDF file {pdf_path}: {e}")
                else:
                    print(f"Failed to convert {pdf_path} to images")
                    
            except Exception as e:
                print(f"Error converting PDF {pdf_path} to images: {e}")
                
    except Exception as e:
        print(f"Error in process_pdfs_to_images: {e}")


if __name__ == "__main__":
    main()
