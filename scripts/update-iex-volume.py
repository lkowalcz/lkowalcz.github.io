#!/usr/bin/env python3
"""Regenerate data/iex-volume.json from iextrading.com/stats data.

The stats page's volume chart is monthly average daily matched volume (ADV).
Values for Jan 2014 - Jul 2021 are hardcoded in the page's own JS (copied
below); later months come from POST /api/stats/monthly, one call per month.
Run from the repo root (no dependencies beyond the standard library).
"""

import json
import time
import urllib.request
from datetime import date
from pathlib import Path

API = "https://iextrading.com/api/stats/monthly"
OUT = Path(__file__).resolve().parent.parent / "data" / "iex-volume.json"

# Jan 2014 - Jul 2021, from `monthlyVolumeOld` in iextrading.com/build/site/stats.js
HISTORICAL = [
    9089309, 14694304, 18891254, 28964393, 31271546, 37032170, 43142552,
    42044024, 48957889, 59728334, 55805516, 58280324, 66681710, 63878219,
    61765355, 71912332, 68099042, 74985531, 94724940, 113706582, 106667653,
    117064016, 110939330, 108593900, 158642007, 156740917, 126234325,
    112610844, 112247378.5, 122054371.5, 104516019, 86908524.5, 107036654.4,
    115130921.3, 138875743, 115819609.7, 128190194.8, 143199060.7,
    140963064.7, 137650908.9, 149167688.7, 156220705.2, 133170211.9,
    131343282.1, 141416654.2, 146047833.9, 169621282.5, 148034015.4,
    165265854.5, 194214479, 167038904, 155442242.7, 163260595.5, 173608673.2,
    147992555.8, 153758722, 174503275.2, 216559575.5, 220726731.7,
    227641173.7, 206970642.5, 193281327.6, 195910532.1, 180302563, 200232358,
    195754126, 175552155, 215779825, 201408476, 175004362, 190928049,
    174133306, 194354918, 237859901, 423536386, 256435406, 230341496,
    244350540, 180080056, 164638922, 180174171, 249736288, 285502579,
    221807090, 296064938, 308624051, 315666168, 228162725, 257915277,
    251899051, 218425680,
]


def month_range(start_year, start_month, end_year, end_month):
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def fetch_adv(year, month):
    body = json.dumps({"month": f"{month:02d}", "year": str(year)}).encode()
    req = urllib.request.Request(
        API, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    stats = (data.get("stats") or [{}])[0]
    adv = stats.get("SingleADV")
    return float(adv) if adv else None


def main():
    today = date.today()
    # Fetch through the last complete month, same as the stats page itself.
    end_y, end_m = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)

    adv = [round(v) for v in HISTORICAL]
    for y, m in month_range(2021, 8, end_y, end_m):
        value = fetch_adv(y, m)
        if value is None:
            break  # data not published yet; stop at the last available month
        adv.append(round(value))
        time.sleep(0.25)

    OUT.write_text(
        json.dumps(
            {
                "source": "https://iextrading.com/stats/",
                "series": "IEX average daily matched volume by month, in shares",
                "start": "2014-01",
                "updated": today.isoformat(),
                "adv": adv,
            },
            indent=1,
        )
        + "\n"
    )
    print(f"wrote {OUT.relative_to(Path.cwd())} with {len(adv)} months")


if __name__ == "__main__":
    main()
