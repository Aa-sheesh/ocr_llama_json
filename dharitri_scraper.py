from datetime import datetime

import requests
from bs4 import BeautifulSoup
import os

# Step 1: Load the main page
BASE_URL = "https://dharitriepaper.in"  # Replace this with the real start page
response = requests.get(BASE_URL)
soup = BeautifulSoup(response.text, "html.parser")
# Step 2: Find all <a> with class including "thumbnail epost-image float..."
links = []
for a in soup.find_all(
    "a", class_=lambda c: c and "thumbnail" in c and "epost-image" in c
):
    href = a.get("href")
    print(f"Found edition: {href}")
    if href and "edition/" in href:  # Changed to match any edition
        full_url = requests.compat.urljoin(BASE_URL, href)
        links.append(full_url)

print(f"Found {len(links)} edition links to process.")
paper_name = "dharitri"
# Step 3: Visit each edition page and find the PDF download link
downloaded = 0
# os.makedirs(paper_name, exist_ok=True)
str_date = datetime.now().strftime("%Y-%m-%d")
date_dir = os.path.join(paper_name, str_date)
for url in links:
    try:
        edition_name = url.split("/")[-1]
        print(f"\nProcessing edition: {url}")
        res = requests.get(url)
        sub_soup = BeautifulSoup(res.text, "html.parser")

        # Look for dropdown menu containing PDF link
        download_menu = sub_soup.find(class_="btn-group")
        if not download_menu:
            print(f"No download menu found on {url}")
            continue

        # Find PDF link inside the dropdown menu
        pdf_a = download_menu.find("a", href=True, text=lambda t: t and "Full PDF" in t)
        if not pdf_a:
            print(f"No PDF link found on {url}")
            continue

        pdf_url = pdf_a["href"]
        pdf_url = requests.compat.urljoin(url, pdf_url)
        print(f"Downloading PDF from: {pdf_url}")
        # Download the PDF
        pdf_data = requests.get(pdf_url)
        script_dir = os.getcwd()
        edition_dir = os.path.join(script_dir, 'downloads',paper_name,edition_name)
        os.makedirs(edition_dir, exist_ok=True)
        file_name = f"{paper_name}_{str_date}.pdf"
        file_path = os.path.join(edition_dir, file_name)

        # Changed filename to be more descriptive

        with open(file_path, "wb") as f:
            f.write(pdf_data.content)

        print(f"Successfully downloaded: {file_path}")
        downloaded += 1

    except Exception as e:
        print(f"Error processing {url}: {e}")

print(
    f"\nDownload complete. Downloaded {downloaded} PDFs out of {len(links)} editions."
)
