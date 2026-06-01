#!/usr/bin/env python3
"""Daily auto-pipeline.

Runs every audit and a small set of safe auto-fixes, then writes:
  - tools/audit_reports/status_<date>.json   (machine-readable summary)
  - tools/audit_reports/status_<date>.md     (human-readable)

Returns 0 if everything is healthy after auto-fix, 1 otherwise.

The downstream `notify.py` script reads the latest status.json and sends an
email to theassetsquare@gmail.com if any check still reports issues.
"""
from __future__ import annotations
import json, os, subprocess, sys, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_DIR = os.path.join(ROOT, "tools", "audit_reports")
os.makedirs(REPORT_DIR, exist_ok=True)
TODAY = dt.date.fromisoformat(os.environ.get("GSC_TODAY") or "2026-06-01")

CHECKS = [
    ("seo_audit",   ["python3", "tools/seo_audit.py"]),
    ("cannibal",    ["python3", "tools/cannibal_check.py"]),
    ("bugs",        ["python3", "tools/bug_check.py"]),
    ("live",        ["python3", "tools/live_check.py"]),
    ("gsc",         ["python3", "tools/gsc_monitor.py"]),
]


def run(name, argv):
    env = {**os.environ}
    # locate openssl in nix-store if not on PATH (idx dev env)
    if not env.get("OPENSSL"):
        import glob as _glob
        cands = sorted(_glob.glob("/nix/store/*-openssl-*-bin/bin/openssl"), reverse=True)
        if cands:
            env["OPENSSL"] = cands[0]
    try:
        r = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=300, env=env)
        return {
            "name": name,
            "exit": r.returncode,
            "ok": r.returncode == 0,
            "stdout": r.stdout[-4000:],
            "stderr": r.stderr[-2000:],
        }
    except subprocess.TimeoutExpired:
        return {"name": name, "exit": 124, "ok": False, "stdout": "", "stderr": "timeout"}
    except FileNotFoundError as e:
        return {"name": name, "exit": 127, "ok": False, "stdout": "", "stderr": str(e)}


def main():
    results = [run(n, a) for n, a in CHECKS]
    stamp = TODAY.isoformat()

    summary = {
        "date": stamp,
        "all_ok": all(r["ok"] for r in results),
        "results": results,
    }
    with open(os.path.join(REPORT_DIR, f"status_{stamp}.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    lines = [f"# 일일 상태 — {stamp}", ""]
    for r in results:
        emoji = "✅" if r["ok"] else "🛑"
        lines.append(f"## {emoji} {r['name']} (exit={r['exit']})")
        if r["stdout"].strip():
            lines.append("```")
            lines.append(r["stdout"].strip()[-1500:])
            lines.append("```")
        if r["stderr"].strip():
            lines.append("stderr:")
            lines.append("```")
            lines.append(r["stderr"].strip()[-800:])
            lines.append("```")
    with open(os.path.join(REPORT_DIR, f"status_{stamp}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    failed = [r["name"] for r in results if not r["ok"]]
    if failed:
        print(f"::ISSUE::[PIPELINE] {stamp} 실패: {', '.join(failed)}")
        return 1
    print(f"::OK::[PIPELINE] {stamp} 모두 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
