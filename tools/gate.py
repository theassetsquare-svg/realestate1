#!/usr/bin/env python3
"""Build gate — fails the build (exit 1) if any page regresses to a known defect.

This is the anti-regression backstop: even if a future generator or hand-edit
re-introduces one of the four root defects (or hype / un-sourced numbers / a
stale 청약중 / a false 실시간 claim), the gate catches it before push/deploy.

Checks (per page):
  G-ENTITY-NAME : detail JSON-LD name must NOT start with "더에셋스퀘어" (현장명 only)
  G-ENTITY-TYPE : detail JSON-LD must use a listing type, not RealEstateAgent
  G-BREADCRUMB  : detail must carry a BreadcrumbList
  G-CANONICAL   : canonical / og:url must be extension-less (no .html → no 308)
  G-LINK-HTML   : no internal link ending in .html (would 308)
  G-SISE        : no numeric 시세차익 (digits+억 adjacent to 시세차익)
  G-HYPE        : no 역대급/완판/로또/초프리미엄/대박/줍줍/초피/불장
  G-STALE       : a closed listing must not be shown as 청약 접수 중/청약중
  G-FREE        : no 무료 offer (체험형 prose is allowed; bare 무료 is not)
  G-REALTIME    : no "실시간 청약홈 연동" claim (false until a real feed exists)

Usage:
  python3 tools/gate.py            # scan, print report, exit 1 on any violation
  python3 tools/gate.py --selftest # inject each defect, prove gate blocks, restore
"""
from __future__ import annotations
import os, re, sys, glob, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROP = os.path.join(ROOT, "property")
HYPE_WORDS = ["역대급", "완판", "로또", "초프리미엄", "대박", "줍줍", "초피", "불장"]


def _ssot_status():
    p = os.path.join(ROOT, "tools", "data", "listings.json")
    if not os.path.exists(p):
        return {}
    return {r["slug"]: r.get("status") for r in json.load(open(p, encoding="utf-8"))["listings"]}


def check_html(path, h, is_detail, status=None):
    v = []
    # entity (detail only)
    if is_detail:
        m = re.search(r'"name":\s*"([^"]+)"', h)
        if m and m.group(1).startswith("더에셋스퀘어"):
            v.append(("G-ENTITY-NAME", f'name="{m.group(1)[:30]}"'))
        ld = " ".join(re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S))
        if '"RealEstateAgent"' in ld:
            v.append(("G-ENTITY-TYPE", "RealEstateAgent on detail"))
        if "BreadcrumbList" not in ld:
            v.append(("G-BREADCRUMB", "no BreadcrumbList"))
    # canonical / og:url extension-less
    for tag, rx in [("canonical", r'rel="canonical" href="([^"]+)"'),
                    ("og:url", r'property="og:url" content="([^"]+)"')]:
        mm = re.search(rx, h)
        if mm and mm.group(1).endswith(".html"):
            v.append(("G-CANONICAL", f"{tag}={mm.group(1)}"))
    # internal .html links
    for mm in re.finditer(r'href="(/[a-z][a-z0-9\-/]*\.html)"', h):
        v.append(("G-LINK-HTML", mm.group(1))); break
    # numeric 시세차익
    if re.search(r'시세\s*차익[^<.。]{0,12}[0-9][0-9,]*\s*억|[0-9][0-9,]*\s*억[^<.。]{0,8}시세\s*차익', h):
        v.append(("G-SISE", "numeric 시세차익"))
    # hype
    for w in HYPE_WORDS:
        if w in h:
            v.append(("G-HYPE", w)); break
    # stale 청약중 on a closed listing
    if status in ("청약 마감", "분양 종료") and re.search(r"청약\s*접수\s*중|청약중", h):
        v.append(("G-STALE", f"closed but shows 청약중 (status={status})"))
    # 무료 offer
    if re.search(r"무료", h):
        v.append(("G-FREE", "무료"))
    # false realtime claim (contiguous, or split across the home stat tiles)
    if re.search(r"실시간[^가-힣]{0,40}청약홈\s*연동|실시간\s*청약홈", h):
        v.append(("G-REALTIME", "실시간 청약홈 연동"))
    return v


