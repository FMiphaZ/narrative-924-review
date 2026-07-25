#!/usr/bin/env python3
"""从 Futu OpenD 拉取指数与叙事篮子标的的日K数据（只读行情，不涉账户/交易）。

用法:
  python fetch_klines.py --start 2023-11-01 --end 2026-07-24
输出:
  narrative-924-review/data/index/<CODE>.csv
  narrative-924-review/data/baskets/<CODE>.csv
  narrative-924-review/data/manifest.json
"""
import argparse
import json
import signal
import time
from pathlib import Path

import pandas as pd
from futu import OpenQuoteContext, RET_OK

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


class FetchTimeout(Exception):
    pass


def _alarm_handler(signum, frame):
    raise FetchTimeout("single request timed out")


signal.signal(signal.SIGALRM, _alarm_handler)


def load_universe():
    with open(DATA / "universe.json", encoding="utf-8") as f:
        return json.load(f)


def fetch_history(ctx, code, start, end, max_retry=3):
    """分页拉取全部日K，返回 DataFrame。"""
    rows = []
    req_key = None
    for attempt in range(max_retry):
        try:
            while True:
                signal.alarm(45)  # 单次请求45秒看门狗
                try:
                    if req_key is None:
                        ret, data, page_key = ctx.request_history_kline(
                            code, start=start, end=end, max_count=1000)
                    else:
                        ret, data, page_key = ctx.request_history_kline(
                            code, start=start, end=end, max_count=1000,
                            extended_time=False, page_req_key=req_key)
                finally:
                    signal.alarm(0)
                if ret != RET_OK:
                    raise RuntimeError(f"{code}: {data}")
                rows.append(data)
                if page_key is None:
                    break
                req_key = page_key
                time.sleep(1.0)
            if rows:
                df = pd.concat(rows, ignore_index=True)
                df = df.drop_duplicates(subset=["time_key"]).sort_values("time_key")
                return df
            return pd.DataFrame()
        except Exception as e:
            if attempt == max_retry - 1:
                raise
            wait = 10 * (attempt + 1)
            print(f"  retry {code} after error: {e} (wait {wait}s)", flush=True)
            time.sleep(wait)
    return pd.DataFrame()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2023-11-01")
    ap.add_argument("--end", default="2026-07-24")
    args = ap.parse_args()

    uni = load_universe()
    jobs = []  # (code, name, subdir, role_info)
    for idx in uni["indexes"]:
        jobs.append((idx["code"], idx["name"], "index", idx["role"]))
    for idx in uni.get("industry_indexes", []):
        jobs.append((idx["code"], idx["name"], "index",
                     "行业指数|" + idx.get("proxy", "")))
    for bkey, basket in uni["baskets"].items():
        for st in basket["stocks"]:
            jobs.append((st["code"], st["name"], "baskets",
                         f'{bkey}|{st["role"]}'))

    # 去重（同一标的只拉一次；角色信息合并）
    seen = {}
    for code, name, subdir, role in jobs:
        if code not in seen:
            seen[code] = {"code": code, "name": name, "subdir": subdir,
                          "roles": [role]}
        else:
            seen[code]["roles"].append(role)
            if subdir == "index":
                seen[code]["subdir"] = "index"

    manifest = {"fetched": [], "failed": [], "start": args.start,
                "end": args.end, "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S")}

    ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
    try:
        for i, (code, info) in enumerate(seen.items(), 1):
            subdir = info["subdir"]
            out = DATA / subdir / f"{code.replace('.', '_')}.csv"
            if out.exists() and out.stat().st_size > 500:
                print(f"[{i}/{len(seen)}] skip {code} (cached)", flush=True)
                manifest["fetched"].append({**info, "rows": "cached"})
                continue
            try:
                df = fetch_history(ctx, code, args.start, args.end)
                cols = [c for c in ["time_key", "open", "high", "low", "close",
                                    "volume", "turnover", "turnover_rate",
                                    "change_rate"] if c in df.columns]
                df[cols].to_csv(out, index=False)
                print(f"[{i}/{len(seen)}] ok {code} {info['name']} rows={len(df)}",
                      flush=True)
                manifest["fetched"].append({**info, "rows": len(df)})
            except Exception as e:
                print(f"[{i}/{len(seen)}] FAIL {code}: {e}", flush=True)
                manifest["failed"].append({**info, "error": str(e)})
                # 连接可能已损坏，重建一次，避免传染后续标的
                try:
                    ctx.close()
                except Exception:
                    pass
                time.sleep(3)
                ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
            time.sleep(2.2)  # 控制历史K线频限
    finally:
        ctx.close()

    with open(DATA / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"done. fetched={len(manifest['fetched'])} failed={len(manifest['failed'])}")


if __name__ == "__main__":
    main()
