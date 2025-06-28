import os
from datetime import datetime

from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

main_url = "https://sambadepaper.com/"
save_dir = "downloads/sambad"
paper_name = "sambad"
str_date = datetime.now().strftime("%Y-%m-%d")


# def create_pdf_from_images(image_paths, output_pdf_path):
#     """Create a PDF from a list of image paths"""
#     try:
#         # Create a new PDF with ReportLab
#         c = canvas.Canvas(output_pdf_path, pagesize=A4)
#
#         for img_path in image_paths:
#             if os.path.exists(img_path):
#                 # Open the image
#                 img = Image.open(img_path)
#
#                 # Convert to RGB if necessary
#                 if img.mode != "RGB":
#                     img = img.convert("RGB")
#
#                 # Calculate dimensions to fit on A4
#                 img_width, img_height = img.size
#                 aspect = img_height / float(img_width)
#
#                 # A4 dimensions in points (1 point = 1/72 inch)
#                 a4_width, a4_height = A4
#
#                 # Calculate dimensions to fit on A4 while maintaining aspect ratio
#                 # Use 90% of page width/height to ensure margins
#                 if aspect > 1:
#                     # Portrait
#                     width = a4_width * 0.9
#                     height = width * aspect
#                     if height > a4_height * 0.9:
#                         height = a4_height * 0.9
#                         width = height / aspect
#                 else:
#                     # Landscape
#                     height = a4_height * 0.9
#                     width = height / aspect
#                     if width > a4_width * 0.9:
#                         width = a4_width * 0.9
#                         height = width * aspect
#
#                 # Center the image on the page
#                 x = (a4_width - width) / 2
#                 y = (a4_height - height) / 2
#
#                 # Draw the image
#                 c.drawImage(
#                     img_path, x, y, width=width, height=height, preserveAspectRatio=True
#                 )
#                 c.showPage()
#
#         c.save()
#         print(f"PDF created successfully: {output_pdf_path}")
#         return True
#     except Exception as e:
#         print(f"Error creating PDF: {e}")
#         return False


