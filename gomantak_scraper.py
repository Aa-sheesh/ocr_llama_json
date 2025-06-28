#Multi Page PDF

import os
import requests
import datetime
from PIL import Image
from io import BytesIO
from pathlib import Path

# === CONFIG ===
publication_name = "gomantak"
edition = "Goa"
today = datetime.datetime.now().date()
date_str = today.strftime("%Y-%m-%d")            # "2025-05-30"
folder_path = Path(f"downloads/{publication_name}/{edition.lower()}")
folder_path.mkdir(parents=True, exist_ok=True)

PDF_PATH = folder_path / f"{publication_name}_{date_str}.pdf"

TILE_URL_PATTERN = (
    f"https://epaper-sakal-application.s3.ap-south-1.amazonaws.com/"
    f"DainikGomantakEpaperData/DainikGomantak/GOA/{today.strftime('%Y/%m/%d')}/Main/"
    f"DainikGomantak_Goa_{date_str.replace('-', '_')}_Main_DA_{{page:03d}}/S/{{tile}}.jpg"
)

def download_tile(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGB")
    except Exception:
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
        img = download_tile(url)
        if img is None:
            print(f"❌ Missing tile: {url}")
            return None
        tiles.append(img)
    return stitch_tiles(tiles)

def main():
    pages = []
    saved_images = []
    page_num = 1
    while True:
        print(f"📥 Downloading page {page_num}")
        image = download_page(page_num)
        if image is None:
            break
        img_path = folder_path / f"page_{page_num:02d}.jpg"
        image.save(img_path)
        pages.append(image)
        saved_images.append(img_path)
        page_num += 1

    if pages:
        print("🖨️ Creating PDF...")
        pages[0].save(PDF_PATH, save_all=True, append_images=pages[1:])
        print(f"✅ PDF saved at: {PDF_PATH}")

        # 🔥 Delete image files
        for img_file in saved_images:
            try:
                img_file.unlink()
                print(f"🗑️ Deleted: {img_file}")
            except Exception as e:
                print(f"⚠️ Could not delete {img_file}: {e}")
    else:
        print("⚠️ No pages downloaded.")

if __name__ == "__main__":
    main()
