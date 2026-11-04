// 数据集明细查看抽屉走查：登录 → 数据集 → 预览（复杂版面已发布）→ 查看 → 截图 / 校验页图加载。
const { chromium } = require('playwright-core');
const path = require('path');

const BASE = 'http://localhost:5173';
const outDir = path.join(__dirname, 'shots');

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

  await page.goto(BASE + '/dataset', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  // 复杂版面已发布数据集所在行
  const row = page.locator('tr', { hasText: '复杂版面' }).filter({ hasText: '已发布' }).first();
  await row.getByRole('button', { name: '预览' }).click();
  await page.waitForTimeout(1200);
  const viewBtn = page.getByRole('button', { name: '查看' }).first();
  await viewBtn.click();
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(outDir, 'dataset-item-viewer.png'), fullPage: true });

  const img = page.locator('.page-image img').first();
  const natural = await img.count() ? await img.evaluate((el) => el.naturalWidth) : 0;
  console.log('page image naturalWidth =', natural);
  console.log('errors =', JSON.stringify([...new Set(errors)], null, 2));
  await browser.close();
  process.exit(natural > 0 && errors.length === 0 ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