def download_epaper_images(base_url, edition_name):
    # Create base directory if it doesn't exist
    if not os.path.exists(save_dir):
        try:
            os.makedirs(save_dir)
            print(f"Created directory: {save_dir}")
        except Exception as e:
            print(f"Error creating directory: {e}")
            return

    try:
        print(f"Processing edition: {edition_name}")

        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--window-size=1920,1080")  # Set window size
        chrome_options.add_argument(
            "--disable-gpu"
        )  # Disable GPU hardware acceleration
        chrome_options.add_argument(
            "--disable-software-rasterizer"
        )  # Disable software rasterizer

        driver = webdriver.Chrome(options=chrome_options)
        driver.get(base_url)
        time.sleep(5)

        processed_areas = set()  # Keep track of processed areas
        page_images = {}  # Keep track of images for each page

        # Get total number of pages
        page_thumbnails = driver.find_elements(By.CSS_SELECTOR, 'div[id^="pgmain"]')
        total_pages = len(page_thumbnails)
        print(f"Found {total_pages} pages")

        # Process each page
        for page_num in range(1, total_pages + 1):
            print(f"\nProcessing page {page_num}")
            page_images[page_num] = []  # Initialize list for this page's images

            # Click on the page thumbnail
            try:
                # Find the page thumbnail
                page_thumbnail = driver.find_element(By.ID, f"pgmain{page_num}")
                if page_thumbnail:
                    # Find the image inside the thumbnail and click it
                    img = page_thumbnail.find_element(By.CLASS_NAME, "pagethumb")
                    driver.execute_script("arguments[0].click();", img)
                    time.sleep(5)  # Wait for page to load

                    # Now process the areas on this page
                    try:
                        print("\nLooking for map elements...")
                        # Find the specific map for this page
                        map_element = driver.find_element(
                            By.CSS_SELECTOR, f'map[name="enewspaper{page_num}"]'
                        )
                        if not map_element:
                            print("No map found on this page. Moving to next page...")
                            continue

                        print(f"Found map for page {page_num}")

                        areas = map_element.find_elements(By.TAG_NAME, "area")
                        print(f"Found {len(areas)} areas in map")

                        # Process all areas in the map
                        for index, area in enumerate(areas):
                            coords = area.get_attribute("coords")
                            if coords in processed_areas:
                                continue

                            onclick = area.get_attribute("onclick")
                            if onclick and "show_pop" in onclick:
                                print(f"\nProcessing area with coords: {coords}")
                                print(f"Onclick JS: {onclick}")

                                # Store the current window handle
                                main_window = driver.current_window_handle

                                # Execute the onclick JS directly
                                driver.execute_script(onclick)
                                time.sleep(5)

                                # Switch to the new tab
                                new_window = [
                                    window
                                    for window in driver.window_handles
                                    if window != main_window
                                ]
                                if new_window:
                                    driver.switch_to.window(new_window[0])
                                    print(f"Switched to new tab: {driver.current_url}")

                                    # Parse the page using BeautifulSoup
                                    soup = BeautifulSoup(
                                        driver.page_source, "html.parser"
                                    )

                                    # Try to find the image tag
                                    img_tag = None

                                    # Method 1: Find in rDivImgouterBox
                                    img_div = soup.find("div", class_="rDivImgouterBox")
                                    if img_div:
                                        img_tag = img_div.find("img")

                                    # Method 2: Find by onclick
                                    if not img_tag:
                                        img_tag = soup.find(
                                            "img", {"onclick": "zoomin(this.id);"}
                                        )

                                    # Method 3: Find any image with epaperimages
                                    if not img_tag:
                                        img_tag = soup.find(
                                            "img",
                                            src=lambda x: x and "epaperimages" in x,
                                        )

                                    if img_tag:
                                        img_url = img_tag.get("src") or img_tag.get(
                                            "data-src"
                                        )
                                        if (
                                            img_url and "epaperimages" in img_url
                                        ):  # Only process epaper images
                                            print(f"Image URL: {img_url}")

                                            # Create temporary directory for this page
                                            download_dir = os.path.join(save_dir,edition_name.lower())
                                            os.makedirs(download_dir, exist_ok=True)
                                            response = requests.get(
                                                img_url,
                                                headers={
                                                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                                                    "Referer": main_url,
                                                },
                                            )

                                            if response.status_code == 200:
                                                filename = f"{paper_name}_{str_date}_article_{page_num}_{index}.jpg"
                                                filepath = os.path.join(
                                                    download_dir, filename
                                                )
                                                with open(filepath, "wb") as f:
                                                    f.write(response.content)
                                                print(f"Image saved: {filepath}")
                                                # processed_areas.add(
                                                #     coords
                                                # )  # Mark this area as processed
                                                # page_images[page_num].append(
                                                #     filepath
                                                # )  # Add to page's images
                                            else:
                                                print(
                                                    f"Failed to download image: HTTP {response.status_code}"
                                                )
                                        else:
                                            print(
                                                "No valid epaper image URL found in tag."
                                            )
                                    else:
                                        print(
                                            "Image tag not found using BeautifulSoup."
                                        )

                                    # Close the current tab and switch back to main window
                                    driver.close()
                                    driver.switch_to.window(main_window)
                                    time.sleep(2)
                                else:
                                    print("No new tab was opened")

                        # After processing all areas, create PDF for this page
                        # if page_images[page_num]:
                        #     os.makedirs(f"{save_dir}/{edition_name}", exist_ok=True)
                        #     pdf_path = os.path.join(
                        #         f"{save_dir}/{edition_name}",
                        #         f"{edition_name}_page_{page_num}.pdf",
                        #     )
                        #     create_pdf_from_images(page_images[page_num], pdf_path)
                        #     # Clean up temporary files
                        #     for img_path in page_images[page_num]:
                        #         try:
                        #             os.remove(img_path)
                        #         except:
                        #             pass

                    except Exception as map_error:
                        print(f"Error processing map: {map_error}")
                        continue

            except Exception as page_error:
                print(f"Error processing page {page_num}: {page_error}")
                # Try to recover the session
                try:
                    driver.quit()
                    driver = webdriver.Chrome(options=chrome_options)
                    driver.get(base_url)
                    time.sleep(5)
                except:
                    break
                continue

            # Wait before moving to next page
            time.sleep(3)

        # Create a combined PDF of all pages
        # all_images = []
        # for page_num in range(1, total_pages + 1):
        #     all_images.extend(page_images[page_num])
        #
        # if all_images:
        #     combined_pdf_path = os.path.join(
        #         f"{save_dir}/{edition_name}", f"{edition_name}_all_pages.pdf"
        #     )
        #     create_pdf_from_images(all_images, combined_pdf_path)

    except Exception as e:
        print(f"Error in main process: {e}")
    finally:
        print("Closing browser...")
        driver.quit()


def get_edition_urls(main_url):
    print("Getting edition URLs...")

    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--start-maximized")

    # Initialize the driver
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(main_url)
    time.sleep(5)  # Wait for initial page load

    edition_data = []

    try:
        # Find all paper columns
        print("Looking for paper columns...")
        paper_cols = driver.find_elements(By.CLASS_NAME, "papercol")
        print(f"Found {len(paper_cols)} editions")

        for paper_col in paper_cols:
            try:
                # Extract edition name
                edition_name = paper_col.find_element(
                    By.CLASS_NAME, "edspan"
                ).text.strip()
                print(f"\nProcessing edition: {edition_name}")

                # Find and click the link
                link = paper_col.find_element(By.TAG_NAME, "a")

                # Get the URL before clicking
                url = link.get_attribute("href")

                if url:
                    print(f"Found edition URL: {url}")
                    edition_data.append({"name": edition_name, "url": url})

            except Exception as e:
                print(f"Error processing paper column: {e}")
                continue

    except Exception as e:
        print(f"Error getting editions: {e}")
    finally:
        print("Closing browser...")
        driver.quit()

    return edition_data


def main():
    # Create main directory
    os.makedirs(save_dir, exist_ok=True)

    # Get all edition URLs
    edition_urls = get_edition_urls(main_url)

    # Process each edition
    for edition in edition_urls:
        print(f"\nProcessing edition: {edition['name']}")
        download_epaper_images(edition["url"], edition["name"])


if __name__ == "__main__":
    main()
