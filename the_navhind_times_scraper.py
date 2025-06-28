import os
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import requests
from datetime import datetime
from PIL import Image
import io

today = datetime.today()
formatted_date = today.strftime("%Y-%m-%d")
base_url = f"https://epaper.navhindtimes.in/mainpage.aspx?pdate={formatted_date}"


def setup_driver():
    """Setup and return a configured Chrome WebDriver"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(options=chrome_options)


def extract_page_info(element):
    """Extract date and page number from onclick attribute"""
    try:
        onclick_attr = element.get_attribute('onclick')
        if onclick_attr:
            match = re.search(r"OpenHeadingWindow\('([^']+)','(\d+)'\)", onclick_attr)
            if match:
                date = match.group(1)
                page_num = match.group(2)
                return date, page_num
    except Exception as e:
        print(f"Error extracting page info: {e}")
    return None, None


def download_article_images(driver, story_id, date, page_num):
    """Download images from a specific article page"""
    try:
        print(f"\nProcessing article {story_id} for page {page_num}")

        # Create directory structure
        root_dir = "downloads/the_navhind_times"
        edition_dir = os.path.join(root_dir, "goa")
        if not os.path.exists(edition_dir):
            os.makedirs(edition_dir)

        # Navigate to article page
        article_url = f"https://epaper.navhindtimes.in/NewsDetail.aspx?storyid={story_id}&date={date}"
        print(f"Navigating to: {article_url}")

        # Open in new tab
        driver.execute_script(f"window.open('{article_url}', '_blank');")
        time.sleep(2)

        # Switch to new tab
        driver.switch_to.window(driver.window_handles[-1])

        # Find and download images
        images = driver.find_elements(By.TAG_NAME, "img")
        image_count = 0

        for img in images:
            img_url = img.get_attribute('src')
            if img_url and ('storyImages' in img_url or 'PageImages' in img_url):
                print(f"Found image: {img_url}")
                try:
                    # Download image
                    response = requests.get(img_url)
                    if response.status_code == 200:
                        # Create filename with new format
                        filename = f"the_navhind_times{formatted_date}{page_num}.png"
                        filepath = os.path.join(edition_dir, filename)

                        # Save image directly as PNG
                        with open(filepath, 'wb') as f:
                            f.write(response.content)
                        print(f"Saved image to {filepath}")
                        image_count += 1
                except Exception as e:
                    print(f"Error downloading image: {e}")

        # Close tab and switch back
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        time.sleep(1)

        print(f"Downloaded {image_count} images for article {story_id}")
        return image_count

    except Exception as e:
        print(f"Error processing article images: {e}")
        # Try to close tab and switch back in case of error
        try:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        except:
            pass
        return 0


def process_modal_links(driver, modal_html, page_num, date):
    """Process all GetClickData links in the modal"""
    try:
        soup = BeautifulSoup(modal_html, 'html.parser')
        # Find all elements with onclick containing GetClickData
        click_links = soup.find_all(lambda tag: tag.has_attr('onclick') and 'GetClickData' in tag['onclick'])

        print(f"\nFound {len(click_links)} GetClickData links in page {page_num}")

        total_images = 0
        for link in click_links:
            onclick = link['onclick']
            match = re.search(r"GetClickData\('(\d+)','([^']+)'\)", onclick)
            if match:
                story_id = match.group(1)
                date = match.group(2)
                print(f"\nProcessing link: {link.text.strip()}")
                print(f"Story ID: {story_id}, Date: {date}")

                # Download images from article
                image_count = download_article_images(driver, story_id, date, page_num)
                total_images += image_count

        print(f"\nTotal images downloaded for page {page_num}: {total_images}")
        return total_images

    except Exception as e:
        print(f"Error processing modal links: {e}")
        return 0


def get_modal_content(driver, max_retries=3):
    """Get modal content using JavaScript with retry mechanism"""
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1} to get modal content")

            # Wait for modal to be visible with increased timeout
            wait = WebDriverWait(driver, 20)

            # Try to find modal using different selectors
            modal = None
            selectors = [
                (By.ID, "DV_NewsHeading"),
                (By.CLASS_NAME, "modal-dialog"),
                (By.CLASS_NAME, "modal")
            ]

            for selector in selectors:
                try:
                    modal = wait.until(EC.presence_of_element_located(selector))
                    if modal:
                        print(f"Found modal using selector: {selector}")
                        break
                except:
                    continue

            if not modal:
                print("Modal not found with any selector")
                time.sleep(5)  # Wait before retry
                continue

            # Wait for modal to be visible
            wait.until(EC.visibility_of(modal))
            time.sleep(3)  # Additional wait

            # Try to get modal HTML
            modal_html = modal.get_attribute('outerHTML')
            if not modal_html:
                print("Could not get modal HTML")
                continue

            return None, modal_html

        except Exception as e:
            print(f"Error in attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print("Retrying...")
                time.sleep(5)  # Wait before retry
                return None
            else:
                print("All retry attempts failed")
                return None, None
    return None


def get_page_content(driver, page_element, max_retries=3):
    """Get the content of a specific page with retry mechanism"""
    for attempt in range(max_retries):
        try:
            print(f"\nAttempt {attempt + 1} to process page")

            # Get page info before clicking
            date, page_num = extract_page_info(page_element)
            if not date or not page_num:
                print("Could not extract page information")
                return None, None, None

            print(f"Processing page {page_num} for date {date}")

            # Scroll element into view and click
            driver.execute_script("arguments[0].scrollIntoView(true);", page_element)
            time.sleep(2)

            # Try different click methods
            click_methods = [
                lambda: driver.execute_script("arguments[0].click();", page_element),
                lambda: page_element.click(),
                lambda: driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', {'bubbles': true}));",
                                              page_element)
            ]

            clicked = False
            for click_method in click_methods:
                try:
                    click_method()
                    clicked = True
                    break
                except:
                    continue

            if not clicked:
                print("Failed to click page element")
                continue

            time.sleep(3)

            # Get modal content
            content, modal_html = get_modal_content(driver)

            if modal_html:
                total_images = process_modal_links(driver, modal_html, page_num, date)
                print(f"Completed page {page_num} with {total_images} total images")
            else:
                print(f"No modal content found for page {page_num}")
                continue

            # Try to close modal
            close_methods = [
                lambda: driver.find_element(By.CSS_SELECTOR, "div.close_news").click(),
                lambda: driver.execute_script("document.querySelector('div.close_news').click();"),
                lambda: driver.execute_script("""
                    var closeDiv = document.querySelector('div.close_news');
                    if (closeDiv) {
                        closeDiv.click();
                    }
                """)
            ]

            closed = False
            for close_method in close_methods:
                try:
                    close_method()
                    closed = True
                    time.sleep(2)
                    break
                except:
                    continue

            if not closed:
                print("Failed to close modal")
                continue

            return content, date, page_num

        except Exception as e:
            print(f"Error in attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print("Retrying...")
                time.sleep(5)
            else:
                print("All retry attempts failed")
                return None, None, None

    return None, None, None


def download_navhind_times():
    """Main function to download Navhind Times e-paper content"""
    driver = setup_driver()

    try:
        # Navigate to the base URL
        driver.get(base_url)
        time.sleep(5)  # Increased initial wait time

        # Get all page links with specific onclick attribute
        page_links = driver.find_elements(By.CSS_SELECTOR, "a[id^='Repeater_pageNo_A_pageNo_']")

        if not page_links:
            print("No page links found!")
            return

        total_pages = len(page_links)
        print(f"\nProcessing all {total_pages} pages")

        # Process each page
        for i, page_link in enumerate(page_links, 1):
            print(f"\n{'=' * 50}")
            print(f"Processing page {i} of {total_pages}")
            print(f"{'=' * 50}")

            # Try to process page with retries
            content, date, page_num = get_page_content(driver, page_link)

            if not content and not date and not page_num:
                print(f"Failed to process page {i} after all retries")
                continue

            time.sleep(3)  # Increased delay between pages

        print("\nDownload completed successfully!")

    except Exception as e:
        print(f"Error during download: {e}")

    finally:
        driver.quit()


if __name__ == "__main__":
    download_navhind_times()