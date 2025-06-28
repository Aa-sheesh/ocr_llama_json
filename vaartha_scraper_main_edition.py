import asyncio
import os
from datetime import datetime

import requests
from playwright.async_api import async_playwright


class NewspaperDownloader:
    def __init__(self):
        self.today_date = datetime.now().strftime("%Y-%m-%d")
        self.today = datetime.strptime(self.today_date, "%Y-%m-%d").strftime(
            "%Y_%m_%d")

        self.output_dir = os.path.join("downloads", "vaartha")
        self.successful_downloads = 0  # Initialize the counter for successful downloads

    async def get_edition_links(self, page):
        """Get all the links from the 'Main Editions' dropdown."""
        await page.click('a#navbarDropdown1')
        await page.wait_for_selector('ul[aria-labelledby="navbarDropdown1"]')

        edition_links = await page.query_selector_all(
            'ul[aria-labelledby="navbarDropdown1"] a')
        editions = []

        for link in edition_links:
            edition_url = await link.get_attribute('href')
            edition_name = await link.inner_text()

            # Prepend the base URL to the edition URL (to make it absolute)
            if not edition_url.startswith('http'):
                edition_url = "https://epaper.vaartha.com" + edition_url
            editions.append((edition_name, edition_url))

        total_editions = len(editions)  # Update the total editions count
        print(f"Total editions found in the dropdown: {total_editions}")
        return editions

    async def download_pdf(self, page, edition_name, download_link):
        """Download the PDF and save it locally."""

        # Use the edition name as part of the filename (replace spaces with underscores)
        edition_filename = edition_name.replace(" ", "_").lower()

        # Create a city-specific directory for the edition
        city_dir = os.path.join(self.output_dir, edition_filename)
        os.makedirs(city_dir, exist_ok=True)
        print(f"city_dir = {city_dir}")

        output_filename = os.path.join(city_dir, f"{edition_filename}_"
                                                 f"{self.today}.pdf")

        # Download the PDF
        response = requests.get(download_link)
        if response.status_code == 200:
            with open(output_filename, 'wb') as f:
                f.write(response.content)
            print(f"PDF saved as {output_filename}")
            self.successful_downloads += 1  # Increment successful downloads count
        else:
            print(
                f"Failed to download PDF for edition '{edition_name}', status code: {response.status_code}")

    async def process_edition(self, page, edition_name, edition_url):
        """Process a single edition page."""
        await page.goto(edition_url)
        await page.wait_for_load_state('domcontentloaded')

        # Get the title of the page to create a dynamic filename
        page_title = await page.title()
        print(f"Processing edition: {edition_name} - {page_title}")

        # Wait for the download button to appear
        await page.wait_for_selector('a.btn-pdfdownload')

        # Locate the download link
        download_link = await page.get_attribute('a.btn-pdfdownload', 'href')
        print(f"Found download link: {download_link}")

        # Download the PDF
        await self.download_pdf(page, edition_name, download_link)

    async def download_newspapers(self):
        """Main function to download all newspapers."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Open the e-paper website
            await page.goto("https://epaper.vaartha.com/")
            print("Main page opened.")

            # Get all edition links
            editions = await self.get_edition_links(page)

            # Iterate through each edition link
            for edition_name, edition_url in editions:

                print(f"Opening edition: {edition_name}")
                await self.process_edition(page, edition_name, edition_url)

            # Close the browser
            await browser.close()

            # Print the results
            print(f"Successfully downloaded: {self.successful_downloads}")


# Main Execution
if __name__ == "__main__":
    downloader = NewspaperDownloader()

    # Run the download process
    asyncio.run(downloader.download_newspapers())
