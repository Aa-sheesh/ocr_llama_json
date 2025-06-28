import asyncio
import os
import time
from datetime import datetime, timedelta

from playwright.async_api import async_playwright

# Set edition name (modify or extract from site if dynamic)
edition_name = "gangtok"  # Replace this if you want to extract it dynamically


async def download_hamro_praja_shakti():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        # Open the website
        await page.goto("https://www.hamroprajashakti.in/", timeout=60000)
        time.sleep(5)
        # Wait for the iframe to load and get its content
        iframe_element = await page.wait_for_selector('iframe.pdf-container',
                                                      timeout=60000)
        iframe = await iframe_element.content_frame()

        # Wait for the download button in the iframe
        await iframe.wait_for_selector('button#download', timeout=60000)

        # Trigger download and handle it at the page level
        async with page.expect_download() as download_info:
            await iframe.click('button#download')

        download = await download_info.value

        # Get yesterday's date
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_date_str = yesterday.strftime("%Y-%m-%d")
        yesterday_str = datetime.strptime(yesterday_date_str, "%Y-%m-%d").strftime("%Y_%m_%d")

        # Build directory path using yesterday's date
        base_dir = os.path.join("downloads","hamro_praja_shakti", edition_name)
        os.makedirs(base_dir, exist_ok=True)

        # Define file name and save path
        filename = f"{edition_name}_{yesterday_str}.pdf"
        save_path = os.path.join(base_dir, filename)

        # Save the file
        await download.save_as(save_path)
        print(f"✅ PDF saved at: {save_path}")

        await browser.close()


asyncio.run(download_hamro_praja_shakti())



# multiple editions required then below code use

"""

from playwright.sync_api import sync_playwright
import os
import time
from datetime import datetime, timedelta


def download_paper(url):
    with sync_playwright() as p:
        # Open browser and navigate to the page
        browser = p.chromium.launch(
            headless=True)  # Set headless=True for no browser window
        page = browser.new_page()
        page.goto(url)

        # Open the E-Paper dropdown
        page.click("li.nav-item.drop-link > a")

        # Wait for the dropdown to appear
        page.wait_for_selector("ul.dropdown > li > a")

        # Get all edition links from the dropdown
        editions = page.query_selector_all("ul.dropdown > li > a")
        edition_links = [edition.get_attribute('href') for edition in editions]

        # Filter editions and exclude special editions (assuming they have a specific class or title)
        # edition_links = [
        #     edition.get_attribute('href') for edition in editions
        #     if "special" not in edition.text_content().lower()
        #     # Skip editions that contain "special"
        # ]

        # if special edition required the line comment
        # Limit to only the first two editions
        edition_links = edition_links[:2]

        print(f"edition_links ={edition_links}")
        # Loop through each edition and click on it
        for edition in edition_links:
            print(f"Opening edition: {edition}")
            page.goto(f"https://www.hamroprajashakti.in/{edition}")

            # Wait for the news items to load (assuming the row class contains the articles)
            page.wait_for_selector(".row")

            # Click the first news post (article) to open the viewer
            first_news_post = page.query_selector(".col-sm-3 .post-image a")
            if first_news_post:
                news_link = first_news_post.get_attribute('href')
                print(f"Opening news post: {news_link}")

                # Prepend base URL to the relative link to make it absolute
                news_link = "https://www.hamroprajashakti.in/" + news_link

                # Open the news link in a new tab
                new_tab = browser.new_page()
                new_tab.goto(news_link)

                # Wait for the page with toolbar and buttons to load
                new_tab.wait_for_selector("#toolbarViewer")

                # Wait for the download button inside the toolbar
                new_tab.wait_for_selector("button#download")

                # Expect the download to be triggered when the download button is clicked
                with new_tab.expect_download() as download_info:
                    # Click the download button to start the download
                    new_tab.click("button#download")

                # Wait for the download to complete and get the download path
                download_path = download_info.value.path()

                # Get yesterday's date
                yesterday = datetime.now() - timedelta(days=1)
                yesterday_str = yesterday.strftime("%Y-%m-%d")

                # Build directory path using yesterday's date and edition name
                edition_name = edition.split("/")[-1]  # Extract edition
                # name from URL
                base_dir = os.path.join("downloads","hamro_praja_shakti_edition",
                    edition_name)
                os.makedirs(base_dir, exist_ok=True)

                # Define file name and save path
                filename = f"{edition_name}_hamro_praja_shakti_{yesterday_str}.pdf"
                save_path = os.path.join(base_dir, filename)

                # Move the downloaded file to the desired location
                os.rename(download_path, save_path)

                print(f"File saved as: {save_path}")

                # Close the current tab (news page)
                new_tab.close()

        browser.close()


if __name__ == "__main__":
    url = "https://www.hamroprajashakti.in/"
    download_paper(url)

"""