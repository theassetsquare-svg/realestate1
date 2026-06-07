#!/usr/bin/env python3
"""Daily content pipeline — the automation entrypoint (run by the cron workflow).

Order (each step is honest + idempotent):
  1. chungyang_fetch  — pull official 청약홈 data IF a key is set (else no-op,
                        no fabrication).
  2. ssot             — rebuild listings.json from pages + feed; recompute every
                        status against *today* → expired 청약 auto-closes.
  3. render           — regenerate the 34 template pages with clean logic and
                        surgically refresh the 46 rich pages + home/categories +
                        sitemap (clean URLs, entity, no estimates/hype).
  4. gate             — BLOCK if any defect slipped in; nonzero exit stops the
                        deploy (the workflow only commits when the gate passes).
  5. indexnow         — best-effort ping (key-gated) + sitemap is refreshed for
                        Naver Search Advisor / Google to recrawl.

The workflow commits & pushes the changed files only when this script returns 0.
"""
from __future__ import annotations
import os, sys, json, subprocess, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://realestate1-3xh.pages.dev"


def step(name, argv):
    print(f"\n=== {name} ===")
    r = subprocess.run(argv, cwd=ROOT)
    return r.returncode


def indexnow(today: dt.date):
    """Best-effort IndexNow submit (Bing/Yandex/Seznam). Key-gated, never fatal.
    Naver uses Search Advisor (sitemap), so we always refresh sitemap.xml above."""
    key = os.environ.get("INDEXNOW_KEY")
    if not key:
        print("ℹ INDEXNOW_KEY 미설정 — IndexNow 핑 생략(사이트맵은 갱신됨).")
        return
    import urllib.request
    try:
        listings = json.load(open(os.path.join(ROOT, "tools", "data", "listings.json"), encoding="utf-8"))["listings"]
        urls = [f"{SITE}/", *(f"{SITE}/property/{r['slug']}" for r in listings)]
        body = json.dumps({"host": SITE.split("//")[1], "key": key,
                           "keyLocation": f"{SITE}/{key}.txt", "urlList": urls}).encode()
        req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"  IndexNow → HTTP {r.status} ({len(urls)} URLs)")
    except Exception as e:
        print(f"  IndexNow 핑 실패(비치명적): {e}")


def main():
    today = dt.date.fromisoformat(os.environ.get("GSC_TODAY") or dt.date.today().isoformat())
    os.environ["GSC_TODAY"] = today.isoformat()
    py = sys.executable

    step("1/5 청약홈 실데이터 fetch", [py, "tools/chungyang_fetch.py"])
    if step("2/5 SSOT 재빌드", [py, "tools/ssot.py"]) != 0:
        print("❌ SSOT 실패"); return 1
    if step("3/5 페이지 재생성/갱신 + 사이트맵", [py, "-c", "import tools.render as R; R.run()"]) != 0:
        print("❌ render 실패"); return 1
    gate_rc = step("4/5 빌드 게이트", [py, "tools/gate.py"])
    if gate_rc != 0:
        print("❌ 게이트 실패 — 배포 차단(결함 양산 방지). 커밋하지 않습니다.")
        return 1
    print("\n=== 5/5 IndexNow ===")
    indexnow(today)
    print("\n✅ daily_update 완료 — 게이트 통과, 배포 가능 상태")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
