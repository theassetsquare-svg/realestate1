#!/usr/bin/env python3
"""SSOT builder — tools/data/listings.json (single source of truth).

Builds a structured, real-data-only record per venue from:
  1. property/*.html  info-tables (the data currently live on the site), and
  2. tools/data/new_listings_2026-06.json (structured June feed).

NO fabrication. Fields that cannot be parsed are left empty / null and the
status falls back to a neutral, honest label. Subscription dates are parsed
from the 청약일정 cell so that `status` can be recomputed every day and expired
subscriptions auto-close (fixes the "4월 동결 / 청약중" staleness at the root).

A daily fetch adapter (chungyang_fetch.py) may overwrite/extend this file with
official 청약홈 (data.go.kr) data when a service key is configured; absent a
key it leaves the SSOT untouched (no invented data).

Run:  python3 tools/ssot.py            # rebuild listings.json from pages
Env:  GSC_TODAY=YYYY-MM-DD             # "today" for status (default 2026-06-07)
"""
from __future__ import annotations
import os, re, json, glob, html as _html, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROP = os.path.join(ROOT, "property")
NEW = os.path.join(ROOT, "tools", "data", "new_listings_2026-06.json")
OUT = os.path.join(ROOT, "tools", "data", "listings.json")

CATS = ("apartment", "officetel", "store", "knowledge-center", "land", "industrial")

CAT_LABEL = {
    "apartment": "아파트분양", "officetel": "오피스텔분양", "store": "상가분양",
    "knowledge-center": "지식산업센터분양", "land": "토지분양", "industrial": "산업단지분양",
}


def today() -> dt.date:
    return dt.date.fromisoformat(os.environ.get("GSC_TODAY") or "2026-06-07")


def _text(s: str) -> str:
    return _html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def _category_of(h: str) -> str | None:
    m = re.search(r'breadcrumb.*?<a href="/([a-z-]+)(?:\.html)?"', h, re.S)
    if m and m.group(1) in CAT_LABEL:
        return m.group(1)
    return None


def _info_table(h: str) -> dict:
    """Map every <th>k</th><td>v</td> in the first info-table to {k: v}."""
    m = re.search(r'<table class="info-table">(.*?)</table>', h, re.S)
    rows = {}
    if not m:
        return rows
    for th, td in re.findall(r"<th>(.*?)</th>\s*<td>(.*?)</td>", m.group(1), re.S):
        rows[_text(th)] = _text(td)
    return rows


_DATE_FULL = re.compile(r"(20\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})")
_DATE_MD = re.compile(r"(?<!\d)(\d{1,2})[.\-/](\d{1,2})(?!\d)")


def parse_apply_dates(cell: str, default_year: int = 2026):
    """Return (start, end) ISO dates parsed from a 청약일정 string, or (None,None).

    Handles '2026.04.10(특별) ~ 04.15(2순위)' and '2026.04.10 ~ 2026.04.15'.
    Only returns dates we can actually read — never guesses a schedule."""
    if not cell:
        return None, None
    dates: list[dt.date] = []
    year = default_year
    # full dates first; they also set the working year for bare M.D tokens
    spans = []
    for m in _DATE_FULL.finditer(cell):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            dates.append(dt.date(y, mo, d)); year = y
        except ValueError:
            pass
        spans.append(m.span())
    # bare M.D tokens not already covered by a full-date match
    for m in _DATE_MD.finditer(cell):
        if any(s <= m.start() < e for s, e in spans):
            continue
        mo, d = int(m.group(1)), int(m.group(2))
        try:
            dates.append(dt.date(year, mo, d))
        except ValueError:
            pass
    if not dates:
        return None, None
    return min(dates).isoformat(), max(dates).isoformat()


_YM = re.compile(r"(20\d{2})\s*년\s*(\d{1,2})(?:\s*~\s*(\d{1,2}))?\s*월")


