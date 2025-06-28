import os
import time
from datetime import datetime

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


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
    global driver
    try:
        # Initialize the driver
        driver = setup_driver()

        # Navigate to the Haryana edition page
        base_url = 'https://jagatkranti.co.in/category/%e0%a4%b9%e0%a4%b0%e0%a4%bf%e0%a4%af%e0%a4%be%e0%a4%a3%e0%a4%be-%e0%a4%b8%e0%a4%82%e0%a4%b8%e0%a5%8d%e0%a4%95%e0%a4%b0%e0%a4%a3/'
        driver.get(base_url)

        # Wait for the page to load
        time.sleep(2)

        # Get today's date in the format DDMMYYYY
        today = datetime.now().strftime('%d%m%Y')
        print(f"Looking for date: {today}")

        # Find the link with today's date
        wait = WebDriverWait(driver, 10)
        today_link = wait.until(
            EC.presence_of_element_located((
                By.XPATH,
                f"//a[contains(@class, 'more-link') and contains(@href, '{today}')]"
            ))
        )

        # Click on the link
        today_link.click()

        # Wait for the redirect
        time.sleep(2)

        # Get the redirected URL
        redirected_url = driver.current_url
        print(f"Navigating to: {redirected_url}")

        # Scroll 25% of the page height
        page_height = driver.execute_script("return document.body.scrollHeight")
        scroll_position = int(page_height * 0.15)
        driver.execute_script(f"window.scrollTo(0, {scroll_position});")
        print("Scrolling to load PDF viewer...")
        time.sleep(3)  # Wait for content to load

        # Handle OneSignal notification dialog
        try:
            cancel_button = wait.until(
                EC.presence_of_element_located((
                    By.ID,
                    "onesignal-slidedown-cancel-button"
                ))
            )
            print("Dismissing notification popup...")
            cancel_button.click()
        except:
            pass  # No notification found, continue silently

        try:
            # First find and click the more button
            try:
                more_button = wait.until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR,
                        "div[class*='df-ui-more']"
                    ))
                )
            except:
                try:
                    more_button = wait.until(
                        EC.presence_of_element_located((
                            By.CSS_SELECTOR,
                            "div.df-ui-btn"
                        ))
                    )
                except:
                    print("Error: Could not find more button")
                    raise

            more_button.click()
            print("Opening download options...")

            # Wait for and find the more container
            more_container = wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "div.df-more-container"
                ))
            )

            # Find the download link within the more container
            pdf_link = wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "a.df-ui-btn.df-ui-download.df-icon-download"
                ))
            )
            pdf_url = pdf_link.get_attribute('href')
            print(f"Found PDF download link")

            # Create directory structure
            base_dir = "downloads/jagat_kranti/chandigarh"
            date_dir = os.path.join(base_dir)
            os.makedirs(date_dir, exist_ok=True)

            # Download the PDF
            pdf_filename = f"jagat_kranti_{datetime.now().strftime('%Y-%m-%d')}.pdf"
            pdf_path = os.path.join(date_dir, pdf_filename)
            print(f"Downloading PDF to: {pdf_path}")
            download_pdf(pdf_url, pdf_path)

        except Exception as e:
            print(f"Error: {str(e)}")

    except Exception as e:
        print(f"Error: {str(e)}")

    finally:
        print("Closing browser...")
        driver.quit()


if __name__ == "__main__":
    get_todays_edition_url()
