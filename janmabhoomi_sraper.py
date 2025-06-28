import os
import tempfile
import time
from datetime import datetime
from io import BytesIO

import img2pdf
import requests
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def setup_driver():
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')  # Set window size
    chrome_options.add_argument('--start-maximized')  # Start maximized
    chrome_options.add_argument('--disable-gpu')  # Disable GPU hardware acceleration
    chrome_options.add_argument('--disable-extensions')  # Disable extensions
    chrome_options.add_argument('--disable-infobars')  # Disable infobars
    chrome_options.add_argument('--disable-notifications')  # Disable notifications
    chrome_options.add_argument('--disable-popup-blocking')  # Disable popup blocking

    # Initialize the Chrome driver
    driver = webdriver.Chrome(options=chrome_options)

    # Set window size explicitly
    driver.set_window_size(1920, 1080)

    return driver


def download_image(url):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    except Exception as e:
        print(f"Error downloading image {url}: {str(e)}")
        return None


def create_pdf(images, output_path):
    try:
        # Create a temporary directory to store images
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save images to temporary files
            image_paths = []
            for idx, img in enumerate(images):
                if img is not None:
                    temp_path = os.path.join(temp_dir, f'page_{idx}.jpg')
                    img.save(temp_path, 'JPEG')
                    image_paths.append(temp_path)

            # Convert images to PDF
            pdf_bytes = img2pdf.convert(image_paths)

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Save PDF
            with open(output_path, "wb") as f:
                f.write(pdf_bytes)
            print(f"Created PDF: {output_path}")
            return True
    except Exception as e:
        print(f"Error creating PDF: {str(e)}")
        return False


def get_page_image(driver, page_num):
    try:
        # Wait for the epaper image to be present
        epaper_image = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "epaper_image"))
        )

        # Get the image URL
        img_url = epaper_image.get_attribute('src')
        if not img_url:
            print(f"No image URL found for page {page_num}")
            return None

        return download_image(img_url)

    except Exception as e:
        print(f"Error getting image for page {page_num}: {str(e)}")
        return None


def login_to_epaper():
    # URL of the login page
    login_url = "https://epaper.janmabhoominewspapers.com/login"

    # Initialize the driver
    driver = setup_driver()

    try:
        # Navigate to the login page
        driver.get(login_url)

        # Wait for the email input field to be present
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "email"))
        )

        # Wait for the password input field to be present
        password_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "password"))
        )

        # Enter credentials
        email_input.send_keys("Subscriptions@AAIZELTECH.com")
        password_input.send_keys("A@izel@123")

        # Find and click the login button
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "r1"))
        )

        # Scroll to the button and click using JavaScript
        driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
        time.sleep(1)  # Wait for scroll to complete
        driver.execute_script("arguments[0].click();", login_button)

        # Wait for navigation to complete
        time.sleep(3)

        # Wait for 6 more seconds after redirecting to the main page - let the modal close automatically
        time.sleep(6)

        # Get today's date in the required format (DD-MM-YYYY)
        today_date = datetime.now().strftime("%d-%m-%Y")

        # Wait for the epaper container to be present
        container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "epaper_img_container"))
        )

        # Find all links with class 'bec_link'
        links = container.find_elements(By.CLASS_NAME, "bec_link")

        # Find the link with today's date
        target_link = None
        for link in links:
            try:
                date_element = link.find_element(By.CLASS_NAME, "edate")
                if date_element.text == today_date:
                    target_link = link
                    break
            except:
                continue

        if target_link:
            # Store the current window handle
            main_window = driver.current_window_handle

            # Click the link using JavaScript
            driver.execute_script("arguments[0].scrollIntoView(true);", target_link)
            time.sleep(1)  # Wait for scroll to complete
            driver.execute_script("arguments[0].click();", target_link)

            # Wait for the new tab to open
            time.sleep(7)

            # Get all window handles
            all_handles = driver.window_handles

            # Switch to the new tab
            for handle in all_handles:
                if handle != main_window:
                    driver.switch_to.window(handle)
                    break

            # Get the current URL in the new tab
            current_url = driver.current_url

            # Verify if the URL matches the expected format
            expected_url_format = f"https://epaper.janmabhoominewspapers.com/view/epaper/{today_date}/1"
            if current_url == expected_url_format:
                # Format date for folder structure (YYYY-MM-DD)
                folder_date = datetime.strptime(today_date, "%d-%m-%Y").strftime("%Y-%m-%d")

                # List to store all page images
                page_images = []

                # Get total number of pages
                page_numbers = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "ep_page_numbers"))
                )
                page_links = page_numbers.find_elements(By.TAG_NAME, "a")
                total_pages = len(page_links)
                print(f"Found {total_pages} page links")

                # Process each page
                for page_num in range(1, total_pages + 1):
                    try:
                        print(f"Processing page {page_num}")

                        # Navigate to the page
                        page_url = f"https://epaper.janmabhoominewspapers.com/view/epaper/{today_date}/{page_num}"
                        driver.get(page_url)

                        # Wait for page to load
                        time.sleep(3)

                        # Get the page image
                        page_image = get_page_image(driver, page_num)
                        if page_image:
                            page_images.append(page_image)

                    except Exception as e:
                        print(f"Error processing page {page_num}: {str(e)}")
                        continue

                # Create PDF from all collected images
                if page_images:
                    pdf_path = f"downloads/janmbhoomi/mumbai/janmbhoomi_{folder_date}.pdf"
                    create_pdf(page_images, pdf_path)

            else:
                print(f"URL does not match expected format. Expected: {expected_url_format}")

            # Switch back to the main window
            driver.switch_to.window(main_window)

        else:
            print(f"No link found for date: {today_date}")

        return driver

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        driver.quit()
        return None


def main():
    # Attempt to login
    driver = login_to_epaper()

    if driver:
        try:
            # Add a small delay to avoid overwhelming the server
            time.sleep(2)

        finally:
            # Close the browser when done
            driver.quit()


if __name__ == "__main__":
    main()
