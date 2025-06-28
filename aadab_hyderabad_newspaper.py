import os
import time
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Base download folder
BASE_DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads/aadab_hyderabad")
os.makedirs(BASE_DOWNLOAD_DIR, exist_ok=True)

# Configure Chrome options
options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": BASE_DOWNLOAD_DIR,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "plugins.always_open_pdf_externally": True
}
options.add_experimental_option("prefs", prefs)
options.add_argument('--headless=new')  # support downloads in headless mode
options.add_argument('--disable-gpu')

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def get_navigation_items(driver):
    nav_items = driver.find_elements(By.CSS_SELECTOR, "#nav_drpdown .nav-item a.nav-link")
    items_data = []

    for item in nav_items:
        edid = item.get_attribute('edid')
        eddate = item.get_attribute('eddate')  # e.g., 22/05/2025
        default_view = item.get_attribute('default-view')
        item_id = item.get_attribute('id')

        if item_id == "a_Aadab Hyderabad Main":
            name = "AADAB_HYDERABAD_MAIN"
            base_url = f"https://epaper.aadabhyderabad.in/AadabHyderabadMain?eid={edid}&edate={eddate}&device=desktop&view={default_view}"
        elif item_id == "a_Aadab Hyderabad District":
            name = "AADAB_HYDERABAD_DISTRICT"
            base_url = f"https://epaper.aadabhyderabad.in/AadabHyderabadDistrict?eid={edid}&edate={eddate}&device=desktop&view={default_view}"
        else:
            continue

        formatted_date = eddate.replace("/", "-")
        items_data.append({
            'text': item.text.strip(),
            'base_url': base_url,
            'edid': edid,
            'eddate': eddate,
            'date_folder': formatted_date,
            'default_view': default_view,
            'folder': name
        })

    return items_data


def get_page_ids(driver, url):
    driver.get(url)
    try:
        dropdown = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "ddl_Pages"))
        )
        options = dropdown.find_elements(By.TAG_NAME, "option")
        return [option.get_attribute("value") for option in options if option.get_attribute("value")]
    except Exception as e:
        print(f"  → Error fetching pages: {e}")
        return []


def wait_for_new_download(before_files, timeout=15):
    """Wait for a new .pdf file to appear in the download folder"""
    for _ in range(timeout):
        after_files = set(os.listdir(BASE_DOWNLOAD_DIR))
        new_files = after_files - before_files
        pdfs = [f for f in new_files if f.endswith(".pdf")]
        if pdfs:
            return pdfs[0]
        time.sleep(1)
    return None


def download_pdf_for_page(driver, page_url, download_folder, page_number):
    try:
        driver.get(page_url)

        # Wait for download button to appear
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "downloadpagetoolbar"))
        )

        # Snapshot files before download
        before_files = set(os.listdir(BASE_DOWNLOAD_DIR))

        # Trigger download
        driver.find_element(By.ID, "downloadpagetoolbar").click()

        # Wait for new PDF file to appear
        new_pdf = wait_for_new_download(before_files)
        if not new_pdf:
            raise Exception("Download timed out or failed.")

        # Destination folder
        dest_folder = os.path.join(BASE_DOWNLOAD_DIR, download_folder)
        os.makedirs(dest_folder, exist_ok=True)
        dest_file = os.path.join(dest_folder, f"aadabhyderabad-page_{page_number}.pdf")

        # Move file
        shutil.move(os.path.join(BASE_DOWNLOAD_DIR, new_pdf), dest_file)
        print(f" Downloaded page {page_number} → {dest_file}")
    except Exception as e:
        print(f" Failed to download page {page_number}: {e}")


try:
    print("\nLaunching browser and opening site...")
    driver.get("https://epaper.aadabhyderabad.in/")
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#nav_drpdown"))
    )

    nav_items = get_navigation_items(driver)
    print(f"\nFound {len(nav_items)} editions\n")

    for item in nav_items:
        print(f"\n→ Processing: {item['text']} ({item['date_folder']})")
        page_ids = get_page_ids(driver, item['base_url'])

        for pg_num, pid in enumerate(page_ids, start=1):
            page_url = f"{item['base_url']}&pgid={pid}"
            subfolder_path = os.path.join(item['folder'])
            download_pdf_for_page(driver, page_url, subfolder_path.lower(), pg_num)

except Exception as e:
    print(f"\n General Error: {e}")
finally:
    driver.quit()
    print("\n Done. Browser closed.\n")