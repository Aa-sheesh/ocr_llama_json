# output formate  {publication_name}/{date}/({publication_name}{date}{page_number}{article{n}}.png)s

import os
import asyncio
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from collections import defaultdict
from playwright.async_api import async_playwright
import re
from datetime import datetime

def download_image(url, save_path):
    try:
        r = requests.get(url, stream=True, timeout=10)
        if r.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
    except Exception as e:
        print(f"⚠️ Failed to download {url}: {e}")

def download_article_images(article_url, save_dir, publication_name, date_str, page_number, article_number):
    try:
        res = requests.get(article_url, timeout=10)
        if res.status_code != 200:
            return []
        soup = BeautifulSoup(res.text, 'html.parser')
        img_tags = soup.find_all('img')
        saved_imgs = []

        skip_keywords = ['logo', 'punyanagari', 'yashobhumi', 'mumbaichoufernew', '12.png']

        image_count = 1
        for img in img_tags:
            img_url = img.get('src')
            if not img_url or not img_url.startswith("http"):
                continue

            filename = os.path.basename(img_url.split("?")[0])
            if any(kw in filename.lower() for kw in skip_keywords):
                continue

            # New filename format:
            # ({publication_name}{date}{page_number}{article_number}{image_count}).png
            new_filename = f"({publication_name}{date_str}{page_number}{article_number}{image_count}).png"
            path = os.path.join(save_dir, new_filename)

            download_image(img_url, path)
            saved_imgs.append(path)

            image_count += 1

        return saved_imgs
    except Exception as e:
        print(f"⚠️ Error processing article {article_url}: {e}")
        return []

async def scrape():
    all_data = defaultdict(list)
    base_url = "https://www.mumbaichoufer.com/view/842/mumbai-choufer"
    publication_name = "mumbaichoufer"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(base_url)
        await page.wait_for_selector("ul.epaper-pagination")

        # Extract dynamic date from the page - example: from some visible text or meta tag
        # As an example, let's try to extract date from the title or header text
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')

        date_str = None
        # Example: Look for a date pattern in the page header or title
        # You need to adapt this if you find a better element on your site
        title_text = soup.title.string if soup.title else ""
        # Match date like DD/MM/YYYY or DD-MM-YYYY
        match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', title_text)
        if match:
            # Convert date to YYYYMMDD format
            try:
                dt = datetime.strptime(match.group(1), "%d/%m/%Y")
            except ValueError:
                try:
                    dt = datetime.strptime(match.group(1), "%d-%m-%Y")
                except ValueError:
                    dt = None
            if dt:
                date_str = dt.strftime("%Y%m%d")

        # If no date found, fallback to today
        if not date_str:
            date_str = datetime.today().strftime("%Y%m%d")

        print(f"📅 Using date: {date_str}")

        page_urls = set()

        while True:
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Extract page links
            for tag in soup.select('ul.epaper-pagination a.page-link'):
                if tag.text.strip().isdigit():
                    full_url = urljoin(base_url, tag['href'])
                    page_urls.add(full_url)

            # Try clicking the 'fa-forward' button (next page scroller)
            next_btn = await page.query_selector('ul.epaper-pagination a.page-link:has(i.fas.fa-forward)')
            if next_btn:
                try:
                    await next_btn.click()
                    await page.wait_for_timeout(1500)
                except Exception as e:
                    print("⚠️ Cannot click next anymore:", e)
                    break
            else:
                break

        sorted_links = sorted(page_urls, key=lambda x: int(x.rstrip('/').split('/')[-1]))

        for page_url in sorted_links:
            page_num = page_url.rstrip('/').split('/')[-1]
            print(f"\n📄 Processing Page {page_num}...")
            await page.goto(page_url)
            await page.wait_for_timeout(2000)

            page_html = await page.content()
            soup = BeautifulSoup(page_html, 'html.parser')
            article_links = []

            for tag in soup.find_all('a', class_='areamapper-maparea'):
                data_id = tag.get('data-id')
                if data_id:
                    article_links.append(f"https://www.mumbaichoufer.com/news/{data_id}/placeholder")

            if not article_links:
                print("⚠️ No articles found on this page.")
                continue

            # Set directory by publication_name and date
            page_dir = os.path.join(publication_name, date_str, f"page_{page_num}")
            os.makedirs(page_dir, exist_ok=True)

            for idx, article_url in enumerate(article_links, start=1):
                article_id = article_url.split('/')[-2]
                print(f"  📰 Processing article {article_id} (Article #{idx})...")
                images = download_article_images(
                    article_url,
                    page_dir,
                    publication_name,
                    date_str,
                    page_num,
                    idx
                )

                all_data[f"page_{page_num}"].append({
                    "article_id": article_id,
                    "article_url": article_url,
                    "images": images
                })

        await browser.close()
        return all_data

if __name__ == "__main__":
    final_data = asyncio.run(scrape())
    print("\n✅ Scraping Complete.\n")
    for page, articles in final_data.items():
        print(f"{page}: {len(articles)} articles")
        for article in articles:
            print(f"  - Article {article['article_id']}: {len(article['images'])} images")



