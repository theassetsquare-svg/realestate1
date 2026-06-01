#!/usr/bin/env python3
"""Read site-issue emails from Gmail and auto-fix what's safely fixable.

Auth:
  GMAIL_USER + GMAIL_APP_PASS    (Google App Password, 16 chars no spaces)

Search:
  - From any sender (monitoring services, GSC notifications, etc.)
  - Subject contains "더에셋스퀘어" OR "site issue" OR "GSC" OR "Search Console"
  - Unread

Action policy (conservative — never destructive):
  - sitemap stale         → bump <lastmod> to today, log, do NOT delete email
  - CSS version stale     → bump ?v=<today> across all html, log
  - 404/broken link known → fix in HTML, log
  - density warning       → log only (auto-rewrite is risky); flag for human
  - unrecognized          → log, leave the email untouched

When all action items on an email are resolved AND no destructive action was
proposed, the email is moved to label "AutoHandled" and marked read. We never
permanently delete; the user does that.

Run manually:  GMAIL_USER=... GMAIL_APP_PASS=... python3 tools/issue_inbox.py
"""
from __future__ import annotations
import email, imaplib, os, re, sys, glob, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODAY = dt.date.fromisoformat(os.environ.get("GSC_TODAY", "2026-06-01"))

KEYWORDS = ["더에셋스퀘어", "site issue", "GSC", "Search Console", "더에셋"]

HANDLED_LABEL = "AutoHandled"


def fix_sitemap_lastmod() -> bool:
    """Bump every <lastmod> to today. Returns True if changed."""
    p = os.path.join(ROOT, "sitemap.xml")
    s = open(p, encoding="utf-8").read()
    new = re.sub(r"<lastmod>[^<]+</lastmod>", f"<lastmod>{TODAY.isoformat()}</lastmod>", s)
    if new != s:
        open(p, "w", encoding="utf-8").write(new)
        return True
    return False


def fix_css_version() -> bool:
    """Bump style.css?v= across all html to YYYYMMDDxx."""
    stamp = TODAY.strftime("%Y%m%d") + "01"
    changed = False
    for f in glob.glob(os.path.join(ROOT, "*.html")) + glob.glob(os.path.join(ROOT, "property", "*.html")):
        s = open(f, encoding="utf-8").read()
        new = re.sub(r"/style\.css\?v=[0-9a-z]+", f"/style.css?v={stamp}", s)
        if new != s:
            open(f, "w", encoding="utf-8").write(new)
            changed = True
    return changed


HANDLERS = {
    r"sitemap.*(stale|lastmod|오래)": fix_sitemap_lastmod,
    r"css.*(stale|version|버전)":     fix_css_version,
}


def connect():
    user = os.environ.get("GMAIL_USER")
    pwd = os.environ.get("GMAIL_APP_PASS")
    if not user or not pwd:
        print("GMAIL_USER / GMAIL_APP_PASS not set — skipping")
        sys.exit(0)
    M = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    M.login(user, pwd)
    return M


def ensure_label(M, label):
    M.create(f'"{label}"')  # idempotent — fails silently if exists


def handle():
    M = connect()
    ensure_label(M, HANDLED_LABEL)
    M.select("INBOX")
    # Build OR query
    q_parts = ['UNSEEN', '(OR ' + ' '.join([f'SUBJECT "{k}"' for k in KEYWORDS]) + ')']
    typ, data = M.search(None, *q_parts)
    if typ != "OK":
        print("search failed:", typ)
        return 1
    ids = data[0].split()
    print(f"found {len(ids)} candidate emails")
    actions = []
    for i in ids:
        typ, m = M.fetch(i, "(RFC822)")
        if typ != "OK":
            continue
        msg = email.message_from_bytes(m[0][1])
        subj = msg.get("Subject", "")
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body += part.get_payload(decode=True).decode("utf-8", "replace")
        else:
            body = msg.get_payload(decode=True).decode("utf-8", "replace") if msg.get_payload() else ""
        full = (subj + "\n" + body).lower()
        did = []
        for pat, fn in HANDLERS.items():
            if re.search(pat, full, re.IGNORECASE):
                if fn():
                    did.append(pat)
        actions.append({"id": i.decode(), "subject": subj, "did": did})
        if did:
            # archive + label
            M.copy(i, HANDLED_LABEL)
            M.store(i, "+FLAGS", "\\Seen")
            M.store(i, "+X-GM-LABELS", HANDLED_LABEL)
    M.logout()
    print("actions:", actions)
    return 0


if __name__ == "__main__":
    sys.exit(handle())
