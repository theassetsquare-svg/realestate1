#!/usr/bin/env python3
"""Email the latest status report to the owner.

Two transport options, picked by env:
  - RESEND_API_KEY → POST to api.resend.com (preferred, no SMTP)
  - GMAIL_APP_PASS + GMAIL_USER → SMTP via Gmail

If neither is configured, the script still prints the summary and exits 0
(no-op). The 24h GitHub Action wires whichever secret is available.
"""
from __future__ import annotations
import glob, json, os, smtplib, sys, urllib.request, datetime as dt
from email.mime.text import MIMEText

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TO = "theassetsquare@gmail.com"
TODAY = dt.date.fromisoformat(os.environ.get("GSC_TODAY") or "2026-06-01")


def latest_status():
    files = sorted(glob.glob(os.path.join(ROOT, "tools", "audit_reports", "status_*.json")))
    if not files:
        return None
    with open(files[-1], encoding="utf-8") as f:
        data = json.load(f)
    md_path = files[-1].replace(".json", ".md")
    body = open(md_path, encoding="utf-8").read() if os.path.exists(md_path) else json.dumps(data, indent=2)
    return data, body


def send_resend(subject, body):
    key = os.environ["RESEND_API_KEY"]
    body_html = "<pre style='font-family:ui-monospace,monospace'>" + body.replace("<", "&lt;") + "</pre>"
    payload = json.dumps({
        "from": os.environ.get("RESEND_FROM", "onboarding@resend.dev"),
        "to": [TO],
        "subject": subject,
        "html": body_html,
        "text": body,
    }).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails", data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        print("resend:", r.status, r.read()[:200])


def send_smtp(subject, body):
    user = os.environ["GMAIL_USER"]
    pwd = os.environ["GMAIL_APP_PASS"]
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = user
    msg["To"] = TO
    msg["Subject"] = subject
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(user, pwd)
        s.sendmail(user, [TO], msg.as_string())
    print("smtp:", "sent")


def main():
    s = latest_status()
    if not s:
        print("no status report")
        return 0
    data, body = s
    ok = data["all_ok"]
    failed = [r["name"] for r in data["results"] if not r["ok"]]
    if ok and os.environ.get("NOTIFY_ONLY_ON_ISSUE", "1") == "1":
        print("status OK — skip email (set NOTIFY_ONLY_ON_ISSUE=0 to always send)")
        return 0
    subj = (f"[더에셋스퀘어 서브] ✅ {data['date']} 모두 통과"
            if ok else f"[더에셋스퀘어 서브] 🛑 {data['date']} 이슈: {', '.join(failed)}")
    try:
        if os.environ.get("RESEND_API_KEY"):
            send_resend(subj, body)
        elif os.environ.get("GMAIL_APP_PASS") and os.environ.get("GMAIL_USER"):
            send_smtp(subj, body)
        else:
            print("no email transport configured (set RESEND_API_KEY or GMAIL_APP_PASS+GMAIL_USER)")
    except Exception as e:
        print("send error:", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
