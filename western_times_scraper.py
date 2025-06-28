import asyncio
import os
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright


def generate_pdf_url(date: datetime, lang: str) -> str:
    """Generate the correct PDF URL based on language and date."""
    year = date.year
    month = f"{date.month:02d}"
    day = f"{date.day:02d}"
    suffix = 'en' if lang == 'english' else 'ah'
    filename = f"{day}{month}{year}{suffix}.pdf"
    return f"https://westerntimesnews.in/wp-content/uploads/{year}/{month}/{filename}"


async def download_pdf(playwright, url: str, save_path: Path):
    """Download a PDF using Playwright's request context."""
    request_context = await playwright.request.new_context()

    print(f"Trying to download: {url}")
    response = await request_context.get(url)

    if response.ok and "application/pdf" in response.headers.get("content-type", ""):
        content = await response.body()
        save_path.write_bytes(content)
        print(f"✅ PDF saved at: {save_path}")
    else:
        print(f"❌ Failed or not a valid PDF: {url} (Status: {response.status})")

    await request_context.dispose()


async def main():
    today_date = datetime.now()
    today_str = today_date.strftime("%Y-%m-%d")
    formatted_date = datetime.strptime(today_str, "%Y-%m-%d").strftime("%Y_%m_%d")

    base_dir = Path(os.path.join("downloads", "western_times"))

    # Define editions and filename templates
    editions = {
        "english": f"western_news_paper_english_{formatted_date}.pdf",
        "gujarati": f"western_news_paper_gujarati_{formatted_date}.pdf"
    }

    async with async_playwright() as playwright:
        for lang, filename in editions.items():
            edition_folder = base_dir / "ahmedabad"
            edition_folder.mkdir(parents=True, exist_ok=True)
            save_path = edition_folder / filename
            pdf_url = generate_pdf_url(today_date, lang)
            await download_pdf(playwright, pdf_url, save_path)


if __name__ == "__main__":
    asyncio.run(main())