def compute_status(apply_start, apply_end, schedule_text, t: dt.date) -> str:
    """Honest status from real dates first, schedule text second.

    Precise dates win. Otherwise we read an explicit 'YYYY년 M월 분양' window and
    compare it to today; failing that we fall back to plain-text markers. We
    never invent a status — unknown schedules stay '분양 정보 확인'."""
    end = dt.date.fromisoformat(apply_end) if apply_end else None
    start = dt.date.fromisoformat(apply_start) if apply_start else None
    if end:
        if end < t:
            return "청약 마감"
        if start and start > t:
            return "청약 예정"
        return "청약 접수 중"
    txt = schedule_text or ""
    # explicit launch month/window, e.g. "2026년 6월 분양" / "2026년 5~6월 분양"
    m = _YM.search(txt)
    if m and "분양" in txt:
        y = int(m.group(1)); m1 = int(m.group(2)); m2 = int(m.group(3) or m.group(2))
        cur = (t.year, t.month)
        if (y, m2) < cur:
            return "분양 중"            # window already opened; closed status unknown → still active info
        if (y, m1) > cur:
            return "분양 예정"
        return "분양 중"
    if re.search(r"분양\s*(개시|진행|중)|청약\s*진행|선착순|접수\s*중", txt):
        return "분양 중"
    if re.search(r"예정|미정|하반기|상반기|공고|착수|준공|개교", txt):
        return "분양 예정"
    return "분양 정보 확인"


def from_pages() -> dict:
    """Extract a record per existing property page (real, currently-live data)."""
    t = today()
    out = {}
    for f in sorted(glob.glob(os.path.join(PROP, "*.html"))):
        slug = os.path.basename(f)[:-5]
        h = open(f, encoding="utf-8").read()
        cat = _category_of(h)
        h1 = _text((re.search(r"<h1>(.*?)</h1>", h, re.S) or re.match("", "")).group(1)) if re.search(r"<h1>(.*?)</h1>", h, re.S) else ""
        rows = _info_table(h)
        # prefer the H1 (clean, matches <title>) over the verbose info-table 현장명
        name = h1 or rows.get("현장명") or slug
        region = rows.get("위치") or ""
        dev = rows.get("시공사") or rows.get("시공·시행") or rows.get("시공") or ""
        units = rows.get("세대수") or rows.get("규모") or ""
        sizes = rows.get("전용면적") or rows.get("평형/면적") or rows.get("평형·면적") or ""
        price = rows.get("분양가") or ""
        sched = rows.get("청약일정") or rows.get("일정") or ""
        movein = rows.get("입주예정") or rows.get("입주") or ""
        astart, aend = parse_apply_dates(sched)
        out[slug] = {
            "slug": slug,
            "name": name,
            "category": cat,
            "region": region,
            "developer": dev,
            "total_units": units,
            "size_range": sizes,
            "price_range": price,
            "schedule": sched,
            "movein": movein,
            "apply_start": astart,
            "apply_end": aend,
            "status": compute_status(astart, aend, sched, t),
            "highlights": [],
            "source": "site-info-table",
            "template": 'class="highlight-list"' in h and "분양 정보·분석" in h,
        }
    return out


def merge_new(records: dict) -> dict:
    """Layer structured June feed fields (highlights, clean schedule) on top."""
    if not os.path.exists(NEW):
        return records
    t = today()
    for e in json.load(open(NEW, encoding="utf-8")):
        slug = e["slug"]
        r = records.get(slug, {"slug": slug, "source": "new_listings_2026-06"})
        r.setdefault("apply_start", None)
        r.setdefault("apply_end", None)
        r["name"] = r.get("name") or e.get("name_ko")
        r["category"] = r.get("category") or e.get("category")
        for k_src, k_dst in [("region", "region"), ("developer", "developer"),
                             ("total_units", "total_units"), ("size_range", "size_range"),
                             ("price_range", "price_range"), ("schedule", "schedule")]:
            if not r.get(k_dst) and e.get(k_src):
                r[k_dst] = e[k_src]
        if e.get("highlights"):
            r["highlights"] = e["highlights"]
        r["status"] = compute_status(r.get("apply_start"), r.get("apply_end"), r.get("schedule"), t)
        records[slug] = r
    return records


def build() -> list:
    recs = merge_new(from_pages())
    listings = sorted(recs.values(), key=lambda r: (r.get("category") or "zzz", r["slug"]))
    return listings


def main():
    listings = build()
    payload = {
        "generated": today().isoformat(),
        "today": today().isoformat(),
        "count": len(listings),
        "source_note": "real data extracted from live pages + structured June feed; no estimates/fabrication",
        "listings": listings,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    # honest summary
    from collections import Counter
    by_status = Counter(r["status"] for r in listings)
    by_cat = Counter(r.get("category") for r in listings)
    missing_cat = [r["slug"] for r in listings if not r.get("category")]
    print(f"SSOT written: {OUT}  ({len(listings)} listings, today={today().isoformat()})")
    print("  status:", dict(by_status))
    print("  category:", dict(by_cat))
    if missing_cat:
        print("  ⚠ missing category:", missing_cat)
    print("  with parsed apply_end:", sum(1 for r in listings if r.get("apply_end")))


if __name__ == "__main__":
    main()
