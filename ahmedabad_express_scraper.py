"""Multi Page PDF Downloader for Ahmedabad Express Newspaper"""

import os
import requests
from datetime import datetime
from urllib.parse import urljoin

def download_newspaper():
    # Publication name
    publication_name = "ahmedabad_express"

    # Get today's date
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    output_date = today.strftime("%Y%m%d")
    edition_name = "ahmedabad"  # Edition name can be customized if needed
    # Construct directory structure: Ahemdabad Express/{date}
    base_dir = os.path.join(os.getcwd(), 'downloads', publication_name, edition_name)
    os.makedirs(base_dir, exist_ok=True)

    # Construct PDF filename: Ahemdabad Express_{date}.pdf
    pdf_filename = f"{publication_name}_{output_date}.pdf"

    # URL of the PDF
    base_url = "https://www.ahmedabadexpress.com/newspaper-pdf/"
    pdf_url = urljoin(base_url, f"{date_str}.pdf")

    # Configure headers to mimic browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # Download PDF
        response = requests.get(pdf_url, headers=headers, timeout=10)
        response.raise_for_status()

        # Save file
        save_path = os.path.join(base_dir, pdf_filename)
        with open(save_path, 'wb') as f:
            f.write(response.content)
        
        print(f"Successfully downloaded newspaper to: {save_path}")

    except requests.exceptions.HTTPError as errh:
        print(f"HTTP Error ({pdf_url}): {errh}")
    except requests.exceptions.ConnectionError as errc:
        print(f"Connection Error: {errc}")
    except requests.exceptions.Timeout as errt:
        print(f"Timeout Error: {errt}")
    except Exception as err:
        print(f"An error occurred: {err}")

if __name__ == "__main__":
    download_newspaper()
