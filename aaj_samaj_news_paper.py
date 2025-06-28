import os
import time
import requests
from datetime import date
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

def wait_for_url_change(driver, old_url, timeout=15):
    wait = WebDriverWait(driver, timeout)
    try:
        wait.until(lambda d: d.current_url != old_url and d.current_url != "about:blank")
        return driver.current_url
    except:
        return driver.current_url

# Setup Chrome options in headless mode
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

# Setup Chrome driver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

# Create dated download directory: download/YYYY-MM-DD/
script_dir = os.path.dirname(os.path.abspath(__file__))
today_str = date.today().isoformat()  # Format: 'YYYY-MM-DD'
download_dir = os.path.join(script_dir, 'downloads',"aaj_samaj")
os.makedirs(download_dir, exist_ok=True)
print(f"Created download directory at: {download_dir}")

try:
    print("Opening initial page (headless)...")
    driver.get("https://www.magzter.com/IN/ITV-Network/Aaj-Samaaj/Newspaper/")

    wait = WebDriverWait(driver, 20)
    section = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "section.jsx-1071302039.issuesplaceholder")))
    main_window = driver.current_window_handle
    section.click()

    wait.until(EC.number_of_windows_to_be(2))
    new_window = [window for window in driver.window_handles if window != main_window][0]
    driver.switch_to.window(new_window)

    new_url = wait_for_url_change(driver, old_url="about:blank", timeout=20)
    print(f"New tab URL after wait: {new_url}")

    scroll_view = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//img[@title='Scroll View' and contains(@class,'icon')]")))
    scroll_view.click()

    image_div = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.jsx-3960180591.cn__list")))
    image_boxes = image_div.find_elements(By.CSS_SELECTOR, "div[id^='scrollimagebox-']")
    print(f"Found {len(image_boxes)} image boxes")

    for idx, box in enumerate(image_boxes, 1):
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", box)
        time.sleep(1.5)

        try:
            main_img = box.find_element(By.CSS_SELECTOR, "img.cn__main")
            main_src = main_img.get_attribute("src")

            if main_src and "jpg" in main_src:
                filename = os.path.join(download_dir, f"aaj-samaj-age_{idx}.jpg")
                response = requests.get(main_src, stream=True)
                with open(filename, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                print(f"Downloaded: {filename}")
            else:
                print(f"Image not found for box {idx}")

        except NoSuchElementException:
            print(f"Main image not found for box {idx}")

except Exception as e:
    print(f"Error occurred: {str(e)}")
    driver.save_screenshot(os.path.join(download_dir, "error_screenshot.png"))

finally:
    driver.quit()