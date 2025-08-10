import asyncio
import random
import time
import sys
import subprocess
import os
from pyppeteer import launch

class Solver:
    def __init__(self, proxy="", headless=True):
        self.proxy = proxy
        self.headless = headless
        self.browser = None
        self.page = None
        self.context = None

    async def start_browser(self):
        args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--disable-gpu',
            '--single-process'
        ]
        if self.proxy:
            args.append(f'--proxy-server={self.proxy}')
        
        self.browser = await launch(
            headless=self.headless,
            args=args,
            ignoreHTTPSErrors=True,
            autoClose=False,
            handleSIGINT=False,
            handleSIGTERM=False,
            handleSIGHUP=False
        )
        return True

    async def terminate(self):
        try:
            if self.page and not self.page.isClosed():
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
        except:
            pass

    def build_page_data(self):
        with open("utils/page.html") as f:
            self.page_data = f.read()
        self.page_data = self.page_data.replace(
            "<!-- cf turnstile -->",
            f'<div class="cf-turnstile" data-sitekey="{self.sitekey}"></div>'
        )

    async def solve(self, url, sitekey, invisible=False):
        self.url = url if url.endswith("/") else url + "/"
        self.sitekey = sitekey
        self.invisible = invisible

        if not await self.start_browser():
            return "failed"

        try:
            self.context = await self.browser.createIncognitoBrowserContext()
            self.page = await self.context.newPage()
            self.build_page_data()

            await self.page.setRequestInterception(True)
            self.page.on('request', lambda req: asyncio.ensure_future(
                req.respond({
                    'body': self.page_data,
                    'status': 200
                }) if req.url == self.url else req.continue_()
            ))

            await self.page.goto(self.url, {
                'timeout': 30000,
                'waitUntil': 'domcontentloaded'
            })

            self.current_x = 0
            self.current_y = 0
            self.window_width = await self.page.evaluate("window.innerWidth")
            self.window_height = await self.page.evaluate("window.innerHeight")

            if self.invisible:
                return await self.solve_invisible()
            return await self.solve_visible()
        except Exception as e:
            print(f"Solve error: {str(e)}")
            return "failed"
        finally:
            await self.terminate()

    async def solve_invisible(self):
        for _ in range(10):
            x = random.randint(0, self.window_width)
            y = random.randint(0, self.window_height)
            await self.move_mouse(x, y)
            elem = await self.page.querySelector("[name=cf-turnstile-response]")
            if elem:
                value = await self.page.evaluate('(elem) => elem.value', elem)
                if value:
                    return value
            await asyncio.sleep(0.1)
        return "failed"

    async def solve_visible(self):
        iframe = await self.wait_for_selector("iframe")
        box = await iframe.boundingBox()
        x = box["x"] + random.randint(5, 12)
        y = box["y"] + random.randint(5, 12)
        await self.move_mouse(x, y)

        frame = await iframe.contentFrame()
        checkbox = await self.wait_for_selector("input", frame)
        box = await checkbox.boundingBox()
        x = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] / 2
        await self.move_mouse(x, y)
        await self.page.mouse.click(x, y)

        for _ in range(10):
            await self.move_mouse(
                random.randint(0, self.window_width),
                random.randint(0, self.window_height)
            )
            elem = await self.page.querySelector("[name=cf-turnstile-response]")
            if elem:
                value = await self.page.evaluate('(elem) => elem.value', elem)
                if value:
                    return value
            await asyncio.sleep(0.1)
        return "failed"

    async def move_mouse(self, x, y):
        steps = 10
        dx = (x - self.current_x) / steps
        dy = (y - self.current_y) / steps
        for _ in range(steps):
            self.current_x += dx
            self.current_y += dy
            await self.page.mouse.move(self.current_x, self.current_y)
            await asyncio.sleep(random.uniform(0.01, 0.05))

    async def wait_for_selector(self, selector, frame=None):
        for _ in range(30):
            element = await (frame or self.page).querySelector(selector)
            if element:
                return element
            await asyncio.sleep(0.1)
        raise Exception(f"Element {selector} not found")