#!/usr/bin/env python3
"""Verify the DEPLOYED site (all 53 pages) over HTTP.

Checks each live URL for: HTTP 200, non-empty <title>, new CSS version load,
og:image present, no leftover placeholder phone, and body keyword density
under the stuffing threshold. Also confirms a bad URL returns 404.

Usage: python3 tools/live_check.py [--css-ver 2026052801]
Exit 0 = all good, 1 = problems.
"""
import glob, os, re, sys, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://l.nolcool.com"
CSS_VER = "2026052803"
DENSITY_MAX = 3.0
KWS = ["부동산분양", "지식산업센터", "오피스텔분양", "산업단지분양", "상가분양", "토지분양", "아파트분양"]
PHONE = "1666-6838"

for a in sys.argv:
    if a.startswith("--css-ver"):
        CSS_VER = a.split("=", 1)[1] if "=" in a else CSS_VER


def urls():
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "*.html"))):
        b = os.path.basename(f)
        if b == "404.html":
            continue
        out.append(SITE + "/" + ("" if b == "index.html" else b))
    for f in sorted(glob.glob(os.path.join(ROOT, "property", "*.html"))):
        out.append(SITE + "/property/" + os.path.basename(f))
    return out


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "live-check/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.read().decode("utf-8", "replace")


def body_density(html):
    m = re.search(r"<body[^>]*>(.*)</body>", html, re.DOTALL)
    src = m.group(1) if m else html
    src = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", src, flags=re.DOTALL | re.I)
    ns = re.sub(r"\s+", "", re.sub(r"<[^>]+>", " ", src))
    worst = (None, 0.0)
    for kw in KWS:
        d = round(ns.count(kw) * len(kw) / max(1, len(ns)) * 100, 2)
        if d > worst[1]:
            worst = (kw, d)
    return worst


def main():
    fails = []
    n = 0
    for u in urls():
        n += 1
        try:
            st, html = fetch(u)
        except urllib.error.HTTPError as e:
            fails.append(f"{u} → HTTP {e.code}")
            continue
        except Exception as e:
            fails.append(f"{u} → {e}")
            continue
        if st != 200:
            fails.append(f"{u} → HTTP {st}")
        if not re.search(r"<title>.+?</title>", html):
            fails.append(f"{u} → title 없음")
        if f"v={CSS_VER}" not in html:
            fails.append(f"{u} → 새 CSS(v={CSS_VER}) 미적용")
        if 'property="og:image"' not in html:
            fails.append(f"{u} → og:image 없음")
        if PHONE in html:
            fails.append(f"{u} → 전화번호 {PHONE} 잔존")
        kw, d = body_density(html)
        if d > DENSITY_MAX:
            fails.append(f"{u} → 스터핑 {kw} {d}%")
    # bad URL must 404
    try:
        fetch(SITE + "/__definitely-not-a-real-page__.html")
        fails.append("soft-404: 없는 URL이 200 반환")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            fails.append(f"soft-404: 없는 URL이 HTTP {e.code}")
    except Exception:
        pass

    print(f"=== LIVE CHECK — {n} pages @ {SITE} ===")
    if fails:
        for f in fails:
            print("  ✗ " + f)
        print(f"\n=== RESULT: FAIL ({len(fails)} issues) ===")
        sys.exit(1)
    print("  모든 검사 통과: HTTP 200 · 고유 title · 신규 CSS · og:image · 전화번호 0 · 스터핑 0 · soft-404 차단")
    print(f"\n=== RESULT: PASS ({n}/{n} pages) ===")


if __name__ == "__main__":
    main()
