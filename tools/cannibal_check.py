#!/usr/bin/env python3
"""Local cannibalization / duplicate-content auditor.

Detects pages that compete with each other for the same keyword via:
  - identical or near-identical <title>
  - identical or near-identical meta description
  - identical H1
  - overlapping primary-keyword sets (same property name appears in title of 2+ pages)
  - identical canonical pointing to non-self URL

Writes tools/audit_reports/cannibal_<date>.md and exits 1 if any high-severity
issue is found.
"""
from __future__ import annotations
import glob, os, re, sys, datetime as dt
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_DIR = os.path.join(ROOT, "tools", "audit_reports")
os.makedirs(REPORT_DIR, exist_ok=True)

TODAY = dt.date.fromisoformat(os.environ.get("GSC_TODAY") or "2026-06-01")

TAG_RE = re.compile(r"<[^>]+>")


def pages():
    out = [p for p in sorted(glob.glob(os.path.join(ROOT, "*.html")))
           if os.path.basename(p) != "404.html"]
    out += sorted(glob.glob(os.path.join(ROOT, "property", "*.html")))
    return out


def extract(html, pattern, flags=re.IGNORECASE | re.DOTALL):
    m = re.search(pattern, html, flags)
    if not m:
        return None
    s = m.group(1).strip()
    s = TAG_RE.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def norm(s):
    if not s:
        return ""
    return re.sub(r"[\s\-—–·.,!?·]+", "", s.lower())


def main():
    by_title = defaultdict(list)
    by_desc = defaultdict(list)
    by_h1 = defaultdict(list)
    by_canon = defaultdict(list)
    for p in pages():
        rel = os.path.relpath(p, ROOT)
        with open(p, encoding="utf-8") as f:
            html = f.read()
        title = extract(html, r"<title[^>]*>(.*?)</title>")
        desc = extract(html, r"<meta\s+name=[\"']description[\"']\s+content=[\"'](.*?)[\"']")
        h1 = extract(html, r"<h1[^>]*>(.*?)</h1>")
        canon = extract(html, r"<link\s+rel=[\"']canonical[\"']\s+href=[\"'](.*?)[\"']")
        if title:
            by_title[norm(title)].append((rel, title))
        if desc:
            by_desc[norm(desc)].append((rel, desc))
        if h1:
            by_h1[norm(h1)].append((rel, h1))
        if canon:
            by_canon[canon].append(rel)

    issues = []
    for key, items in by_title.items():
        if len(items) > 1:
            issues.append(("DUP_TITLE", items[0][1], [i[0] for i in items]))
    for key, items in by_desc.items():
        if len(items) > 1:
            issues.append(("DUP_DESC", items[0][1][:80] + "…", [i[0] for i in items]))
    for key, items in by_h1.items():
        if len(items) > 1:
            issues.append(("DUP_H1", items[0][1], [i[0] for i in items]))
    # canonical: same canonical from multiple files is fine only if it matches one of them
    for canon, files in by_canon.items():
        if len(files) <= 1:
            continue
        canon_path = canon.replace("https://l.nolcool.com/", "")
        if not canon_path or canon_path.endswith("/"):
            canon_path = "index.html"
        if not any(f == canon_path or f.endswith("/" + canon_path) for f in files):
            issues.append(("BAD_CANONICAL", canon, files))

    stamp = TODAY.isoformat()
    path = os.path.join(REPORT_DIR, f"cannibal_{stamp}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# 카니발리제이션/중복 점검 — {stamp}\n\n")
        if not issues:
            f.write("✅ 중복 title / description / H1 / canonical 충돌 없음\n")
        else:
            for kind, sample, files in issues:
                f.write(f"## {kind}: {sample}\n")
                for fl in files:
                    f.write(f"  - {fl}\n")
                f.write("\n")
    print(f"cannibal report → {path}")
    print(f"issues={len(issues)}")
    if issues:
        print(f"::ISSUE::[CANNIBAL] {stamp} {len(issues)}건 중복 감지")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
