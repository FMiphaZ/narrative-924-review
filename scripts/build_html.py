#!/usr/bin/env python3
"""把 template.html + echarts + 四份数据 JSON 组装成单文件 index.html。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
DATA = ROOT / "data" / "processed"

tpl = (OUT / "template.html").read_text(encoding="utf-8")
echarts = (OUT / "echarts.min.js").read_text(encoding="utf-8")

def load(name):
    return (DATA / name).read_text(encoding="utf-8")

html = tpl.replace("/*__ECHARTS__*/", echarts, 1)
html = html.replace("/*__DATA_EPISODES__*/", load("episodes.json").strip(), 1)
html = html.replace("/*__DATA_INDEX__*/", load("chart_index.json").strip(), 1)
html = html.replace("/*__DATA_BASKETS__*/", load("chart_baskets.json").strip(), 1)
html = html.replace("/*__DATA_STOCKS__*/", load("chart_stocks.json").strip(), 1)
html = html.replace("/*__DATA_EPCHARTS__*/", load("chart_episodes.json").strip(), 1)

assert "/*__" not in html, "仍有未替换的占位符"
(OUT / "index.html").write_text(html, encoding="utf-8")
print(f"index.html written: {len(html)/1024/1024:.2f} MB")

# 抽出业务 JS 做语法检查（最后一个 script 块）
import re
scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
biz = scripts[-1] if scripts else ""
(OUT / "_check.js").write_text(biz, encoding="utf-8")
print("business js extracted for syntax check:", len(scripts), "script blocks")
