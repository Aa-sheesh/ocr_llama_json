"""
Clipped Article Images
"""
import asyncio
import os
from datetime import datetime

from playwright.async_api import async_playwright, \
    TimeoutError as PlaywrightTimeoutError


class DeccanHeraldScraper:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.publication_name = "deccan_herald"
        self.edition_name = "national_edition   "
        self.date = datetime.now().strftime("%d_%m_%Y")

    async def start(self):
        async with async_playwright() as p:
            self.browser = await p.chromium.launch(headless=True)
            self.context = await self.browser.new_context(
                accept_downloads=True)
            self.page = await self.context.new_page()
            await self.page.goto("https://epaper.deccanherald.com/")
            await self.login()
            await self.download_articles()
            await self.logout()
            await self.browser.close()

    async def login(self):
        login_tab = self.page.locator('a[data-toggle="pill"][href="#login"]')
        login_tab_li = login_tab.locator('xpath=..')
        if "active" not in (await login_tab_li.get_attribute("class") or ""):
            await login_tab.click()
        await self.page.fill('input[name="Email"]',
                             'Subscriptions@AAIZELTECH.com')
        await self.page.fill('input[name="Password"]', 'A@izel@123')
        await self.page.click('button:has-text("LOGIN")')
        try:
            await self.page.wait_for_selector("#btnyes", timeout=3000)
            await self.page.click("#btnyes")
        except PlaywrightTimeoutError:
            pass

    async def download_articles(self):
        await self.page.wait_for_selector("#UlPages", timeout=10000)
        page_items = self.page.locator("#UlPages li.has-sub ul.pg_thumb > li")
        page_count = await page_items.count()

        seen_ids = set()

        for page_index in range(page_count):
            await page_items.nth(page_index).click()

            active_class = ""
            retry = 0
            while "active" not in active_class and retry < 5:
                await asyncio.sleep(1)
                active_class = await page_items.nth(page_index).get_attribute(
                    "class") or ""
                retry += 1

            try:
                await self.page.wait_for_selector(
                    "#ImageContainer .pagerectangle", timeout=10000)
            except PlaywrightTimeoutError:
                print(f"Page {page_index + 1} content not loaded, retrying...")

            rects = self.page.locator("#ImageContainer .pagerectangle")

            article_count = await rects.count()
            if article_count == 0:
                print(
                    f"No articles found on page {page_index + 1}, retrying after delay")
                await asyncio.sleep(3)

            for article_index in range(await rects.count()):
                rect = rects.nth(article_index)
                try:
                    story_id = await rect.get_attribute("storyid")

                except PlaywrightTimeoutError:
                    continue

                if not story_id or story_id in seen_ids:
                    continue
                seen_ids.add(story_id)

                try:
                    await rect.scroll_into_view_if_needed()
                except Exception:
                    continue

                box = await rect.bounding_box()
                if not box:
                    continue

                await self.page.mouse.click(
                    box["x"] + box["width"] / 2,
                    box["y"] + box["height"] / 2
                )
                await asyncio.sleep(2)

                try:
                    await self.page.wait_for_selector("#PageListViewToolbar",
                                                      timeout=5000)
                    await self.page.wait_for_selector("#downloadImage",
                                                      timeout=5000)
                    async with self.page.expect_download() as download_info:
                        await self.page.click("#downloadImage")
                    download = await download_info.value
                    await self.save_download(download, page_index,
                                             article_index)
                    await asyncio.sleep(4)
                except PlaywrightTimeoutError:
                    continue

    async def save_download(self, download, page_index, article_index):
        path = os.path.join(
            "downloads", self.publication_name,
            self.edition_name
        )
        os.makedirs(path, exist_ok=True)
        filename = f"{self.publication_name}{self.date}{page_index + 1}{article_index + 1}.jpg"
        await download.save_as(os.path.join(path, filename))

    async def logout(self):
        try:
            await self.page.click("#toggle-sidebar-right")
            await self.page.wait_for_selector("#LogoutId", timeout=3000)
            await self.page.click("#LogoutId")
        except PlaywrightTimeoutError:
            pass


if __name__ == "__main__":
    asyncio.run(DeccanHeraldScraper().start())
