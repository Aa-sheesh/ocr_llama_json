#output_formate:Single Page Multiple PDFs

import requests
import os
import sys
import argparse
from datetime import datetime


def download_pdfs(base_url_pattern, publication_name, date, base_dir,
                  start_page=1, max_page=20):
    # Create base folder like 'downloads/sanaleibak/29-05-2025'
    save_folder = os.path.join(base_dir, date)
    os.makedirs(save_folder, exist_ok=True)

    downloaded_files = []
    for page_num in range(start_page, max_page + 1):
        pdf_url = base_url_pattern.format(page_num)
        # filename format: {publication_name}{date}{page_number}.pdf
        file_name = f"{publication_name}{date.replace('-', '')}{page_num}.pdf"
        file_path = os.path.join(save_folder, file_name)

        print(f"Downloading page {page_num} from {pdf_url} ...")

        try:
            response = requests.get(pdf_url, timeout=10)
            if response.status_code == 200:
                with open(file_path, "wb") as f:
                    f.write(response.content)
                print(f"Saved: {file_path}")
                downloaded_files.append(file_path)
            else:
                print(
                    f"Page {page_num} not found (HTTP {response.status_code}). Stopping download.")
                break  # Stop if page not found, assuming no further pages

        except requests.RequestException as e:
            print(f"Failed to download page {page_num}: {e}")
            break

    print("Download process finished.")
    
    # Convert PDFs to images and cleanup like epaperset2.py
    if downloaded_files:
        process_pdfs_to_images(downloaded_files, publication_name, date)
    
    return downloaded_files


def main():
    parser = argparse.ArgumentParser(description='Sanaleibak Crawler')
    parser.add_argument('--notify', action='store_true', help='Send notification to gateway after crawling')
    args = parser.parse_args()
    
    publication_name = "sanaleibak"

    # Get today's date in dd-mm-yyyy format
    today_date = datetime.today().strftime("%d-%m-%Y")

    # Set base directory for downloads - consistent with other crawlers
    base_dir = "downloads/sanaleibak"

    # Construct base_url pattern with today's date inside
    base_url = f"https://sanaleibak.in/wp-content/uploads/{datetime.today().year}/" \
               f"{datetime.today().strftime('%m')}/Page-{{}}-{today_date}.pdf"

    # Adjust max_page as needed
    downloaded_files = download_pdfs(base_url_pattern=base_url,
                                   publication_name=publication_name,
                                   date=today_date,
                                   base_dir=base_dir,
                                   max_page=50)
    
    # Process PDFs using universal processor
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from universal_pdf_processor import process_sanaleibak
        
        print("\n🔄 Processing downloaded PDFs to images...")
        success = process_sanaleibak(notify=args.notify)
        
        if success:
            print("✅ Successfully processed Sanaleibak PDFs")
            if args.notify:
                print("✅ Gateway notification sent")
        else:
            print("❌ Failed to process Sanaleibak PDFs")
            
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
                # Get publication info for Sanaleibak
                publication_info = config.get("downloads/sanaleibak", {
                    "publicationName": "Sanaleibak",
                    "editionName": "Imphal",
                    "languageName": "Manipuri",
                    "zoneName": "East"
                })
                
                # Create newspaper_config dictionary
                newspaper_config = {"sanaleibak": publication_info}
                
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


def process_pdfs_to_images(pdf_files, publication_name, date):
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
            date_obj = datetime.strptime(date, "%d-%m-%Y")
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


