#!/usr/bin/env python3
"""Refresh monthly IEX equities dollar ADV and options contract ADV from Cboe.

Completed months use the MTD average embedded in the first of the next month's
market-share page (which excludes that day's trading). Preserve saved completed
months; keep the provisional current month in a separate `mtd` object so it is
never mistaken for a final average at rollover.

Current-month ADV is calculated from Cboe's dated daily CSV rows, excluding today
in New York. This includes the latest completed session without depending on
the market-share page's cached MTD tab. Equities supports a CSV date range;
options offers the last 30 trading days, enough to cover any current month.
Weekends and holidays do not count toward ADV. Options launched October 2, 2026;
Cboe's October monthly average includes the pre-launch trading day as zero.

Run from the repo root (standard library only).
"""

import csv
import io
import json
import math
import re
import time
import urllib.request
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MARKETS = {
    "equities": {
        "file": "iex-notional.json",
        "source": "https://www.cboe.com/us/equities/market_share/",
        "series": "IEX equities average daily traded dollar value by month, in USD",
        "start": "2016-09",
        "metric": "Notional Value",
        "venue": "investorsexchangev",
        "date_column": "Date",
        "venue_column": "Trading Market Centre",
        "value_column": "Market",
    },
    "options": {
        "file": "iex-options.json",
        "source": "https://www.cboe.com/us/options/market_statistics/market/",
        "series": "IEX options average daily volume by month, in contracts",
        "start": "2026-10",
        "metric": "Volume",
        "venue": "iexoptionsv",
        "date_column": "Day",
        "venue_column": "Market Participant",
        "value_column": "Total Option Contracts",
    },
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8-sig")


def checked_value(value):
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"invalid volume: {value}")
    return value


def month_range(start_year, start_month, end_year, end_month):
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def fetch_month_adv(market, year, month):
    """Full-month ADV, read from the first of the next month."""
    config = MARKETS[market]
    ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
    day = f"{ny}-{nm:02d}-01"
    html = fetch(
        f"https://www.cboe.com/us/{market}/market_share/market/all/{day}/"
    )
    selected = re.search(r"var\s+cal_dt\s*=\s*['\"]([^'\"]+)['\"]", html)
    blob = re.search(r"var\s+mtd_data\s*=\s*(\{.*?\});", html, re.S)
    if not blob or not selected or selected[1] != day:
        raise RuntimeError(f"unexpected Cboe {market} page for {day}")
    rows = json.loads(blob[1])[config["metric"]]["integrated"]["y"]["data"]
    iex = [r for r in rows if r["mktname"] == config["venue"]]
    if len(iex) != 1:
        raise RuntimeError(f"no unique IEX {market} average for {year}-{month:02d}")
    return checked_value(iex[0]["avg_value"])


def parse_mtd(csv_text, market, today):
    """Average dated, completed sessions only; never count missing IEX rows as zero."""
    config = MARKETS[market]
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
    required = {config[key] for key in ("date_column", "venue_column", "value_column")}
    if not required.issubset(reader.fieldnames or []):
        raise RuntimeError(f"unexpected Cboe {market} CSV columns")
    first = today.replace(day=1)
    trading_days, values = set(), {}
    for row in reader:
        day = date.fromisoformat(row[config["date_column"]])
        if not first <= day < today:
            continue
        trading_days.add(day)
        if row[config["venue_column"]] not in ("Investors Exchange (V)", "IEX Options (V)"):
            continue
        if day in values:
            raise RuntimeError(f"duplicate IEX {market} row for {day}")
        values[day] = checked_value(row[config["value_column"]])
    if not trading_days:
        return None  # The new month has no published completed sessions yet.
    # The only legitimate absent venue row is before the options launch.
    missing = trading_days - values.keys()
    if market == "options":
        missing = {day for day in missing if day >= date(2026, 10, 2)}
    if missing:
        raise RuntimeError(f"missing IEX {market} rows: {sorted(missing)}")
    return {
        "month": first.strftime("%Y-%m"),
        "through": max(trading_days).isoformat(),
        "trading_days": len(trading_days),
        "value": round(sum(values.values()) / len(trading_days)),
    }


def fetch_mtd(market, today):
    base = f"https://www.cboe.com/us/{market}/market_share/market/csv/"
    params = {"bias": MARKETS[market]["metric"], "auctions": "y"}
    if market == "options":
        url = base + "history/"
        params["s"] = today.isoformat()  # History excludes the requested day.
    else:
        url = base
        params.update(s=today.replace(day=1).isoformat(), e=today.isoformat())
    return parse_mtd(fetch(url + "?" + urlencode(params)), market, today)


def update_series(market, data, today):
    # Copy the values so failed fetches leave the original snapshot untouched.
    data = {**data, "values": list(data["values"])}
    values = data["values"]
    start_y, start_m = map(int, data["start"].split("-"))
    next_y, next_m = divmod(start_y * 12 + start_m - 1 + len(values), 12)
    next_m += 1
    end_y, end_m = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
    for y, m in month_range(next_y, next_m, end_y, end_m):
        values.append(round(fetch_month_adv(market, y, m)))
        time.sleep(0.25)

    mtd = fetch_mtd(market, today)
    previous = data.get("mtd")
    if previous and previous["month"] == today.strftime("%Y-%m"):
        if mtd is None or mtd["through"] < previous["through"]:
            raise RuntimeError(f"Cboe {market} MTD regressed; keeping the saved snapshot")
    data["mtd"] = mtd
    return data


def main():
    today = datetime.now(ZoneInfo("America/New_York")).date()
    pending = []
    for market, config in MARKETS.items():
        path = DATA_DIR / config["file"]
        if path.exists():
            old = json.loads(path.read_text())
        else:
            old = {key: config[key] for key in ("source", "series", "start")}
            old["values"] = []
        new = update_series(market, old, today)
        if new != old:
            new["updated"] = today.isoformat()
            pending.append((path, new))

    # Fetch and validate both markets before writing either snapshot.
    for path, data in pending:
        temp = path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(data, indent=1) + "\n")
        temp.replace(path)
        print(f"wrote {path.name}: {len(data['values'])} completed months; MTD {data['mtd']}")
    if not pending:
        print("IEX equities and options data is already up to date")


if __name__ == "__main__":
    main()
