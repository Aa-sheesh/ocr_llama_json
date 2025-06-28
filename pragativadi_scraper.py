import time
from datetime import datetime
import os
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException


def setup_driver():
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')  # Use new headless mode
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--disable-popup-blocking')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # Set download preferences
    download_dir = os.path.abspath("Pragativadi")
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "plugins.always_open_pdf_externally": True,  # Don't open PDFs in Chrome
        "download.open_pdf_in_system_reader": False,  # Don't open PDFs in system reader
        "profile.default_content_settings.popups": 0,  # Disable popups
        "profile.content_settings.exceptions.automatic_downloads.*.setting": 1  # Allow automatic downloads
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Initialize the Chrome driver
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def create_download_directory(publication_name, edition_name):
    # Create base directory if it doesn't exist
    base_dir = "downloads/"+publication_name
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    
    # Create edition-specific directory
    edition_dir = os.path.join(base_dir, edition_name)
    if not os.path.exists(edition_dir):
        os.makedirs(edition_dir)
    
    return edition_dir


def download_image(driver, page_num, download_dir, publication_name, edition_name):
    try:
        # Get the base64 image URL from the page
        image_url = driver.execute_script("return pageImgUrlBase64;")
        if not image_url:
            print(f"Could not find image URL for page {page_num + 1}")
            return False

        # Construct the full download URL
        download_url = f"https://epaper.pragativadi.com/imagedownload.php?image={image_url}"
        
        # Download the image using requests
        response = requests.get(download_url)
        if response.status_code == 200:
            # Create filename with the new format
            today = datetime.now().strftime("%Y-%m-%d")
            filename = f"{publication_name.lower()}{today}{page_num + 1}.png"
            filepath = os.path.join(download_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            print(f"Successfully downloaded page {page_num + 1} as {filename}")
            return True
        else:
            print(f"Failed to download page {page_num + 1}. Status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Error downloading page {page_num + 1}: {str(e)}")
        return False


def download_page(driver, page_num, total_pages, download_dir, publication_name, edition_name):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Wait for the page selector to be present and get a fresh reference
            page_selector = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "ddlistPage"))
            )
            select = Select(page_selector)
            
            # Select the page
            select.select_by_index(page_num)
            print(f"Processing page {page_num + 1} of {total_pages}")
            
            # Wait for the page to load
            time.sleep(3)
            
            # Wait for the download button to be clickable
            download_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "shareit.download"))
            )
            
            # Check if download button is present
            print("Download button found, proceeding to download.")
            
            # Download the image
            if download_image(driver, page_num, download_dir, publication_name, edition_name):
                return True
            else:
                print(f"Download failed for page {page_num + 1}, attempt {attempt + 1}")
                
        except (StaleElementReferenceException, TimeoutException) as e:
            print(f"Error on page {page_num + 1}, attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                print("Retrying...")
                time.sleep(3)
            else:
                print(f"Failed to download page {page_num + 1} after {max_retries} attempts")
                return False
    
    return False


def main():
    # Initialize the driver
    driver = setup_driver()
    
    try:
        # Define publication and edition names
        publication_name = "Pragativadi"
        edition_name = "Bhubaneswar"
        
        # Visit the website
        driver.get("https://epaper.pragativadi.com/")
        print("Current URL:", driver.current_url)
        
        # Wait for the dropdown to be clickable and click it
        dropdown = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "li.dropdown"))
        )
        dropdown.click()
        
        # Wait for the dropdown menu to be visible
        dropdown_menu = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "dropdown-menu"))
        )
        
        # Find and click on Bhubaneswar link
        bhubaneswar_link = dropdown_menu.find_element(By.XPATH, ".//a[contains(text(), 'Bhubaneswar')]")
        bhubaneswar_link.click()
        
        # Print the URL after clicking Bhubaneswar
        print("URL after clicking Bhubaneswar:", driver.current_url)
        
        # Get today's date in the required format
        today_date = datetime.now().strftime("%d-%m-%Y")
        target_text = f"Bhubaneswar-{today_date}"
        
        # Wait for and find the link with today's date
        today_edition = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f"//a[contains(text(), '{target_text}')]"))
        )
        today_edition.click()
        
        # Print the final URL
        print("Final URL:", driver.current_url)
        
        # Create download directory with new structure
        download_dir = create_download_directory(publication_name.lower(), edition_name.lower())
        print(f"Downloading images to: {download_dir}")
        
        # Wait for the page selector to be present
        page_selector = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "ddlistPage"))
        )
        
        # Get all page options
        select = Select(page_selector)
        total_pages = len(select.options)
        print(f"Total pages found: {total_pages}")
        
        # Loop through each page
        for page_num in range(total_pages):
            if not download_page(driver, page_num, total_pages, download_dir, publication_name, edition_name):
                print(f"Skipping to next page after failed download of page {page_num + 1}")
                continue
            
            # Add a small delay between pages
            time.sleep(3)
        
        print("Download process completed!")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    
    finally:
        # Close the browser
        driver.quit()


if __name__ == "__main__":
    main()
