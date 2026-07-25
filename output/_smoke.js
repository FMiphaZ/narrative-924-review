// 冒烟测试：桩件环境下执行业务 JS，捕获运行时错误
const fs = require('fs');
const path = require('path');
const html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);

// ---- 桩件 ----
const elements = {};
function makeEl(id) {
  return {
    id, _innerHTML: '', style: {},
    set innerHTML(v) { this._innerHTML = v; if (typeof v === 'string' && v.includes('undefined')) console.error(`[WARN] #${id} innerHTML contains "undefined"`); },
    get innerHTML() { return this._innerHTML; },
    classList: { toggle() {}, add() {}, remove() {} },
    scrollIntoView() {},
    addEventListener() {},
    set onclick(fn) { this._onclick = fn; },
    get onclick() { return this._onclick; },
    open: false,
  };
}
const documentStub = {
  getElementById(id) { if (!elements[id]) elements[id] = makeEl(id); return elements[id]; },
};
const charts = [];
const echartsStub = {
  init(el) {
    const c = { el, options: [],
      setOption(opt, notMerge) {
        // 基本结构校验
        const s = JSON.stringify(opt, (k, v) => typeof v === 'function' ? '__fn__' : v);
        if (s.includes('undefined')) console.error(`[WARN] chart option for #${el.id} contains "undefined"`);
        if (s.includes('NaN')) console.error(`[WARN] chart option for #${el.id} contains NaN`);
        this.options.push(opt);
      },
      on() {}, resize() {}, dispatchAction() {} };
    charts.push(c); return c;
  },
  connect() {}
};
const windowStub = { addEventListener() {}, _hlRange: null };

// ---- 执行数据与业务脚本（跳过 echarts 库本体） ----
const context = {
  document: documentStub, window: windowStub, echarts: echartsStub,
  console, JSON, Object, Array, Math, Date, Number, String, Set, Map, RegExp, parseInt, parseFloat, isNaN,
  setTimeout: (fn) => 0,
};
const vm = require('vm');
vm.createContext(context);
for (const code of scripts.slice(1)) { // scripts[0] 是 echarts 库
  try {
    vm.runInContext(code, context, { timeout: 15000 });
  } catch (e) {
    console.error('[FAIL] script block error:', e.message);
    console.error(e.stack.split('\n').slice(0, 4).join('\n'));
    process.exit(1);
  }
}
// 检查关键产物
const need = ['regimeBox', 'statBox', 'expectTable', 'epToc', 'epCards', 'bottomTable', 'topTable', 'limitBox'];
let ok = true;
need.forEach(id => {
  const el = elements[id];
  if (!el || !el._innerHTML || el._innerHTML.length < 20) { console.error(`[FAIL] #${id} empty`); ok = false; }
});
console.log(`charts initialized: ${charts.length} (expect 5)`);
charts.forEach((c, i) => {
  const opt = c.options[0];
  console.log(`  chart#${i} el=#${c.el.id} series=${opt.series ? opt.series.length : 0}`);
});
// 测试叙事点击联动
try {
  vm.runInContext("selectEpisode('EP04'); selectEpisode('EP18');", context);
  console.log('selectEpisode ok');
} catch (e) { console.error('[FAIL] selectEpisode:', e.message); ok = false; }
// 测试切换按钮
try {
  vm.runInContext("document.getElementById('btnNorm').onclick(); document.getElementById('btnAbs').onclick();", context);
  console.log('mode toggle ok');
} catch (e) { console.error('[FAIL] mode toggle:', e.message); ok = false; }
console.log(ok ? 'SMOKE PASS' : 'SMOKE FAIL');
process.exit(ok ? 0 : 1);
