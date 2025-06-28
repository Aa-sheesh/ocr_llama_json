# Multi Page PDF

import os
import requests
import datetime
from PIL import Image
from io import BytesIO
from pathlib import Path

# === CONFIG ===
PAPER = "Sakal"
EDITION = "Mumbai"
SECTION = "Main"
EDITION_CODE = "DA"  # from HTML: DA, not MP

today = datetime.datetime.now().date()
date_str = today.strftime("%Y-%m-%d")
date_folder = today.strftime("%Y/%m/%d")
folder_name = f"{PAPER.lower()}/{EDITION.lower()}"
BASE_FOLDER = Path(folder_name)
BASE_FOLDER = Path("downloads") / BASE_FOLDER
BASE_FOLDER.mkdir(parents=True, exist_ok=True)
PDF_PATH = "downloads"/BASE_FOLDER / f"{PAPER}_{date_str}.pdf"

TILE_URL_PATTERN = (
    f"https://epaper-sakal-application.s3.ap-south-1.amazonaws.com/"
    f"EpaperData/{PAPER}/{EDITION}/{date_folder}/{SECTION}/"
    f"{PAPER}_{EDITION}_{date_str.replace('-', '_')}_{SECTION}_{EDITION_CODE}_{{page:03d}}/S/{{tile}}.jpg"
)

def download_tile(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGB")
    except Exception:
        print(f"❌ Failed: {url}")
        return None

def stitch_tiles(tiles):
    width, height = tiles[0].size
    stitched = Image.new("RGB", (width * 3, height * 3))
    for row in range(3):
        for col in range(3):
            idx = row * 3 + col
            stitched.paste(tiles[idx], (col * width, row * height))
    return stitched

def download_page(page_number):
    tiles = []
    for i in range(9):
        url = TILE_URL_PATTERN.format(page=page_number, tile=i)
        print(f"➡️ Downloading: {url}")
        img = download_tile(url)
        if img is None:
            return None
        tiles.append(img)
    return stitch_tiles(tiles)

def main():
    pages = []
    page_num = 1
    while True:
        print(f"📄 Processing page {page_num}")
        image = download_page(page_num)
        if image is None:
            break
        filename = f"{PAPER.lower()}{date_str.replace('-', '')}{page_num:02d}.png"
        img_path = BASE_FOLDER / filename
        image.save(img_path)
        pages.append(image)
        page_num += 1

    # if pages:
    #     print("🖨️ Creating PDF...")
    #     pages[0].save(PDF_PATH, save_all=True, append_images=pages[1:])
    #     print(f"✅ PDF saved at: {PDF_PATH}")
    # else:
    #     print("⚠️ No pages downloaded.")

if __name__ == "__main__":
    main()