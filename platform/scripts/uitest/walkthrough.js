// 前端页面走查：Edge 无头模式登录后逐页截图，收集控制台错误与失败请求。
// 用法：node walkthrough.js <taskId> <reviewOrderId> [输出目录]
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const BASE = 'http://localhost:5173';
const taskId = process.argv[2];
const orderId = process.argv[3];
const outDir = process.argv[4] || path.join(__dirname, 'shots');
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('response', r => { if (r.status() >= 400) errors.push(`http ${r.status()}: ${r.url()}`); });

  await page.goto(BASE + '/login', { waitUntil: 'networkidle' });
  await page.getByPlaceholder('账号').fill('admin');
  await page.getByPlaceholder('密码').fill('admin123');
  await page.getByRole('button', { name: '登 录' }).click();
  await page.waitForURL('**/wb/metadata', { timeout: 15000 });
  await page.waitForLoadState('networkidle');

  const pages = [
    ['wb-metadata', '/wb/metadata'],
    ['wb-layout', '/wb/layout'],
    ['wb-formula', '/wb/formula'],
    ['wb-graphic', '/wb/graphic'],
    ['task-detail', `/task/${taskId}`],
    ['material', '/material'],
    ['review', '/review'],
    ['review-drawer', `/review?orderId=${orderId}`],
    ['dataset', '/dataset'],
    ['params', '/params'],
  ];
  const report = {};
  for (const [name, url] of pages) {
    await page.goto(BASE + url, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1200);
    await page.screenshot({ path: path.join(outDir, name + '.png'), fullPage: true });
    const text = (await page.locator('body').innerText()).replace(/\s+/g, ' ').slice(0, 600);
    report[name] = { url, text };
    console.log(`[shot] ${name} ${url}`);
  }
  report.errors = [...new Set(errors)];
  fs.writeFileSync(path.join(outDir, 'report.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report.errors, null, 2));
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
