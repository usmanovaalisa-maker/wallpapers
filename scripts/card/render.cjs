// Локальная отрисовка тем же шаблоном через Playwright, поставляемый с Codex.
const fs = require('node:fs');
const {pathToFileURL} = require('node:url');
const {chromium} = require('playwright');

(async () => {
  const {template, output, args} = JSON.parse(fs.readFileSync(0, 'utf8'));
  const browser = await chromium.launch(process.env.CHROME_PATH
    ? {executablePath: process.env.CHROME_PATH} : {channel: 'chrome'});
  try {
    const page = await browser.newPage({viewport: {width: 1080, height: 1080}});
    await page.goto(pathToFileURL(template).href);
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(a => window.fill(...a), args);
    await page.waitForFunction(() => Array.from(document.images).every(i => i.complete && i.naturalWidth > 0));
    await page.screenshot({path: output, type: 'jpeg', quality: 90});
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
