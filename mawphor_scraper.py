"""single page multiple pdfs - Mawphor/20250531/Mawphor202505311.pdf
"""

import os
import time
import requests
import sys
import argparse
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def main():
    parser = argparse.ArgumentParser(description='Mawphor Crawler')
    parser.add_argument('--notify', action='store_true', help='Send notification to gateway after crawling')
    args = parser.parse_args()
    
    # Step 1: Setup date and output path structure
    publication_name = "Mawphor"
    date_str = datetime.today().strftime('%Y%m%d')
    
    # Set base directory for downloads - consistent with other crawlers
    base_dir = "downloads/mawphor"
    output_dir = Path(base_dir) / date_str
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 2: Setup Selenium WebDriver
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        # Step 3: Open the e-paper page
        driver.get("https://mawphor.com/e-paper/")
        time.sleep(2)

        # Step 4: Locate all <a> tags under the e-paper container
        content_div = driver.find_element(By.CLASS_NAME, "entry-content")
        page_links = content_div.find_elements(By.TAG_NAME, "a")

        print(f"🔍 Found {len(page_links)} page links. Starting download...")

        # Step 5: Loop through each link and download the PDF
        downloaded_files = []
        for idx, link in enumerate(page_links, start=1):
            pdf_url = link.get_attribute("href")
            filename = f"{publication_name}{date_str}{idx}.pdf"
            file_path = output_dir / filename

            print(f"⬇️ Downloading {filename} from {pdf_url} ...")

            try:
                response = requests.get(pdf_url, timeout=10)
                response.raise_for_status()
                with open(file_path, "wb") as f:
                    f.write(response.content)
                print(f"✅ Saved to {file_path}")
                downloaded_files.append(str(file_path))
            except Exception as e:
                print(f"❌ Failed to download {pdf_url} — {e}")

    finally:
        driver.quit()
        print("🧹 Browser closed. Script finished.")
    
    # Process PDFs to images and optionally notify gateway
    if downloaded_files:
        print(f"✅ Downloaded {len(downloaded_files)} PDFs")
    
    # Process PDFs using universal processor
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from universal_pdf_processor import process_mawphor
        
        print("\n🔄 Processing downloaded PDFs to images...")
        success = process_mawphor(notify=args.notify)
        
        if success:
            print("✅ Successfully processed Mawphor PDFs")
            if args.notify:
                print("✅ Gateway notification sent")
        else:
            print("❌ Failed to process Mawphor PDFs")
            
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
                # Get publication info for Mawphor
                publication_info = config.get("downloads/mawphor", {
                    "publicationName": "Mawphor",
                    "editionName": "Imphal",
                    "languageName": "Manipuri",
                    "zoneName": "East"
                })
                
                # Create newspaper_config dictionary
                newspaper_config = {"mawphor": publication_info}
                
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


def process_pdfs_to_images(pdf_files, publication_name, date_str):
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
            date_obj = datetime.strptime(date_str, "%Y%m%d")
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
                    publication_name.lower(),  # edition_name
                    formatted_date,
                    "imphal"  # edition_city
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
