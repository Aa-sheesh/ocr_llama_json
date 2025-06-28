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

def setup_driver():
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in headless mode
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # Initialize the Chrome WebDriver
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def download_pdf(url, save_path):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f"PDF downloaded successfully to: {save_path}")
    except Exception as e:
        print(f"Error downloading PDF: {str(e)}")

def get_todays_edition_url():
    try:
        # Initialize the driver
        driver = setup_driver()
        
        # Navigate to the Mumbai edition page
        mumbai_url = 'https://epaper.bombaysamachar.com/category/14/%E0%AA%AE%E0%AB%81%E0%AA%82%E0%AA%AC%E0%AA%88'
        driver.get(mumbai_url)
        
        # Wait for the page to load
        time.sleep(2)
        
        # Get today's date in the format DD-MM-YYYY
        today = datetime.now().strftime('%d-%m-%Y')
        str_date = datetime.now().strftime('%Y-%m-%d')
        print(f"Looking for date: {today}")
        
        # Find the link with today's date in the edition-title div
        wait = WebDriverWait(driver, 10)
        today_link = wait.until(
            EC.presence_of_element_located((
                By.XPATH, 
                f"//div[contains(@class, 'edition-title')]//a[contains(@href, '/view/') and contains(@href, '{today}')]"
            ))
        )
        
        # Click on the link
        today_link.click()
        
        # Wait for the redirect
        time.sleep(2)
        
        # Get the redirected URL
        redirected_url = driver.current_url
        print(f"Redirected URL: {redirected_url}")
        
        # Find the PDF download link
        pdf_link = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "btn-pdfdownload"))
        )
        pdf_url = pdf_link.get_attribute('href')
        print(f"PDF URL: {pdf_url}")
        
        # Create directory structure
        base_dir = "bombay_samachar"
        edition = "mumbai"
        date_dir = os.path.join('downloads',base_dir, edition)
        os.makedirs(date_dir, exist_ok=True)
        
        # Download the PDF
        pdf_filename = f"bombaysamachar_{str_date}.pdf"
        pdf_path = os.path.join(date_dir, pdf_filename)
        download_pdf(pdf_url, pdf_path)
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    
    finally:
        # Close the browser
        driver.quit()

if __name__ == "__main__":
    get_todays_edition_url()
