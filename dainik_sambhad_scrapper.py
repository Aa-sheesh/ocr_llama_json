import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from pdf2image import convert_from_path
import os
import shutil

# === CONFIGURATION ===
publication_name = "dainik_sambad"
edition_name = "agartala"
base_folder = Path('downloads') / publication_name.lower() /edition_name.lower() / "pdfs"

# Step 1: Fetch and parse homepage
URL = "https://www.dainiksambad.net/"
res = requests.get(URL)
soup = BeautifulSoup(res.text, "html.parser")

# Step 2: Extract date and format
date_text = soup.find("div", class_="topcol1").get_text(strip=True)
date_parts = date_text.split(",")
date_string = f"{date_parts[1].strip()} {date_parts[2].strip()}"  # "05 June 2025"
parsed_date = datetime.strptime(date_string, "%d %B %Y")
date_str = parsed_date.strftime("%d%m%Y")  # "05062025"

# Step 3: Get number of pages
select = soup.find("select", attrs={"onchange": "pagechange(this.value)"})
num_pages = len(select.find_all("option"))

# Step 4: Prepare folder
base_folder.mkdir(parents=True, exist_ok=True)

# Step 5: Download PDFs and convert to PNG
base_url = f"https://dainiksambad.net/epaperimages/{date_str}"

for i in range(1, num_pages + 1):
    pdf_url = f"{base_url}/PAGE-{i}.PDF"
    pdf_path = base_folder / f"page_{i}.pdf"
    
    try:
        # Download PDF
        r = requests.get(pdf_url)
        r.raise_for_status()
        with open(pdf_path, "wb") as f:
            f.write(r.content)
        print(f"✅ Downloaded: PAGE-{i}.pdf")

        # Convert PDF to image
        images = convert_from_path(str(pdf_path), dpi=400)
        for img_index, img in enumerate(images):
            image_filename = f"{publication_name.lower().replace(' ', '_')}_{edition_name.lower()}_{date_str}_{i}.png"
            image_path = base_folder.parent / image_filename
            img.save(image_path, "PNG")
            print(f"🖼️  Saved image: {image_path.name}")
        
        # Delete the original PDF
        os.remove(pdf_path)
        print(f"🗑️  Deleted PDF: {pdf_path.name}")
        
    except Exception as e:
        print(f"❌ Failed PAGE-{i}: {e}")


shutil.rmtree(base_folder)