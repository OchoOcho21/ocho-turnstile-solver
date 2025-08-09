import puppeteer from 'puppeteer-extra';
import StealthPlugin from 'puppeteer-extra-plugin-stealth';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

puppeteer.use(StealthPlugin());

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default class Solver {
    constructor(headless = true) {
        this.headless = headless;
    }

    async startBrowser() {
        this.browser = await puppeteer.launch({
            headless: this.headless,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--single-process'
            ]
        });
        const context = await this.browser.createIncognitoBrowserContext();
        this.page = await context.newPage();
    }

    async buildPageData() {
        this.pageData = fs.readFileSync(path.join(__dirname, 'utils', 'page.html'), 'utf-8');
        const stub = `<div class="cf-turnstile" data-sitekey="${this.sitekey}"></div>`;
        this.pageData = this.pageData.replace("<!-- cf turnstile -->", stub);
    }

    async getMousePath(x1, y1, x2, y2) {
        const pathArr = [];
        let x = x1, y = y1;
        while (Math.abs(x - x2) > 3 || Math.abs(y - y2) > 3) {
            let diff = Math.abs(x - x2) + Math.abs(y - y2);
            let speed = Math.random() * (diff < 20 ? 3 : (diff / 45) * 2);
            if (Math.abs(x - x2) > 3) x += x < x2 ? speed : -speed;
            if (Math.abs(y - y2) > 3) y += y < y2 ? speed : -speed;
            pathArr.push([x, y]);
        }
        return pathArr;
    }

    async moveTo(x, y) {
        const pathArr = await this.getMousePath(this.currentX, this.currentY, x, y);
        for (const [px, py] of pathArr) {
            await this.page.mouse.move(px, py);
            if (Math.random() > 0.15) await new Promise(r => setTimeout(r, Math.random() * 10));
        }
    }

    async solveInvisible() {
        for (let i = 0; i < 10; i++) {
            this.randomX = Math.floor(Math.random() * this.windowWidth);
            this.randomY = Math.floor(Math.random() * this.windowHeight);
            await this.moveTo(this.randomX, this.randomY);
            this.currentX = this.randomX;
            this.currentY = this.randomY;
            const elem = await this.page.$("[name=cf-turnstile-response]");
            if (elem) {
                const val = await this.page.evaluate(el => el.value, elem);
                if (val) return val;
            }
            await new Promise(r => setTimeout(r, Math.random() * 10));
        }
        return "failed";
    }

    async solveVisible() {
        let iframe = null;
        while (!iframe) {
            iframe = await this.page.$("iframe");
            await new Promise(r => setTimeout(r, 100));
        }
        let box = await iframe.boundingBox();
        while (!box) {
            await new Promise(r => setTimeout(r, 100));
            box = await iframe.boundingBox();
        }
        let x = box.x + 5 + Math.random() * 12;
        let y = box.y + 5 + Math.random() * 12;
        await this.moveTo(x, y);
        this.currentX = x;
        this.currentY = y;
        const frame = await iframe.contentFrame();
        let checkbox = null;
        while (!checkbox) {
            checkbox = await frame.$('input');
            await new Promise(r => setTimeout(r, 100));
        }
        const cbBox = await checkbox.boundingBox();
        x = cbBox.x + cbBox.width / 2;
        y = cbBox.y + cbBox.height / 2;
        await this.moveTo(x, y);
        this.currentX = x;
        this.currentY = y;
        await new Promise(r => setTimeout(r, Math.random() * 10));
        await this.page.mouse.click(x, y);
        for (let i = 0; i < 10; i++) {
            this.randomX = Math.floor(Math.random() * this.windowWidth);
            this.randomY = Math.floor(Math.random() * this.windowHeight);
            await this.moveTo(this.randomX, this.randomY);
            this.currentX = this.randomX;
            this.currentY = this.randomY;
            const elem = await this.page.$("[name=cf-turnstile-response]");
            if (elem) {
                const val = await this.page.evaluate(el => el.value, elem);
                if (val) return val;
            }
            await new Promise(r => setTimeout(r, Math.random() * 10));
        }
        return "failed";
    }

    async solve(url, sitekey, invisible = false) {
        this.url = url.endsWith("/") ? url : url + "/";
        this.sitekey = sitekey;
        this.invisible = invisible;
        await this.startBrowser();
        await this.buildPageData();
        await this.page.setRequestInterception(true);
        this.page.on('request', request => {
            if (request.url() === this.url) {
                request.respond({ status: 200, body: this.pageData });
            } else {
                request.continue();
            }
        });
        await this.page.goto(this.url, { waitUntil: 'domcontentloaded', timeout: 45000 });
        this.currentX = 0;
        this.currentY = 0;
        this.windowWidth = await this.page.evaluate(() => window.innerWidth);
        this.windowHeight = await this.page.evaluate(() => window.innerHeight);
        const output = this.invisible ? await this.solveInvisible() : await this.solveVisible();
        await this.browser.close();
        return output;
    }
}