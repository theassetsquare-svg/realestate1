#!/usr/bin/env python3
"""청약홈 real-data adapter (data.go.kr · 한국부동산원_청약홈 분양정보).

HONEST CONTRACT
  • If a data.go.kr service key is configured (env DATA_GO_KR_KEY, or
    ~/.gsc/datago.key), this fetches the official 분양정보 feed, maps it to the
    SSOT schema, and MERGES it into tools/data/listings.json — new venues are
    added, real 청약 dates drive the daily auto-close.
  • If NO key is configured, it fabricates NOTHING. It prints a clear notice and
    exits 0, leaving the SSOT exactly as-is. The site never claims a live feed
    it does not have (the false "실시간 청약홈 연동" copy was removed at the root).

KEY SETUP (one-time, by the owner — no new Google key, this is a *separate*
free public-data key):
  1. data.go.kr → "한국부동산원_청약홈 분양정보 조회 서비스" 활용신청 (무료)
  2. repo Settings → Secrets → Actions → new secret  DATA_GO_KR_KEY = <발급키>
  3. add it to the daily workflow env (see tools/workflow_drop/daily-update.yml)

NOTE: the field mapping below follows the documented odcloud schema. It is
written to be correct-by-construction but has NOT been run against the live API
here (no key available in this environment) — the no-key path is what executes.
"""
from __future__ import annotations
import os, json, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SSOT = os.path.join(ROOT, "tools", "data", "listings.json")

# odcloud 청약홈 분양정보 endpoints (APT + 오피스텔/도시형/민간임대/생활숙박)
ENDPOINTS = {
    "apartment": "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail",
    "officetel": "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getUrbtyOfctlLttotPblancDetail",
}


def _key():
    k = os.environ.get("DATA_GO_KR_KEY")
    if k:
        return k.strip()
    p = os.path.expanduser("~/.gsc/datago.key")
    if os.path.exists(p):
        return open(p, encoding="utf-8").read().strip()
    return None


def _slugify(name: str, no: str) -> str:
    base = "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")
    return f"{base or 'listing'}-{no}"[:60]


def _map_apt(row: dict) -> dict:
    """Map one odcloud APT record → SSOT record (real fields only)."""
    name = row.get("HOUSE_NM") or ""
    no = str(row.get("PBLANC_NO") or row.get("HOUSE_MANAGE_NO") or "")
    astart = (row.get("SUBSCRPT_RCEPT_BGNDE") or "")[:10] or None
    aend = (row.get("SUBSCRPT_RCEPT_ENDDE") or row.get("GNRL_RNK1_CRSPAREA_RCEPT_ENDDE") or "")[:10] or None
    # normalise YYYYMMDD → YYYY-MM-DD if needed
    def iso(d):
        if d and len(d) == 8 and d.isdigit():
            return f"{d[:4]}-{d[4:6]}-{d[6:]}"
        return d
    return {
        "slug": _slugify(name, no),
        "name": name,
        "category": "apartment",
        "region": row.get("HSSPLY_ADRES") or "",
        "developer": row.get("CNSTRCT_ENTRPS_NM") or row.get("BSNS_MBY_NM") or "",
        "total_units": (f"{row.get('TOT_SUPLY_HSHLDCO')}세대"
                        if row.get("TOT_SUPLY_HSHLDCO") else ""),
        "size_range": "",
        "price_range": "모집공고문 기준",
        "schedule": f"청약 {iso(astart) or '?'} ~ {iso(aend) or '?'}",
        "movein": row.get("MVN_PREARNGE_YM") or "",
        "apply_start": iso(astart),
        "apply_end": iso(aend),
        "highlights": [],
        "source": "applyhome-data.go.kr",
        "source_url": row.get("PBLANC_URL") or "",
    }


def fetch_all(key: str, today: dt.date) -> list:
    import urllib.parse, urllib.request
    out = []
    for cat, base in ENDPOINTS.items():
        if cat != "apartment":
            continue  # officetel schema differs; enable once verified against live API
        params = urllib.parse.urlencode({
            "page": 1, "perPage": 100, "serviceKey": key,
            # only currently-open or upcoming subscriptions
            "cond[RCRIT_PBLANC_DE::GTE]": (today - dt.timedelta(days=30)).isoformat(),
        })
        req = urllib.request.Request(f"{base}?{params}", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        for row in data.get("data", []):
            try:
                out.append(_map_apt(row))
            except Exception as e:
                print(f"  skip row ({e})")
    return out


def merge_into_ssot(fetched: list, today: dt.date):
    import importlib.util
    spec = importlib.util.spec_from_file_location("ssot", os.path.join(ROOT, "tools", "ssot.py"))
    ssot = importlib.util.module_from_spec(spec); spec.loader.exec_module(ssot)
    payload = json.load(open(SSOT, encoding="utf-8"))
    by_slug = {r["slug"]: r for r in payload["listings"]}
    added = 0
    for rec in fetched:
        rec["status"] = ssot.compute_status(rec.get("apply_start"), rec.get("apply_end"),
                                            rec.get("schedule"), today)
        if rec["slug"] not in by_slug:
            added += 1
        by_slug[rec["slug"]] = {**by_slug.get(rec["slug"], {}), **rec}
    payload["listings"] = sorted(by_slug.values(), key=lambda r: (r.get("category") or "z", r["slug"]))
    payload["count"] = len(payload["listings"])
    payload["chungyang_fetched"] = today.isoformat()
    json.dump(payload, open(SSOT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"  청약홈 merge: +{added} new, {len(fetched)} fetched, total {payload['count']}")


def main():
    today = dt.date.fromisoformat(os.environ.get("GSC_TODAY") or "2026-06-07")
    key = _key()
    if not key:
        print("ℹ 청약홈 키(DATA_GO_KR_KEY) 미설정 — 실데이터 fetch 건너뜀.")
        print("  SSOT는 변경하지 않으며, 데이터를 창작하지 않습니다(정직).")
        print("  키 1회 등록 방법은 tools/chungyang_fetch.py 상단 주석 참조.")
        return 0
    try:
        fetched = fetch_all(key, today)
        merge_into_ssot(fetched, today)
    except Exception as e:
        print(f"⚠ 청약홈 fetch 실패({e}) — SSOT 유지(창작 없음).")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
