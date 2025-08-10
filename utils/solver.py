import asyncio
import random
import time

class Solver:
    def __init__(self, proxy="", headless=True):
        self.proxy = proxy
        self.headless = headless
        self.browser = None
        self.page = None
        self.context = None

    async def start_browser(self):
        if self.proxy:
            self.browser = await pyppeteer.launch(
                headless=self.headless,
                args=[f'--proxy-server=http://{self.proxy.split("@")[1]}'],
                ignoreHTTPSErrors=True
            )
        else:
            self.browser = await pyppeteer.launch(
                headless=self.headless,
                ignoreHTTPSErrors=True
            )

    async def terminate(self):
        await self.browser.close()

    def build_page_data(self):
        with open("utils/page.html") as f:
            self.page_data = f.read()
        stub = f'<div class="cf-turnstile" data-sitekey="{self.sitekey}"></div>'
        self.page_data = self.page_data.replace("<!-- cf turnstile -->", stub)

    def get_mouse_path(self, x1, y1, x2, y2):
        path = []
        x = x1
        y = y1
        while abs(x - x2) > 3 or abs(y - y2) > 3:
            diff = abs(x - x2) + abs(y - y2)
            speed = random.randint(1, 2)
            if diff < 20:
                speed = random.randint(1, 3)
            else:
                speed *= diff / 45

            if abs(x - x2) > 3:
                if x < x2:
                    x += speed
                elif x > x2:
                    x -= speed
            if abs(y - y2) > 3:
                if y < y2:
                    y += speed
                elif y > y2:
                    y -= speed
            path.append((x, y))

        return path

    async def move_to(self, x, y):
        for path in self.get_mouse_path(self.current_x, self.current_y, x, y):
            await self.page.mouse.move(path[0], path[1])
            if random.randint(0, 100) > 15:
                await asyncio.sleep(random.randint(1, 5) / random.randint(400, 600))

    async def solve_invisible(self):
        iterations = 0

        while iterations < 10:
            self.random_x = random.randint(0, self.window_width)
            self.random_y = random.randint(0, self.window_height)
            iterations += 1

            await self.move_to(self.random_x, self.random_y)
            self.current_x = self.random_x
            self.current_y = self.random_y
            elem = await self.page.querySelector("[name=cf-turnstile-response]")
            if elem:
                value = await self.page.evaluate('(elem) => elem.value', elem)
                if value:
                    return value
            await asyncio.sleep(random.randint(2, 5) / random.randint(400, 600))
        return "failed"

    async def solve_visible(self):
        iframe = await self.page.querySelector("iframe")
        while not iframe:
            iframe = await self.page.querySelector("iframe")
            await asyncio.sleep(0.1)
        
        box = await iframe.boundingBox()
        while not box:
            await asyncio.sleep(0.1)
            box = await iframe.boundingBox()

        x = box["x"] + random.randint(5, 12)
        y = box["y"] + random.randint(5, 12)
        await self.move_to(x, y)
        self.current_x = x
        self.current_y = y
        
        frame = await iframe.contentFrame()
        checkbox = await frame.querySelector("input")

        while not checkbox:
            checkbox = await frame.querySelector("input")
            await asyncio.sleep(0.1)

        checkbox_box = await checkbox.boundingBox()
        width = checkbox_box["width"]
        height = checkbox_box["height"]

        x = checkbox_box["x"] + width / 5 + random.randint(int(width / 5), int(width - width / 5))
        y = checkbox_box["y"] + height / 5 + random.randint(int(height / 5), int(height - height / 5))

        await self.move_to(x, y)
        self.current_x = x
        self.current_y = y

        await asyncio.sleep(random.randint(1, 5) / random.randint(400, 600))
        await self.page.mouse.click(x, y)

        iterations = 0

        while iterations < 10:
            self.random_x = random.randint(0, self.window_width)
            self.random_y = random.randint(0, self.window_height)
            iterations += 1

            await self.move_to(self.random_x, self.random_y)
            self.current_x = self.random_x
            self.current_y = self.random_y
            elem = await self.page.querySelector("[name=cf-turnstile-response]")
            if elem:
                value = await self.page.evaluate('(elem) => elem.value', elem)
                if value:
                    return value
            await asyncio.sleep(random.randint(2, 5) / random.randint(400, 600))
        return "failed"

    async def solve(self, url, sitekey, invisible=False):
        self.url = url + "/" if not url.endswith("/") else url
        self.sitekey = sitekey
        self.invisible = invisible
        
        await self.start_browser()
        self.context = await self.browser.createIncognitoBrowserContext()
        self.page = await self.context.newPage()

        self.build_page_data()

        await self.page.setRequestInterception(True)
        
        async def intercept(request):
            if request.url == self.url:
                await request.respond({
                    'body': self.page_data,
                    'status': 200
                })
            else:
                await request.continue_()
        
        self.page.on('request', lambda req: asyncio.ensure_future(intercept(req)))
        
        await self.page.goto(self.url)
        output = "failed"
        self.current_x = 0
        self.current_y = 0

        self.window_width = await self.page.evaluate("window.innerWidth")
        self.window_height = await self.page.evaluate("window.innerHeight")
        
        if self.invisible:
            output = await self.solve_invisible()
        else:
            output = await self.solve_visible()

        await self.context.close()
        await self.terminate()
        return output