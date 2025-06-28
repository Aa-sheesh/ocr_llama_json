import os
import time
from datetime import datetime

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait


def create_directory(date_str):
    # Create base directory if it doesn't exist
    base_dir = "downloads/virat_vaibhav"
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    # Create edition directory (Delhi)
    edition_dir = os.path.join(base_dir, "delhi")
    if not os.path.exists(edition_dir):
        os.makedirs(edition_dir)

    return edition_dir


def download_image(url, save_path):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded: {save_path}")
        else:
            print(f"Failed to download: {url}")
    except Exception as e:
        print(f"Error downloading {url}: {str(e)}")


def main():
    # Set up Chrome options for headless mode
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    # Initialize Chrome driver with headless options
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 10)

    try:
        # Navigate to the website
        driver.get("https://epaper.viraatvaibhav.com/")

        # Wait for the date element to be present
        date_element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "topcol1")))
        date_text = date_element.text.strip()

        # Parse the date from the website
        website_date = datetime.strptime(date_text, "%A, %d %B, %Y")
        today = datetime.now()

        # Check if the date matches today
        if website_date.date() != today.date():
            print("Today's e-paper is not available yet.")
            return

        # Create directory for today's date
        date_str = today.strftime("%Y-%m-%d")
        save_dir = create_directory(date_str)

        # Process all 16 pages
        for page_num in range(1, 17):
            # Find the image element
            img_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "img.map.shadowimage.maphilighted")))
            img_src = img_element.get_attribute("src")

            # Construct full URL
            full_url = f"{img_src}"

            # Save the image
            save_path = os.path.join(save_dir, f"viratvaibhav{date_str}{page_num}.png")
            download_image(full_url, save_path)

            print(f"Processed page {page_num} of 16")

            # Click next button if not on the last page
            if page_num < 16:
                next_button = wait.until(EC.element_to_be_clickable((By.ID, "nexts")))
                next_button.click()
                time.sleep(2)  # Wait for page to load

    except Exception as e:
        print(f"An error occurred: {str(e)}")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
