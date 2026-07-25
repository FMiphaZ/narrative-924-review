#!/usr/bin/env python3
"""把原始日K加工成网页所需的四轨数据结构。

输出（data/processed/）：
  chart_index.json    指数日线（收盘+归一化+全A/全港成交额）
  chart_baskets.json  叙事篮子：等权价格指数、成交额、占全市场比例、相对强弱
  chart_stocks.json   个股：归一化收盘（周频）、月度收益热力矩阵、关键底/顶标记
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "processed"


def load_csv(code):
    f = DATA / ("index" if code.startswith(("SH.000", "SZ.399", "HK.800")) else "baskets") / f"{code.replace('.', '_')}.csv"
    if not f.exists():
        f2 = DATA / "index" / f"{code.replace('.', '_')}.csv"
        f3 = DATA / "baskets" / f"{code.replace('.', '_')}.csv"
        f = f2 if f2.exists() else f3
    df = pd.read_csv(f)
    df["date"] = pd.to_datetime(df["time_key"]).dt.strftime("%Y-%m-%d")
    return df.set_index("date").sort_index()


def main():
    uni = json.loads((DATA / "universe.json").read_text(encoding="utf-8"))

    # ---------- 1. 指数（市场指数 + 行业指数） ----------
    idx_series = {}
    all_dates = set()
    for ix in uni["indexes"] + uni.get("industry_indexes", []):
        code = ix["code"]
        if code in idx_series:
            continue
        try:
            df = load_csv(code)
        except Exception as e:
            print("skip index", code, e)
            continue
        s = df["close"].dropna()
        base = s.iloc[0]
        entry = {
            "name": ix["name"],
            "close": {d: round(v, 2) for d, v in s.items()},
            "norm": {d: round(v / base * 100, 2) for d, v in s.items()},
        }
        if "turnover" in df.columns:
            entry["turnover"] = {d: round(v / 1e8, 2)
                                 for d, v in df["turnover"].items() if pd.notna(v)}
        idx_series[code] = entry
        all_dates.update(s.index)

    # 全A成交额 = 上证 + 深证成指成交额；全港 = 恒指成交额
    def turnover_of(code):
        try:
            return load_csv(code)["turnover"]
        except Exception:
            return pd.Series(dtype=float)

    to_sh, to_sz = turnover_of("SH.000001"), turnover_of("SZ.399001")
    total_a = pd.concat([to_sh, to_sz], axis=1).sum(axis=1, min_count=1)
    to_hk = turnover_of("HK.800000")
    all_dates = sorted(all_dates)
    chart_index = {
        "dates": all_dates,
        "series": idx_series,
        "turnover_a": {d: (round(v / 1e8, 1) if pd.notna(v) else None)
                       for d, v in total_a.reindex(all_dates).items()},  # 亿元
        "turnover_hk": {d: (round(v / 1e8, 1) if pd.notna(v) else None)
                        for d, v in to_hk.reindex(all_dates).items()},  # 亿港元
    }
    (OUT / "chart_index.json").write_text(
        json.dumps(chart_index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("chart_index ok, dates:", len(all_dates))

    # ---------- 2. 叙事篮子 ----------
    bench_a = load_csv("SH.000300")["close"]   # 沪深300
    bench_hk = load_csv("HK.800000")["close"]  # 恒指
    baskets_out = {}
    for bkey, b in uni["baskets"].items():
        members, member_norm = [], []
        to_a_parts, to_hk_parts = [], []
        n_hk = sum(1 for s in b["stocks"] if s["code"].startswith("HK"))
        is_hk = n_hk == len(b["stocks"])
        for st in b["stocks"]:
            try:
                df = load_csv(st["code"])
            except Exception as e:
                print("  miss", st["code"], e)
                continue
            close = df["close"].dropna()
            member_norm.append(close / close.iloc[0] * 100)
            if st["code"].startswith("HK"):
                to_hk_parts.append(df["turnover"])
            else:
                to_a_parts.append(df["turnover"])
            members.append({"code": st["code"], "name": st["name"], "role": st["role"]})
        if not member_norm:
            continue
        price = pd.concat(member_norm, axis=1).mean(axis=1, skipna=True)
        bench = bench_hk if is_hk else bench_a
        rs = (price / bench.reindex(price.index).ffill() * 100).dropna()
        rs = rs / rs.iloc[0] * 100
        to_a = sum(to_a_parts) if to_a_parts else None
        to_hk = sum(to_hk_parts) if to_hk_parts else None
        share = (to_a / total_a.reindex(to_a.index) * 100).dropna() if to_a is not None else None
        baskets_out[bkey] = {
            "name": b["name"], "market": "HK" if is_hk else "A",
            "members": members,
            "dates": [d for d in price.index],
            "price": {d: round(v, 2) for d, v in price.items()},
            "rs": {d: round(v, 2) for d, v in rs.items()},
            "turnover_a": ({d: round(v / 1e8, 2) for d, v in to_a.items()} if to_a is not None else None),
            "turnover_hk": ({d: round(v / 1e8, 2) for d, v in to_hk.items()} if to_hk is not None else None),
            "share": ({d: round(v, 3) for d, v in share.items()} if share is not None else None),
        }
    (OUT / "chart_baskets.json").write_text(
        json.dumps(baskets_out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("chart_baskets ok:", len(baskets_out))

    # ---------- 3. 个股：周频归一化 + 月度收益热力 + 底顶标记 ----------
    stocks = {}
    seen = set()
    for bkey, b in uni["baskets"].items():
        for st in b["stocks"]:
            if st["code"] in seen:
                # 合并篮子归属
                stocks[st["code"]]["baskets"].append(bkey)
                continue
            seen.add(st["code"])
            try:
                df = load_csv(st["code"])
            except Exception:
                continue
            close = df["close"].dropna()
            close.index = pd.to_datetime(close.index)
            to_s = df["turnover"].copy()
            to_s.index = pd.to_datetime(to_s.index)
            wk = close.resample("W-FRI").last().dropna()
            norm = wk / wk.iloc[0] * 100
            # 月度收益
            mo = close.resample("ME").last().dropna()
            mo_ret = mo.pct_change() * 100
            first_mo = mo.iloc[0] / close.iloc[0] - 1
            mo_ret.iloc[0] = first_mo * 100
            # 关键标记
            pmin_d, pmin = close.idxmin(), float(close.min())
            pmax_d, pmax = close.idxmax(), float(close.max())
            to_max_d = to_s.idxmax()
            base = close.iloc[0]
            # 自峰值最大回撤（峰值之后）
            after = close[pmax_d:]
            dd = float((after.min() / pmax - 1) * 100) if len(after) else 0.0
            # 相对基准强弱（日频）
            bench = bench_hk if st["code"].startswith("HK") else bench_a
            b2 = bench.copy()
            b2.index = pd.to_datetime(b2.index)
            rs = (close / b2.reindex(close.index).ffill())
            rs = rs / rs.iloc[0] * 100
            stocks[st["code"]] = {
                "name": st["name"], "roles": st["role"],
                "baskets": [bkey],
                "first_date": close.index[0].strftime("%Y-%m-%d"),
                "weekly_norm": {d.strftime("%Y-%m-%d"): round(v, 1) for d, v in norm.items()},
                "monthly_ret": {d.strftime("%Y-%m"): round(v, 1) for d, v in mo_ret.items()},
                "marks": {
                    "价格底": {"date": pmin_d.strftime("%Y-%m-%d"), "value": round(pmin, 2)},
                    "价格顶": {"date": pmax_d.strftime("%Y-%m-%d"), "value": round(pmax, 2)},
                    "成交顶": {"date": to_max_d.strftime("%Y-%m-%d")},
                    "区间涨幅%": round((close.iloc[-1] / base - 1) * 100, 1),
                    "自顶回撤%": round(dd, 1),
                    "相对强弱顶": {"date": rs.idxmax().strftime("%Y-%m-%d")},
                    "相对强弱底": {"date": rs.idxmin().strftime("%Y-%m-%d")},
                },
            }
    (OUT / "chart_stocks.json").write_text(
        json.dumps(stocks, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("chart_stocks ok:", len(stocks))

    # ---------- 4. 叙事卡片微观图表数据（全期日频，共用日期轴；含行业指数） ----------
    ep_db = json.loads((OUT / "episodes.json").read_text(encoding="utf-8"))
    ep_charts = {"dates": all_dates, "episodes": {}}
    ind_map = {}
    for ix in uni.get("industry_indexes", []):
        for eid in ix.get("episodes", []):
            ind_map.setdefault(eid, []).append((
                ix["code"], ix["name"], ix.get("proxy", ""),
                ix.get("chart_role", "行业指数"),
            ))
    for e in ep_db["episodes"]:
        codes = []
        for st in e.get("stocks", []):
            codes.append((st["code"], st["name"], st["role"]))
        for c in e.get("featured_indexes", []):
            nm = next((ix["name"] for ix in uni["indexes"] if ix["code"] == c), c)
            codes.append((c, nm, "指数"))
        for c, nm, proxy, chart_role in ind_map.get(e["id"], []):
            codes.append((c, nm, chart_role))
        seen_c = set()
        series = []
        for code, name, role in codes:
            if code in seen_c:
                continue
            seen_c.add(code)
            try:
                df = load_csv(code)
            except Exception:
                continue
            close_map = df["close"].round(2).to_dict()
            to_map = (df["turnover"] / 1e8).round(2).to_dict()
            series.append({"code": code, "name": name, "role": role,
                           "close": [close_map.get(d) for d in all_dates],
                           "turnover": [to_map.get(d) for d in all_dates]})
        ep_charts["episodes"][e["id"]] = {"series": series}
    (OUT / "chart_episodes.json").write_text(
        json.dumps(ep_charts, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("chart_episodes ok:", len(ep_charts["episodes"]))


if __name__ == "__main__":
    main()
