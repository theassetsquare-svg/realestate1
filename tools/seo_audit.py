#!/usr/bin/env python3
"""TheAssetSquare sub-site — SEO / debug auditor.

Audits every HTML page for: keyword stuffing, duplicate title/description,
broken asset & internal-link references, JSON-LD validity, meta completeness,
sitemap coverage, and basic HTML sanity.

Usage:
    python3 tools/seo_audit.py            # audit local files
    python3 tools/seo_audit.py --json     # machine-readable output
    python3 tools/seo_audit.py --strict   # exit 1 on any WARN too

Exit code 0 = no errors, 1 = errors found (CI-friendly).
"""
from __future__ import annotations
import json, os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://realestate1-3xh.pages.dev"

# Primary keyword (must appear) + per-section sub keywords.
PRIMARY = "부동산분양"
SUBS = ["아파트분양", "오피스텔분양", "상가분양", "지식산업센터", "토지분양", "산업단지분양"]

# Density targets (CLAUDE.md): primary+sub 1.5–2.5%. Flag stuffing above MAX.
DENSITY_MIN = 1.0      # warn if a keyword the page is "about" is under this
DENSITY_MAX = 3.0      # ERROR (stuffing) above this for any single keyword
TITLE_MAX = 60
DESC_MIN, DESC_MAX = 70, 165

TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
WS_RE = re.compile(r"\s+")


def html_files():
    files = sorted(glob.glob(os.path.join(ROOT, "*.html")))
    files += sorted(glob.glob(os.path.join(ROOT, "property", "*.html")))
    return files


def rel(p):
    return os.path.relpath(p, ROOT)


