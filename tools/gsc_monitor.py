#!/usr/bin/env python3
"""GSC monitor — pulls Search Console data and writes an actionable report.

What it does, top-to-bottom:
  1. Pulls 28d query+page data from GSC.
  2. Detects cannibalization (>=2 distinct pages ranking for the same query).
  3. Flags low-CTR opportunities (high impressions, position<=10, ctr<3%).
  4. Lists pages with zero impressions (likely not indexed / no traffic).
  5. Writes tools/audit_reports/gsc_report_<date>.md and a JSON sibling.
  6. If issues exist, emits a stable subject line on stdout for downstream
     mailers to pick up.

Exit code 0 = clean, 1 = action items found.

Usage: python3 tools/gsc_monitor.py
"""
from __future__ import annotations
import json, os, sys, datetime as dt, glob, urllib.request
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gsc_client import GSC  # noqa: E402

SITE_HOST = "https://realestate1-3xh.pages.dev"
TODAY = dt.date.fromisoformat(os.environ.get("GSC_TODAY") or "2026-06-01")
START = (TODAY - dt.timedelta(days=28)).isoformat()
END = TODAY.isoformat()
REPORT_DIR = os.path.join(ROOT, "tools", "audit_reports")
os.makedirs(REPORT_DIR, exist_ok=True)

# Thresholds — tuned for a young site (few impressions)
LOW_CTR_MIN_IMPR = 20
LOW_CTR_THRESHOLD = 0.03
CANNIBAL_MIN_IMPR = 5  # ignore single-digit cannibalization noise


def local_pages():
    pages = []
    for p in glob.glob(os.path.join(ROOT, "*.html")):
        if os.path.basename(p) == "404.html":
            continue
        pages.append(p)
    pages += glob.glob(os.path.join(ROOT, "property", "*.html"))
    urls = []
    for p in sorted(pages):
        rel = os.path.relpath(p, ROOT)
        if rel == "index.html":
            urls.append(f"{SITE_HOST}/")
        else:
            urls.append(f"{SITE_HOST}/{rel}")
    return urls


def main():
    g = GSC()
    qp = g.query(start=START, end=END,
                 dimensions=["query", "page"], rowLimit=5000).get("rows", [])
    pg = g.query(start=START, end=END,
                 dimensions=["page"], rowLimit=5000).get("rows", [])
    qonly = g.query(start=START, end=END,
                    dimensions=["query"], rowLimit=5000).get("rows", [])

    # ---- aggregate ----
    by_query = defaultdict(list)
    for r in qp:
        q, p = r["keys"]
        by_query[q].append({
            "page": p, "clicks": r["clicks"], "impr": r["impressions"],
            "ctr": r["ctr"], "pos": r["position"],
        })

    cannibal = []
    for q, hits in by_query.items():
        if len(hits) >= 2 and sum(h["impr"] for h in hits) >= CANNIBAL_MIN_IMPR:
            hits_sorted = sorted(hits, key=lambda h: -h["impr"])
            cannibal.append({"query": q, "hits": hits_sorted})

    low_ctr = [r for r in pg
               if r["impressions"] >= LOW_CTR_MIN_IMPR
               and r["position"] <= 10
               and r["ctr"] < LOW_CTR_THRESHOLD]

    indexed_pages = {r["keys"][0].rstrip("/") for r in pg}
    all_pages = local_pages()
    no_impr = [u for u in all_pages if u.rstrip("/") not in indexed_pages]

    # Top winning + losing queries
    qs = sorted(qonly, key=lambda r: -r["impressions"])

    # ---- write JSON + Markdown ----
    stamp = TODAY.isoformat()
    json_path = os.path.join(REPORT_DIR, f"gsc_report_{stamp}.json")
    md_path = os.path.join(REPORT_DIR, f"gsc_report_{stamp}.md")

    summary = {
        "window": {"start": START, "end": END},
        "totals": {
            "queries": len(qonly),
            "ranking_pages": len(pg),
            "impressions": sum(r["impressions"] for r in pg),
            "clicks": sum(r["clicks"] for r in pg),
        },
        "cannibalization": cannibal,
        "low_ctr_opportunities": low_ctr,
        "no_impression_pages": no_impr,
        "top_queries": qs[:25],
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    lines = []
    lines.append(f"# GSC 리포트 — {stamp}")
    lines.append(f"기간: {START} → {END}  ·  site: {SITE_HOST}")
    lines.append("")
    lines.append("## 합계")
    t = summary["totals"]
    lines.append(f"- 쿼리 수: **{t['queries']}**  ·  노출 페이지: **{t['ranking_pages']}**")
    lines.append(f"- 노출(impr): **{t['impressions']}**  ·  클릭: **{t['clicks']}**")
    lines.append("")
    lines.append("## 카니발리제이션 (동일 쿼리에 2+ 페이지 노출)")
    if not cannibal:
        lines.append("- 없음 ✅")
    else:
        for c in cannibal[:20]:
            lines.append(f"- **{c['query']}**")
            for h in c["hits"]:
                lines.append(f"  - {h['page']} · impr {h['impr']} · pos {h['pos']:.1f}")
    lines.append("")
    lines.append("## CTR 개선 후보 (impr≥20, 1~10위, CTR<3%)")
    if not low_ctr:
        lines.append("- 없음 ✅")
    else:
        for r in low_ctr[:30]:
            lines.append(f"- {r['keys'][0]} · impr {r['impressions']} · pos {r['position']:.1f} · CTR {r['ctr']*100:.1f}%")
    lines.append("")
    lines.append(f"## 노출 0회 페이지 ({len(no_impr)}개)")
    if not no_impr:
        lines.append("- 없음 ✅")
    else:
        for u in no_impr[:50]:
            lines.append(f"- {u}")
        if len(no_impr) > 50:
            lines.append(f"- … 외 {len(no_impr)-50}개")
    lines.append("")
    lines.append("## 상위 쿼리 (impr 기준 25개)")
    for r in qs[:25]:
        lines.append(f"- {r['keys'][0]} · impr {r['impressions']} · pos {r['position']:.1f} · clicks {r['clicks']}")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # GSC findings are advisory. Cannibalization is the only "real" failure;
    # low CTR / no-impression pages on a young site are informational.
    fail = bool(cannibal)
    print(f"GSC report → {md_path}")
    print(f"cannibal={len(cannibal)} low_ctr={len(low_ctr)} no_impr={len(no_impr)}")
    if fail or low_ctr or no_impr:
        print(f"::ISSUE::[GSC] {stamp} cannibal={len(cannibal)} low_ctr={len(low_ctr)} no_impr={len(no_impr)}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
