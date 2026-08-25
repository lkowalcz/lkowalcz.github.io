#!/usr/bin/env python3
"""Regenerate data/iex-notional.json from Cboe's market share pages.

IEX publishes volume in shares only, so dollar (notional) value comes from
Cboe's per-day market share pages, which embed a month-to-date average for
every US venue. The page for day D reports MTD through the previous trading
day, and non-trading days roll forward - so the page for the 1st of month
M+1 always carries month M's full-month average daily notional. Verified
against IEX's own published share ADV: the Volume side of the same blob
matches it exactly. IEX appears in Cboe's data from Aug 2020 (partial
month), so the series starts Sep 2020.
Run from the repo root (no dependencies beyond the standard library).
"""

import json
import re
import time
import urllib.request
from datetime import date
from pathlib import Path

PAGE = "https://www.cboe.com/us/equities/market_share/market/all/{day}/"
OUT = Path(__file__).resolve().parent.parent / "data" / "iex-notional.json"
START_YEAR, START_MONTH = 2020, 9


def month_range(start_year, start_month, end_year, end_month):
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def fetch_month_notional(year, month):
    """Full-month IEX average daily notional, read from the 1st of the next month."""
    ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
    req = urllib.request.Request(
        PAGE.format(day=f"{ny}-{nm:02d}-01"),
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode()
    blob = re.search(r"var\s+mtd_data\s*=\s*(\{.*?\});\n", html, re.S)
    if not blob:
        return None
    rows = json.loads(blob.group(1))["Notional Value"]["integrated"]["y"]["data"]
    iex = [r for r in rows if "Investors" in r["mktdesc"]]
    return float(iex[0]["avg_value"]) if iex else None


def main():
    today = date.today()
    # Through the last complete month, matching the chart's monthly cadence.
    end_y, end_m = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)

    values = []
    for y, m in month_range(START_YEAR, START_MONTH, end_y, end_m):
        value = fetch_month_notional(y, m)
        if value is None:
            # Fail loudly rather than commit a silently truncated series.
            raise RuntimeError(f"no IEX notional data for {y}-{m:02d}")
        values.append(round(value))
        time.sleep(0.25)

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "source": "https://www.cboe.com/us/equities/market_share/",
                "series": "IEX average daily traded dollar value by month, in USD",
                "start": f"{START_YEAR}-{START_MONTH:02d}",
                "updated": today.isoformat(),
                "values": values,
            },
            indent=1,
        )
        + "\n"
    )
    print(f"wrote {OUT.relative_to(Path.cwd())} with {len(values)} months")


if __name__ == "__main__":
    main()
