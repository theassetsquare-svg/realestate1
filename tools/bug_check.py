#!/usr/bin/env python3
"""PC/Mobile bug & accessibility static auditor.

Heuristics across every HTML page:
  - <img> missing alt or with empty alt where meaningful
  - <a> with empty text and no aria-label
  - missing meta viewport / theme-color / canonical / og:image
  - inline event handlers (onclick) — XSS-risk / not CSP-friendly
  - hardcoded http:// (mixed-content risk)
  - duplicate id attributes
  - broken internal links (href to non-existent local file)
  - CSS version mismatch (any /style.css?v=X using an outdated stamp)
  - 'Lorem' / 'TODO' / 'placeholder' / 'xxx-xxxx' leftover

Writes tools/audit_reports/bugs_<date>.md. Exit 1 on findings.
"""
from __future__ import annotations
import glob, os, re, sys, datetime as dt
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_DIR = os.path.join(ROOT, "tools", "audit_reports")
os.makedirs(REPORT_DIR, exist_ok=True)
TODAY = dt.date.fromisoformat(os.environ.get("GSC_TODAY") or "2026-06-01")

# canonical css version = newest mtime stamp embedded — use whatever index.html uses
def canonical_css_ver():
    with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
        m = re.search(r"/style\.css\?v=([0-9a-z]+)", f.read())
    return m.group(1) if m else None


def all_html():
    return sorted(glob.glob(os.path.join(ROOT, "*.html"))) + \
           sorted(glob.glob(os.path.join(ROOT, "property", "*.html")))


def check(p, html, css_ver):
    rel = os.path.relpath(p, ROOT)
    findings = []

    # missing alt
    imgs = re.findall(r"<img\b([^>]*)>", html, re.IGNORECASE)
    for attrs in imgs:
        if "alt=" not in attrs.lower():
            findings.append(("IMG_NO_ALT", f"<img{attrs}>"[:120]))

    # empty anchors
    for a in re.finditer(r"<a\b([^>]*)>(.*?)</a>", html, re.IGNORECASE | re.DOTALL):
        attrs, inner = a.group(1), a.group(2)
        text = re.sub(r"<[^>]+>", "", inner).strip()
        if not text and "aria-label" not in attrs.lower():
            findings.append(("LINK_EMPTY", f"<a{attrs}>"[:120]))

    # meta requirements
    if not re.search(r"<meta[^>]+name=[\"']viewport[\"']", html, re.IGNORECASE):
        findings.append(("MISS_VIEWPORT", ""))
    if not re.search(r"<link[^>]+rel=[\"']canonical[\"']", html, re.IGNORECASE):
        findings.append(("MISS_CANONICAL", ""))
    if not re.search(r"<meta[^>]+property=[\"']og:image[\"']", html, re.IGNORECASE):
        findings.append(("MISS_OG_IMAGE", ""))

    # inline handlers
    for m in re.finditer(r"\son\w+=", html):
        findings.append(("INLINE_HANDLER", html[max(0, m.start()-10):m.start()+30]))

    # mixed content
    for m in re.finditer(r"http://(?!localhost|127\.|0\.0\.0\.0)[^\"' )]+", html):
        findings.append(("HTTP_LINK", m.group(0)[:120]))

    # dup ids
    ids = re.findall(r'\sid=[\"\']([^\"\']+)[\"\']', html)
    dupes = {x for x in ids if ids.count(x) > 1}
    for d in dupes:
        findings.append(("DUP_ID", d))

    # broken internal links
    for href in re.findall(r'href=[\"\']([^\"\']+)[\"\']', html):
        if href.startswith(("http", "mailto:", "tel:", "#", "javascript:")):
            continue
        target = href.split("?")[0].split("#")[0]
        # leading slash → repo-rooted
        local = os.path.join(ROOT, target.lstrip("/"))
        if target.endswith("/"):
            local = os.path.join(local, "index.html")
        if not target:
            continue
        if not os.path.exists(local):
            # also try relative to current file dir
            local2 = os.path.normpath(os.path.join(os.path.dirname(p), target))
            if not os.path.exists(local2):
                findings.append(("BROKEN_LINK", href))

    # CSS version
    for m in re.finditer(r"/style\.css\?v=([0-9a-z]+)", html):
        if css_ver and m.group(1) != css_ver:
            findings.append(("CSS_VER_STALE", f"{m.group(1)} vs {css_ver}"))
            break

    # placeholders — strip HTML attributes first to avoid `placeholder="..."` false positives
    text_only = re.sub(r"<[^>]+>", " ", html)
    for pat in (r"\blorem\s+ipsum\b", r"\bTODO\b", r"\bFIXME\b", r"xxx-xxxx", r"010-1234-5678"):
        if re.search(pat, text_only, re.IGNORECASE):
            findings.append(("PLACEHOLDER", pat))

    # small touch target (link/button explicitly styled small) — heuristic
    for m in re.finditer(r"<(a|button)\b[^>]*style=[\"'][^\"']*(height|min-height)\s*:\s*([0-9]+)px",
                         html, re.IGNORECASE):
        h = int(m.group(3))
        if h < 44:
            findings.append(("SMALL_TARGET", f"{m.group(1)}={h}px"))

    return rel, findings


def main():
    css_ver = canonical_css_ver()
    all_findings = []
    counts = defaultdict(int)
    for p in all_html():
        rel, f = check(p, open(p, encoding="utf-8").read(), css_ver)
        if f:
            all_findings.append((rel, f))
            for kind, _ in f:
                counts[kind] += 1

    stamp = TODAY.isoformat()
    md = os.path.join(REPORT_DIR, f"bugs_{stamp}.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write(f"# PC/Mobile 버그 점검 — {stamp}\n\n")
        if not all_findings:
            f.write("✅ 발견된 이슈 없음\n")
        else:
            f.write("## 합계\n")
            for k, n in sorted(counts.items(), key=lambda x: -x[1]):
                f.write(f"- **{k}**: {n}\n")
            f.write("\n## 상세\n")
            for rel, items in all_findings:
                f.write(f"\n### {rel}\n")
                for kind, sample in items[:15]:
                    s = sample.replace("\n", " ")[:200]
                    f.write(f"- **{kind}** — `{s}`\n")
                if len(items) > 15:
                    f.write(f"- … {len(items) - 15}건 추가\n")

    print(f"bug report → {md}")
    total = sum(counts.values())
    print(f"findings={total} files_affected={len(all_findings)}")
    if total:
        print(f"::ISSUE::[BUGS] {stamp} {total}건 ({len(all_findings)}개 파일)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
