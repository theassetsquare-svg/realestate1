#!/usr/bin/env python3
"""Pure-stdlib Google Search Console API client.

Uses a service-account JSON key. Signs the JWT with `openssl` (stdlib has no
RS256), exchanges it for an OAuth2 access token, then calls the GSC API over
plain urllib. No pip dependencies, on purpose — this server has no pip.

Env / args:
  GSC_KEY                 path to service-account JSON (default ~/.gsc/theasset-gsc.json)
  GSC_SITE                Search Console property (default https://l.nolcool.com/)
  OPENSSL                 openssl binary path (default: auto-discover under /nix/store)

Usage as library:
    from gsc_client import GSC
    g = GSC()
    rows = g.query(start="2026-05-04", end="2026-06-01",
                   dimensions=["query", "page"], rowLimit=500)
"""
from __future__ import annotations
import base64, glob, json, os, shutil, subprocess, time, urllib.request, urllib.error

DEFAULT_KEY = os.path.expanduser("~/.gsc/theasset-gsc.json")
DEFAULT_SITE = "https://l.nolcool.com/"
TOKEN_URL = "https://oauth2.googleapis.com/token"
# full scope = read + sitemap submit. Service account is owner so this is fine.
SCOPE = "https://www.googleapis.com/auth/webmasters"
API = "https://searchconsole.googleapis.com/webmasters/v3"


def _find_openssl():
    p = os.environ.get("OPENSSL")
    if p and os.path.isfile(p):
        return p
    p = shutil.which("openssl")
    if p:
        return p
    # nix-store fallback (this dev env has openssl only there)
    for c in sorted(glob.glob("/nix/store/*-openssl-*-bin/bin/openssl"), reverse=True):
        return c
    raise RuntimeError("openssl binary not found")


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


class GSC:
    def __init__(self, key_path: str = None, site: str = None):
        self.key_path = key_path or os.environ.get("GSC_KEY", DEFAULT_KEY)
        self.site = site or os.environ.get("GSC_SITE", DEFAULT_SITE)
        with open(self.key_path) as f:
            self.creds = json.load(f)
        self.openssl = _find_openssl()
        self._token = None
        self._token_exp = 0

    # ---------- auth ----------
    def _sign_jwt(self) -> str:
        now = int(time.time())
        header = {"alg": "RS256", "typ": "JWT", "kid": self.creds["private_key_id"]}
        claims = {
            "iss": self.creds["client_email"],
            "scope": SCOPE,
            "aud": self.creds["token_uri"],
            "iat": now,
            "exp": now + 3600,
        }
        msg = _b64url(json.dumps(header, separators=(",", ":")).encode()) + "." + \
              _b64url(json.dumps(claims, separators=(",", ":")).encode())
        # sign with openssl: stdin=msg, stdout=signature bytes
        sig = subprocess.run(
            [self.openssl, "dgst", "-sha256", "-sign", "/dev/stdin"],
            input=msg.encode(),
            env={**os.environ, "OPENSSL_CONF": "/dev/null"},
            capture_output=True,
            check=False,
        )
        # /dev/stdin trick for key — actually openssl needs key file. Use temp.
        if sig.returncode != 0:
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
                f.write(self.creds["private_key"])
                pem_path = f.name
            try:
                sig = subprocess.run(
                    [self.openssl, "dgst", "-sha256", "-sign", pem_path],
                    input=msg.encode(), capture_output=True, check=True,
                )
            finally:
                os.unlink(pem_path)
        return msg + "." + _b64url(sig.stdout)

    def _access_token(self) -> str:
        if self._token and time.time() < self._token_exp - 60:
            return self._token
        assertion = self._sign_jwt()
        body = ("grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer"
                f"&assertion={assertion}").encode()
        req = urllib.request.Request(
            self.creds["token_uri"], data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        self._token = data["access_token"]
        self._token_exp = time.time() + int(data.get("expires_in", 3600))
        return self._token

    # ---------- API ----------
    def _request(self, method: str, path: str, body=None):
        url = f"{API}{path}"
        headers = {"Authorization": f"Bearer {self._access_token()}"}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                if not raw:
                    return {"ok": True, "status": r.status}
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            try:
                err = json.loads(e.read())
            except Exception:
                err = {"raw": str(e)}
            raise RuntimeError(f"GSC API {method} {path} → {e.code}: {err}") from None

    def sites(self):
        return self._request("GET", "/sites")

    def query(self, *, start: str, end: str, dimensions=("query",),
              rowLimit: int = 1000, startRow: int = 0, filters=None, type: str = "web"):
        body = {
            "startDate": start, "endDate": end,
            "dimensions": list(dimensions),
            "rowLimit": rowLimit, "startRow": startRow,
            "type": type,
        }
        if filters:
            body["dimensionFilterGroups"] = [{"filters": filters}]
        from urllib.parse import quote
        path = f"/sites/{quote(self.site, safe='')}/searchAnalytics/query"
        return self._request("POST", path, body)

    def submit_sitemap(self, sitemap_url: str):
        from urllib.parse import quote
        path = f"/sites/{quote(self.site, safe='')}/sitemaps/{quote(sitemap_url, safe='')}"
        return self._request("PUT", path)


if __name__ == "__main__":
    g = GSC()
    print("sites:", json.dumps(g.sites(), indent=2, ensure_ascii=False)[:600])