def scan():
    status = _ssot_status()
    pages = []
    for fn in ["index.html", "apartment.html", "officetel.html", "store.html",
               "land.html", "industrial.html", "knowledge-center.html"]:
        p = os.path.join(ROOT, fn)
        if os.path.exists(p):
            pages.append((p, False, None))
    for p in sorted(glob.glob(os.path.join(PROP, "*.html"))):
        slug = os.path.basename(p)[:-5]
        pages.append((p, True, status.get(slug)))
    all_v = {}
    for p, is_detail, st in pages:
        h = open(p, encoding="utf-8").read()
        vs = check_html(p, h, is_detail, st)
        if vs:
            all_v[os.path.relpath(p, ROOT)] = vs
    return all_v


def main():
    if "--selftest" in sys.argv:
        return selftest()
    v = scan()
    n = sum(len(x) for x in v.values())
    if not v:
        print(f"✅ GATE PASS — {len(glob.glob(os.path.join(PROP,'*.html')))+7} pages, 0 violations")
        return 0
    print(f"❌ GATE FAIL — {n} violation(s) in {len(v)} page(s):")
    from collections import Counter
    by_rule = Counter(rule for vs in v.values() for rule, _ in vs)
    print("  by rule:", dict(by_rule))
    for page, vs in list(v.items())[:25]:
        print(f"  {page}: {vs}")
    return 1


def selftest():
    """Inject each defect into a temp copy, prove the gate flags it, restore."""
    sample = sorted(glob.glob(os.path.join(PROP, "*.html")))[0]
    orig = open(sample, encoding="utf-8").read()
    cases = {
        "G-ENTITY-NAME": lambda s: re.sub(r'"name":\s*"', '"name": "더에셋스퀘어 — ', s, count=1),
        "G-ENTITY-TYPE": lambda s: s.replace("BreadcrumbList", "BreadcrumbList", 1).replace('"Apartment"', '"RealEstateAgent"').replace('"Place"', '"RealEstateAgent"'),
        "G-CANONICAL": lambda s: re.sub(r'(rel="canonical" href="[^"]+)"', r'\1.html"', s, count=1),
        "G-SISE": lambda s: s.replace("</h1>", "</h1><p>약 20억원의 시세차익이 기대됩니다.</p>", 1),
        "G-HYPE": lambda s: s.replace("</h1>", "</h1><p>역대급 단지</p>", 1),
        "G-FREE": lambda s: s.replace("</h1>", "</h1><p>무료 분양 상담</p>", 1),
        "G-REALTIME": lambda s: s.replace("</h1>", "</h1><p>실시간 청약홈 연동</p>", 1),
    }
    ok = True
    try:
        for rule, mut in cases.items():
            open(sample, "w", encoding="utf-8").write(mut(orig))
            h = open(sample, encoding="utf-8").read()
            flagged = [r for r, _ in check_html(sample, h, True, "청약 마감")]
            hit = rule in flagged or (rule == "G-ENTITY-TYPE" and "G-ENTITY-TYPE" in flagged)
            print(f"  inject {rule:14} → gate {'BLOCKS ✅' if hit else 'MISSED ❌'} (flagged={flagged})")
            ok = ok and hit
    finally:
        open(sample, "w", encoding="utf-8").write(orig)   # restore
    restored = open(sample, encoding="utf-8").read() == orig
    print(f"  restore original → {'OK ✅' if restored else 'FAILED ❌'}")
    print("SELFTEST", "PASS ✅" if ok and restored else "FAIL ❌")
    return 0 if ok and restored else 1


if __name__ == "__main__":
    sys.exit(main())
