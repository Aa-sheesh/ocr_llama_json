import asyncio
from pathlib import Path
import requests
from PIL import Image
from playwright.async_api import async_playwright
import datetime

# === CONFIG ===
publication_name = "sakshi"
edition_name = "Hyderabad"
today = datetime.datetime.now()
date_str = today.strftime("%Y-%m-%d")
date_url_str = today.strftime("%d/%m/%Y")

START_URL = (
    f"https://epaper.sakshi.com/Hyderabad_Main"
    f"?eid=123&edate={date_url_str}"
)

# === PATH SETUP ===
BASE_DIR = Path(f"downloads/{publication_name}/{edition_name.lower()}")
BASE_DIR.mkdir(parents=True, exist_ok=True)
PDF_PATH = BASE_DIR / f"{publication_name}_{date_str}.pdf"

def download_image(img_url, save_path):
    r = requests.get(img_url, stream=True)
    r.raise_for_status()
    with open(save_path, "wb") as f:
        for chunk in r.iter_content(1024):
            f.write(chunk)
    print(f"✅ Downloaded: {save_path.name}")

def convert_to_pdf(image_paths, pdf_path):
    images = [Image.open(p).convert("RGB") for p in image_paths]
    images[0].save(pdf_path, save_all=True, append_images=images[1:])
    print(f"📄 PDF created: {pdf_path}")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(START_URL, wait_until="load")

        # Hide GDPR popup if present
        try:
            await page.evaluate("document.getElementById('gdpr').style.display = 'none'")
        except:
            pass

        image_paths = []
        seen_urls = set()

        for page_num in range(1, 50):
            try:
                # Wait for image container to appear
                await page.wait_for_selector("#ImageContainerDiv", timeout=10000)

                # Extract image src directly from #imgmain1
                img_url = await page.evaluate("document.querySelector('#imgmain1')?.getAttribute('src')")

                if not img_url or img_url in seen_urls:
                    print("✅ Done: No new page or duplicate.")
                    break

                seen_urls.add(img_url)
                filename = f"{publication_name}{date_str.replace('-', '')}{page_num:02}.png"
                
                img_path = BASE_DIR / filename
                download_image(img_url, img_path)
                image_paths.append(img_path)

                # Go to next page
                await page.click("#Next_Page")
                await page.wait_for_timeout(1500)

            except Exception as e:
                print(f"❌ Error on page {page_num}: {e}")
                await page.screenshot(path=f"error_page_{page_num}.png", full_page=True)
                break

        await browser.close()

        # if image_paths:
        #     convert_to_pdf(image_paths, PDF_PATH)
        # else:
        #     print("❌ No pages downloaded.")

if __name__ == "__main__":
    asyncio.run(main())
