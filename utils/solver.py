import asyncio
import random
import time
import sys
import subprocess
from pyppeteer import launch

class Solver:
    def __init__(self, proxy="", headless=True):
        self.proxy = proxy
        self.headless = headless
        self.browser = None
        self.page = None
        self.current_pos = [0, 0]
        self.window_size = [0, 0]

    async def _init_browser(self):
        args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage'
        ]
        if self.proxy:
            args.append(f'--proxy-server={self.proxy}')
        
        try:
            self.browser = await launch({
                'headless': self.headless,
                'args': args,
                'ignoreHTTPSErrors': True,
                'timeout': 60000
            })
        except Exception as e:
            print(f"Browser launch failed: {str(e)}")
            raise

    async def _create_page(self):
        self.page = await self.browser.newPage()
        await self.page.setViewport({'width': 1280, 'height': 720})

    def _build_page_data(self, sitekey):
        with open("utils/page.html") as f:
            return f.read().replace(
                "<!-- cf turnstile -->",
                f'<div class="cf-turnstile" data-sitekey="{sitekey}"></div>'
            )

    async def _safe_close(self):
        if hasattr(self, 'browser') and self.browser:
            await self.browser.close()

    async def solve(self, url, sitekey, invisible=False):
        try:
            await self._init_browser()
            await self._create_page()
            
            page_data = self._build_page_data(sitekey)
            await self.page.setRequestInterception(True)
            
            async def intercept(req):
                if req.url == url:
                    await req.respond({'body': page_data, 'status': 200})
                else:
                    await req.continue_()
            
            self.page.on('request', lambda r: asyncio.ensure_future(intercept(r)))
            await self.page.goto(url, {'timeout': 30000})
            
            self.window_size = [
                await self.page.evaluate("window.innerWidth"),
                await self.page.evaluate("window.innerHeight")
            ]

            for _ in range(15):
                target = [
                    random.randint(50, self.window_size[0]-50),
                    random.randint(50, self.window_size[1]-50)
                ]
                await self._move_mouse(*target)
                if solution := await self._check_solution():
                    return solution
                await asyncio.sleep(random.uniform(0.1, 0.3))

            return "failed"
        except Exception as e:
            print(f"Solve error: {str(e)}")
            return "failed"
        finally:
            await self._safe_close()

    async def _move_mouse(self, x, y):
        steps = random.randint(5, 15)
        dx = (x - self.current_pos[0]) / steps
        dy = (y - self.current_pos[1]) / steps
        
        for i in range(1, steps + 1):
            new_x = self.current_pos[0] + dx * i
            new_y = self.current_pos[1] + dy * i
            await self.page.mouse.move(new_x, new_y)
            await asyncio.sleep(random.uniform(0.01, 0.05))
        
        self.current_pos = [x, y]

    async def _check_solution(self):
        try:
            elem = await self.page.querySelector("[name=cf-turnstile-response]")
            if elem:
                return await self.page.evaluate('(e) => e.value', elem)
        except:
            return None