def visible_text(html: str) -> str:
    # density is measured on <body> only — <title>/<meta> are graded separately
    body = re.search(r"<body[^>]*>(.*)</body>", html, re.DOTALL)
    src = body.group(1) if body else re.sub(r"<head\b.*?</head>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    no_cs = SCRIPT_STYLE_RE.sub(" ", src)
    txt = TAG_RE.sub(" ", no_cs)
    txt = (txt.replace("&nbsp;", " ").replace("&amp;", "&")
              .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"'))
    return WS_RE.sub(" ", txt).strip()


def extract(pattern, html, flags=0):
    m = re.search(pattern, html, flags)
    return m.group(1).strip() if m else None


def density(text_nospace: str, kw: str) -> float:
    if not text_nospace:
        return 0.0
    occ = text_nospace.count(kw)
    return round(occ * len(kw) / len(text_nospace) * 100, 2)


def repeated_words(html: str):
    """Detect immediate duplicate Korean tokens in PROSE only (<p> text).

    Tables/cards legitimately repeat values across cells, so we only scan
    sentence prose to avoid false positives.
    """
    issues = []
    for para in re.findall(r"<p\b[^>]*>(.*?)</p>", html, re.DOTALL):
        prose = WS_RE.sub(" ", TAG_RE.sub(" ", para)).strip()
        toks = prose.split()
        for i in range(len(toks) - 1):
            a, b = toks[i], toks[i + 1]
            if a == b and len(a) >= 2 and re.search(r"[가-힣]", a):
                issues.append(a)
    return issues


def audit():
    files = html_files()
    pages = {}
    titles, descs = {}, {}
    errors, warns = [], []

    # local asset existence helper
    def local_exists(url: str) -> bool:
        if url.startswith("http"):
            return None  # external, skip
        path = url.split("?")[0].split("#")[0].lstrip("/")
        return os.path.exists(os.path.join(ROOT, path))

    for f in files:
        html = open(f, encoding="utf-8").read()
        r = rel(f)
        title = extract(r"<title>(.*?)</title>", html, re.DOTALL)
        desc = extract(r'name="description"\s+content="(.*?)"', html, re.DOTALL)
        canonical = extract(r'rel="canonical"\s+href="(.*?)"', html)
        og_image = extract(r'property="og:image"\s+content="(.*?)"', html)
        h1s = re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL)
        viewport = 'name="viewport"' in html
        robots = extract(r'name="robots"\s+content="(.*?)"', html)

        text = visible_text(html)
        text_ns = text.replace(" ", "")
        total = len(text_ns)

        dens = {PRIMARY: density(text_ns, PRIMARY)}
        for s in SUBS:
            dens[s] = density(text_ns, s)

        pages[r] = {
            "title": title, "title_len": len(title) if title else 0,
            "desc": desc, "desc_len": len(desc) if desc else 0,
            "canonical": canonical, "og_image": og_image,
            "h1_count": len(h1s), "viewport": viewport, "robots": robots,
            "text_chars": total, "density": dens,
        }

        # ---- checks ----
        if not title:
            errors.append(f"{r}: <title> 없음")
        elif len(title) > TITLE_MAX:
            warns.append(f"{r}: title {len(title)}자 (>{TITLE_MAX})")
        if not desc:
            errors.append(f"{r}: meta description 없음")
        elif not (DESC_MIN <= len(desc) <= DESC_MAX):
            warns.append(f"{r}: description {len(desc)}자 (권장 {DESC_MIN}-{DESC_MAX})")
        if not canonical:
            errors.append(f"{r}: canonical 없음")
        if not viewport:
            errors.append(f"{r}: viewport meta 없음")
        if len(h1s) == 0:
            errors.append(f"{r}: <h1> 없음")
        elif len(h1s) > 1:
            warns.append(f"{r}: <h1> {len(h1s)}개 (1개 권장)")
        if PRIMARY not in text_ns and r in ("index.html",):
            errors.append(f"{r}: 홈에 '{PRIMARY}' 키워드 없음")

        # keyword stuffing (any keyword over MAX)
        for kw, d in dens.items():
            if d > DENSITY_MAX:
                errors.append(f"{r}: 키워드 스터핑 '{kw}' 밀도 {d}% (>{DENSITY_MAX}%)")

        # asset refs
        for url in re.findall(r'(?:href|src|content)="([^"]+\.(?:png|jpg|jpeg|webp|ico|css|js|svg))(?:\?[^"]*)?"', html):
            ex = local_exists(url)
            if ex is False:
                errors.append(f"{r}: 깨진 자산 참조 {url}")

        # internal links
        for href in re.findall(r'href="(/[^":]+\.html)"', html):
            if local_exists(href) is False:
                errors.append(f"{r}: 깨진 내부링크 {href}")

        # JSON-LD validity
        for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL):
            try:
                json.loads(block)
            except Exception as e:
                errors.append(f"{r}: JSON-LD 오류 {e}")

        # repeated-word grammar smell (prose only)
        for w in set(repeated_words(html)):
            warns.append(f"{r}: 단어 중복 '{w} {w}'")

        titles.setdefault(title, []).append(r)
        descs.setdefault(desc, []).append(r)

    # duplicate titles / descriptions
    for t, fs in titles.items():
        if t and len(fs) > 1:
            errors.append(f"중복 title '{t}' → {', '.join(fs)}")
    for d, fs in descs.items():
        if d and len(fs) > 1:
            errors.append(f"중복 description → {', '.join(fs)}")

    # sitemap coverage
    smap = os.path.join(ROOT, "sitemap.xml")
    if os.path.exists(smap):
        sm = open(smap, encoding="utf-8").read()
        listed = set(re.findall(r"<loc>(.*?)</loc>", sm))
        for f in files:
            r = rel(f)
            url = SITE + "/" + ("" if r == "index.html" else r)
            if url not in listed:
                errors.append(f"sitemap 누락: {url}")
        for u in listed:
            p = u.replace(SITE + "/", "")
            p = "index.html" if p == "" else p
            if not os.path.exists(os.path.join(ROOT, p)):
                errors.append(f"sitemap 잘못된 URL(파일없음): {u}")
    else:
        errors.append("sitemap.xml 없음")

    return {"pages": pages, "errors": errors, "warns": warns, "count": len(files)}


def main():
    res = audit()
    if "--json" in sys.argv:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"=== SEO/DEBUG AUDIT — {res['count']} pages ===\n")
        # density table (only flag interesting rows)
        print("--- 키워드 밀도 (스터핑 의심 ≥ {:.1f}%) ---".format(DENSITY_MAX))
        for r, p in res["pages"].items():
            hot = {k: v for k, v in p["density"].items() if v >= 2.0}
            if hot:
                print(f"  {r}: " + ", ".join(f"{k}={v}%" for k, v in hot.items()))
        print(f"\n--- ERRORS ({len(res['errors'])}) ---")
        for e in res["errors"]:
            print("  ✗ " + e)
        print(f"\n--- WARNINGS ({len(res['warns'])}) ---")
        for w in res["warns"]:
            print("  ⚠ " + w)
        status = "FAIL" if res["errors"] else ("WARN" if res["warns"] else "PASS")
        print(f"\n=== RESULT: {status} (errors={len(res['errors'])}, warns={len(res['warns'])}) ===")

    bad = bool(res["errors"]) or ("--strict" in sys.argv and bool(res["warns"]))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
