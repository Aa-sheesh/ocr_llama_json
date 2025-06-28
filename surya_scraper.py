from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from datetime import datetime
import time
import os
import requests
from urllib.parse import urlparse

def setup_driver():
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in headless mode
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    # Set download preferences
    prefs = {
        "download.default_directory": os.getcwd(),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # Initialize the Chrome WebDriver
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def get_current_date():
    # Get current date in the format "YYYY-MM-DD"
    return datetime.now().strftime("%Y-%m-%d")

def get_formatted_date():
    # Get current date in the format "DD MMM YYYY" (e.g., "04 Jun 2025")
    return datetime.now().strftime("%d %b %Y")

def create_directory(state_name, city_name, date):
    # Create directory structure: Surya/[State]/[City]/[Publication Name]_[Date].pdf
    base_dir = "downloads/surya"
    state_dir = os.path.join(base_dir, state_name.lower().replace(" ", "_"))
    city_dir = os.path.join(state_dir, city_name.lower())
    
    # Create directories if they don't exist
    os.makedirs(city_dir, exist_ok=True)
    return city_dir

def download_pdf(url, save_path):
    try:
        print(f"Starting download from: {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()

        print(f"Creating file at: {save_path}")
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print("Download completed successfully")
        return True
    except Exception as e:
        print(f"Error downloading PDF: {str(e)}")
        return False

def process_state_dropdown(driver, dropdown_id, state_name, current_date):
    # Dictionary to store PDF URLs for each city
    city_pdf_urls = {}
    processed_cities = 0
    successful_downloads = 0
    
    try:
        print(f"\nStarting to process {state_name}...")
        # Find and click dropdown
        dropdown = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, dropdown_id))
        )
        driver.execute_script("arguments[0].click();", dropdown)
        time.sleep(2)
        
        # Get all list items text first
        list_items = driver.find_elements(By.CSS_SELECTOR, f"#{dropdown_id} + .dropdown-menu li")
        city_names = [item.text.strip() for item in list_items]
        print(f"Found {len(city_names)} cities in {state_name}")
        
        # First pass: Collect all PDF URLs
        for city_name in city_names:
            try:
                processed_cities += 1
                print(f"\nProcessing city {processed_cities}/{len(city_names)}: {city_name}")
                
                # Navigate to main page
                driver.get('https://www.suryaepaper.com/')
                time.sleep(3)
                
                # Handle OneSignal modal if it appears
                try:
                    modal = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.ID, "onesignal-slidedown-dialog"))
                    )
                    cancel_button = driver.find_element(By.ID, "onesignal-slidedown-cancel-button")
                    cancel_button.click()
                    print("Closed OneSignal modal")
                    time.sleep(1)
                except:
                    print("No OneSignal modal found or already closed")
                
                # Find and click dropdown
                dropdown = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, dropdown_id))
                )
                driver.execute_script("arguments[0].click();", dropdown)
                time.sleep(2)
                
                # Find and click the specific city
                list_items = driver.find_elements(By.CSS_SELECTOR, f"#{dropdown_id} + .dropdown-menu li")
                city_found = False
                
                for item in list_items:
                    if item.text.strip() == city_name:
                        city_found = True
                        # Get the href attribute before clicking
                        city_url = item.find_element(By.TAG_NAME, "a").get_attribute('href')
                        print(f"Found city URL: {city_url}")
                        
                        # Navigate directly to the city's page
                        driver.get(city_url)
                        time.sleep(3)
                        
                        # Handle OneSignal modal if it appears
                        try:
                            modal = WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located((By.ID, "onesignal-slidedown-dialog"))
                            )
                            cancel_button = driver.find_element(By.ID, "onesignal-slidedown-cancel-button")
                            cancel_button.click()
                            print("Closed OneSignal modal")
                            time.sleep(1)
                        except:
                            print("No OneSignal modal found or already closed")
                        
                        try:
                            # Find all edition-thumb-box divs
                            edition_boxes = driver.find_elements(By.CLASS_NAME, "edition-thumb-box")
                            print(f"Found {len(edition_boxes)} edition boxes")
                            
                            if len(edition_boxes) == 0:
                                print(f"No edition boxes found for {city_name}")
                                continue
                            
                            # Look for today's newspaper
                            today_date = get_formatted_date()
                            print(f"Looking for today's date: {today_date}")
                            
                            found_today_edition = False
                            for box in edition_boxes:
                                try:
                                    date_element = box.find_element(By.CLASS_NAME, "edition-date")
                                    date_text = date_element.text.strip()
                                    print(f"Checking edition date: {date_text}")
                                    
                                    if date_text == today_date:
                                        found_today_edition = True
                                        # Find and click the link
                                        link = box.find_element(By.TAG_NAME, "a")
                                        newspaper_url = link.get_attribute('href')
                                        print(f"Found newspaper URL: {newspaper_url}")
                                        
                                        # Navigate to the newspaper page
                                        driver.get(newspaper_url)
                                        time.sleep(3)
                                        
                                        # Handle OneSignal modal if it appears
                                        try:
                                            modal = WebDriverWait(driver, 5).until(
                                                EC.presence_of_element_located((By.ID, "onesignal-slidedown-dialog"))
                                            )
                                            cancel_button = driver.find_element(By.ID, "onesignal-slidedown-cancel-button")
                                            cancel_button.click()
                                            print("Closed OneSignal modal")
                                            time.sleep(1)
                                        except:
                                            print("No OneSignal modal found or already closed")
                                        
                                        # Find and get the PDF URL
                                        try:
                                            pdf_button = WebDriverWait(driver, 10).until(
                                                EC.element_to_be_clickable((By.CLASS_NAME, "btn-pdfdownload"))
                                            )
                                            
                                            # Get the PDF URL
                                            pdf_url = pdf_button.get_attribute('href')
                                            if pdf_url:
                                                city_pdf_urls[city_name] = pdf_url
                                                print(f"Successfully found PDF URL for {city_name}: {pdf_url}")
                                            else:
                                                print(f"No PDF URL found for {city_name}")
                                        except Exception as e:
                                            print(f"Error finding PDF button for {city_name}: {str(e)}")
                                        break
                                except Exception as e:
                                    print(f"Error processing edition box: {str(e)}")
                                    continue
                            
                            if not found_today_edition:
                                print(f"No today's edition found for {city_name}")
                                
                        except Exception as e:
                            print(f"Error finding edition boxes: {str(e)}")
                        break
                
                if not city_found:
                    print(f"City {city_name} not found in dropdown")
                
            except Exception as e:
                print(f"Error processing {city_name}: {str(e)}")
                continue
        
        # Second pass: Download all PDFs
        print(f"\nStarting PDF downloads for {state_name}...")
        print(f"Found {len(city_pdf_urls)} PDF URLs to download")
        
        if not city_pdf_urls:
            print(f"No PDF URLs found for {state_name}")
            return
            
        for city_name, pdf_url in city_pdf_urls.items():
            try:
                print(f"\nDownloading PDF for {city_name}...")
                save_dir = create_directory(state_name, city_name, current_date)
                pdf_filename = f"surya_{current_date}.pdf"
                save_path = os.path.join(save_dir, pdf_filename)
                
                print(f"Attempting to download from URL: {pdf_url}")
                print(f"Saving to path: {save_path}")
                
                if download_pdf(pdf_url, save_path):
                    print(f"Successfully downloaded PDF to: {save_path}")
                    successful_downloads += 1
                else:
                    print(f"Failed to download PDF for {city_name}")
                
            except Exception as e:
                print(f"Error downloading PDF for {city_name}: {str(e)}")
                continue
        
        print(f"\nSummary for {state_name}:")
        print(f"Total cities processed: {processed_cities}")
        print(f"Total PDFs found: {len(city_pdf_urls)}")
        print(f"Total successful downloads: {successful_downloads}")
                
    except Exception as e:
        print(f"An error occurred while processing {state_name}: {str(e)}")

def get_dropdown_items():
    driver = setup_driver()
    try:
        # Navigate to the website
        driver.get('https://www.suryaepaper.com/')
        current_date = get_current_date()

        # Wait for the page to load completely
        time.sleep(5)

        # Process Andhra Pradesh dropdown
        print("\nProcessing Andhra Pradesh editions...")
        process_state_dropdown(driver, "navbarDropdown1", "Andhra Pradesh", current_date)

        # Process Telangana dropdown
        print("\nProcessing Telangana editions...")
        process_state_dropdown(driver, "navbarDropdown2", "Telangana", current_date)

    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    get_dropdown_items()

