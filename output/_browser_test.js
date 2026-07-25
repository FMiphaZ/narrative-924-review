// 用系统 Chrome 无头渲染 index.html，捕获控制台错误并截图
const { chromium } = require('playwright-core');
const path = require('path');

(async () => {
  const browser = await chromium.launch({
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless: true,
  });
  const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 300)); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + String(e).slice(0, 300)));
  const file = 'file://' + path.resolve(__dirname, 'index.html');
  await page.goto(file, { waitUntil: 'load', timeout: 60000 });
  await page.waitForTimeout(4000);

  // 每个图表容器里是否有 canvas
  const ids = ['mainChart', 'lifeChart', 'flowChart', 'flowHKChart', 'heatChart'];
  for (const id of ids) {
    const info = await page.evaluate((id) => {
      const el = document.getElementById(id);
      const cvs = el ? el.querySelectorAll('canvas').length : 0;
      return { canvas: cvs, h: el ? el.offsetHeight : 0 };
    }, id);
    console.log(`#${id}: canvas=${info.canvas} height=${info.h}`);
  }
  // 表格是否渲染
  const tbl = await page.evaluate(() => ({
    expect: document.querySelectorAll('#expectTable tbody tr').length,
    bottom: document.querySelectorAll('#bottomTable tbody tr').length,
    cards: document.querySelectorAll('#epCards details').length,
  }));
  console.log('tables:', JSON.stringify(tbl));

  await page.screenshot({ path: path.join(__dirname, '_shot_top.png') });
  await page.evaluate(() => window.scrollTo(0, 900));
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(__dirname, '_shot_main.png') });
  // 测试切换到归一化
  await page.click('#btnNorm');
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(__dirname, '_shot_norm.png') });
  // 行业基准模式应包含新增的半导体、通信与港股创新药基准
  await page.click('#btnInd');
  await page.waitForTimeout(800);
  const industry = await page.evaluate(() => {
    const c = echarts.getInstanceByDom(document.getElementById('mainChart'));
    return c.getOption().series.map(s => s.name);
  });
  for (const name of ['中证半导体（512480跟踪）', '国证通信', '恒生生物科技']) {
    if (!industry.includes(name)) throw new Error(`industry mode missing ${name}`);
  }
  await page.screenshot({ path: path.join(__dirname, '_shot_industry.png') });

  // 展开两张有新增基准的卡片，并核验价格线颜色均唯一且不使用黑/深灰色。
  async function inspectEpisode(id, expectedNames) {
    await page.evaluate((id) => {
      const details = document.getElementById('ep-' + id);
      details.open = true;
      details.dispatchEvent(new Event('toggle'));
    }, id);
    await page.waitForTimeout(500);
    const info = await page.evaluate((id) => {
      const chart = echarts.getInstanceByDom(document.getElementById('epc-' + id));
      const price = chart.getOption().series
        .filter(s => !s.name.endsWith('·量') && s.name !== '全A成交额(亿元)')
        .map(s => ({ name: s.name, color: s.lineStyle && s.lineStyle.color }));
      return { canvas: document.querySelectorAll('#epc-' + id + ' canvas').length, price };
    }, id);
    if (!info.canvas) throw new Error(`${id} card chart did not render`);
    for (const name of expectedNames) {
      if (!info.price.some(s => s.name === name)) throw new Error(`${id} missing ${name}`);
    }
    const colors = info.price.map(s => s.color);
    if (new Set(colors).size !== colors.length) throw new Error(`${id} has repeated price-line colors`);
    if (colors.some(c => ['#0f172a', '#334155', '#64748b', '#94a3b8'].includes(String(c).toLowerCase()))) {
      throw new Error(`${id} still uses a black/gray price line`);
    }
    console.log(`${id} lines:`, JSON.stringify(info.price));
  }
  await inspectEpisode('EP09', ['恒生科技(指数)', '国证通信(指数)', '中证传媒(指数)']);
  await inspectEpisode('EP13', ['生物医药(指数)', '恒生医疗保健(指数)', '恒生生物科技(指数)']);
  await page.locator('#ep-EP13').scrollIntoViewIfNeeded();
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(__dirname, '_shot_card_ep13.png') });
  // 测试点击叙事泳道联动
  await page.click('#btnAbs');
  await page.waitForTimeout(600);

  console.log(errors.length ? 'CONSOLE ERRORS:\n' + errors.join('\n---\n') : 'NO CONSOLE ERRORS');
  await browser.close();
})().catch(e => { console.error('TEST CRASH:', e.message); process.exit(1); });
