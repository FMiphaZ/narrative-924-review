# 9·24 牛市叙事考古复盘

> 研究对象：2024-01-01（熊市末尾）→ 2026-07-24（长鑫科技已发行、未挂牌）的港A牛市。
> 研究单位：**叙事事件段（Narrative Episode）**，跟踪 S=(A叙事, F资金, P价格, E业绩) 四轨的共振与背离。
> 生成时间：2026-07-25 · 数据截止：2026-07-24 收盘（Asia/Shanghai）

## 在线访问

推送到 GitHub 后，Pages 工作流会发布 `output/` 目录。部署成功后可直接分享：

https://fmiphaz.github.io/narrative-924-review/

## 目录结构

```
narrative-924-review/
├── README.md                    ← 本文件
├── data/
│   ├── universe.json            ← 市场指数11个 + 行业/主题基准16个 + 叙事篮子15个（50只标的）与角色定义
│   ├── manifest.json            ← Futu 采集清单（70/70 成功）
│   ├── index/  baskets/         ← 原始日K CSV（time/open/high/low/close/volume/turnover）
│   └── processed/
│       ├── episodes.json        ← 叙事事件主表（24段）+ 时间轴事件(65个) + 五底六顶 + 微观事件(120个)
│       ├── chart_index.json     ← 指数日线（收盘/归一化）+ 全A/全港成交额
│       ├── chart_baskets.json   ← 篮子等权指数、相对强弱、成交额、占全A比例
│       ├── chart_stocks.json    ← 个股周频归一化、月度收益、底/顶/回撤标记
│       └── chart_episodes.json  ← 每张叙事卡片的窗口日频数据（成员点位/成交额/全A成交额）
├── notes/
│   ├── timeline-2024.md         ← 2024 叙事考古底稿（当时信源，225行）
│   ├── timeline-2025H1.md       ← 2025H1 底稿（358行）
│   └── timeline-2025H2-2026.md  ← 2025H2~2026-07 底稿（381行）
├── scripts/
│   ├── fetch_klines.py          ← Futu OpenD 日K采集（只读行情；45s看门狗+断点续传）
│   ├── process_data.py          ← 四轨指标加工
│   ├── merge_micro.py           ← 微观事件（财报/研报/政策）合并进 episodes.json
│   └── build_html.py            ← 单文件网页组装
└── output/
    ├── index.html               ← ★ 最终交互式复盘网页（2.5MB，自包含，双击即开）
    ├── template.html            ← 网页模板
    ├── echarts.min.js           ← ECharts 5.5.1（内联用）
    ├── _smoke.js                ← Node 冒烟测试（桩件环境跑全部业务JS）
    └── _browser_test.js         ← playwright-core + 系统Chrome 真实渲染测试
```

## 交互说明（v2）

- **四张时间图缩放联动**：在主图/生命周期图/迁移图上拖动或滚轮缩放，其余图同步（echarts.connect）。
- **点击叙事聚焦**：点击泳道横带 / 生命周期横带 / 目录标签 → 所有时间图聚焦该叙事窗口（±10天）、价格轨高亮窗口、自动展开对应叙事卡片。
- **重置视图**按钮：清除高亮并恢复全局时间范围。
- **行业基准模式**：主图第三个视图——16个行业/主题基准的归一化点位（实线）+ 对应成交额（虚线·量）。芯片采用中证全指半导体产品与设备指数的 `512480` ETF 跟踪口径；通信采用国证通信；创新药同时展示生物医药、恒生医疗保健和恒生生物科技。光伏→国证新能、稀土→国证有色仍为代理口径。
- **叙事卡片微观图表**（展开卡片时懒加载）：上=标的点位**全期走势**（首日=100，橙色带=叙事窗口），默认聚焦窗口前后各90天，拖动底部滑块可看全期前后发展；下=各标的成交额（本币）；粗竖线=生命周期阶段，细虚线=微观事件（政策/宏观/财报/研报/资金/事件，悬停显名），下方另附事件清单。
- 迁移图默认只显示 6 条主线（红利/券商/半导体/DeepSeek/算力/存储），其余在图例中点开。

## 方法论要点

1. **先扫描后叙事**：篮子标的基于"当时价格/成交异常"窗口选取，再用当时资料（政策原文、新闻标题、研报措辞）重建叙事，避免事后编故事。叙事原话与反证条件是每段卡片的必填字段。
2. **底顶拆分**：市场级底部拆为绝对价格底（2024-09-18 2689.70）/资金底（2024-08-13 地量4773亿）/叙事底（2024-09-24）/相对强弱底/基本面底（2025年滞后确认）；顶部拆为六次观测（三次拥挤顶 + 价格顶先于资金顶的结构）。
3. **资金证据分级**：强证据（两融关键点、南向月度、ETF周度净申购）/中证据（篮子成交占比=注意力代理）/弱证据（新闻热度）。成交占比**不是**净流入。
4. **口径**：全A成交额=上证+深证成指成交额；北向数据因2024-08-19披露调整不使用连续序列；红利/成长红涨绿跌按A股惯例。

## 复现方式

```bash
# 1. 采集（需 Futu OpenD 运行于 127.0.0.1:11111）
../archive/tri-market-intelligence/.venv/bin/python scripts/fetch_klines.py
# 2. 加工
../archive/tri-market-intelligence/.venv/bin/python scripts/process_data.py
# 3. 组装 + 冒烟测试
../archive/tri-market-intelligence/.venv/bin/python scripts/build_html.py
node output/_smoke.js                    # Node 桩件冒烟测试
# 4. 真实浏览器渲染测试（需系统 Chrome + playwright-core）
cd output && NODE_PATH=~/.workbuddy/binaries/node/workspace/node_modules node _browser_test.js
```

## 排障记录（2026-07-25 修复）

首版网页在浏览器中图表/表格全部不显示，根因有两处：
1. **ECharts 跨网格绑定**：绝对点位模式下港股价格系列被绑到成交额轴（x 轴在价格网格、y 轴在资金网格），`setOption` 直接抛异常，首屏渲染中断，后续图表与 DOM 表格全部未执行。修复：统一 5 条 yAxis（泳道/价格左/资金左/价格右/资金右），按网格固定索引。
2. **custom series renderItem 中取 `params.data`**：renderItem 的 params 不含原始数据项，需用 `params.dataIndex` 从闭包数组取数（叙事泳道与生命周期图两处）。

教训：Node 桩件冒烟测试只能抓引用错误，**ECharts 配置错误必须真实浏览器渲染才能暴露**；测试入口为 `output/_browser_test.js`（playwright-core 驱动系统 Chrome 无头模式，校验 canvas 数量、表格行数、控制台错误、点击联动）。

## 已知缺口（诚实清单）

- ETF 分日申赎、两融逐日官方序列（网页中两融为当时报道关键点插值连线）
- 南向 2026 年逐月净买入
- 化债/机器人/雅下等题材板块成交日度
- 篮子标的为事后代表性样本，存在幸存者偏差

## 免责声明

事实 / 分析推断 / 前瞻情景已分层标注；全部内容截至 2026-07-24，不构成投资建议。
