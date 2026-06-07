#!/usr/bin/env python3
"""Clean render layer — the *body* of the automation.

Two jobs, both driven by the SSOT (tools/data/listings.json):
  • generate_template(slug)  — rebuild the 34 template pages from scratch with
    clean logic (entity, canonical, no estimates, no hype, honest status).
  • fix_existing(slug)       — surgically repair the 46 rich hand-written pages
    WITHOUT destroying their unique content (preserve comp-tables / timelines /
    expert prose), fixing only the four defects + staleness.

Plus: rebuild sitemap.xml (extension-less 200 URLs, per-page lastmod) and a
shared SANITIZE pass + clean-URL pass applied to every page so the build gate
can never see a regression.

The four root fixes baked in here:
  R1 entity   : JSON-LD name = 현장명 ONLY (no "더에셋스퀘어 —"); @type per
                category (Apartment/Place — not RealEstateAgent); + BreadcrumbList.
                title == h1 == schema name.
  R2 canonical: canonical / og:url / internal links / sitemap = extension-less
                200 URL (no .html → no 308 hop).
  R3 data     : no un-sourced 시세차익 amounts, no hype words; status from dates.
  R4 funnel   : 0-hop theassetsquare.com CTA kept; header logo no longer
                target=_blank to self (keeps the satellite's own nav honest).
"""
from __future__ import annotations
import os, re, json, html as _html, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://realestate1-3xh.pages.dev"
MAIN = "https://theassetsquare.com/"
SSOT = os.path.join(ROOT, "tools", "data", "listings.json")
CSS_VER = "2026060802"   # bumped so the status/entity/overflow edits invalidate cache

CAT = {
    "apartment":        {"label": "아파트분양",       "page": "/apartment",        "kw": "아파트분양",   "icon": "🏢", "type": "Apartment"},
    "officetel":        {"label": "오피스텔분양",     "page": "/officetel",         "kw": "오피스텔분양", "icon": "🏬", "type": "Apartment"},
    "store":            {"label": "상가분양",         "page": "/store",             "kw": "상가분양",     "icon": "🛒", "type": "Place"},
    "knowledge-center": {"label": "지식산업센터분양", "page": "/knowledge-center",  "kw": "지식산업센터", "icon": "🏭", "type": "Place"},
    "land":             {"label": "토지분양",         "page": "/land",              "kw": "토지분양",     "icon": "🌳", "type": "Place"},
    "industrial":       {"label": "산업단지분양",     "page": "/industrial",        "kw": "산업단지분양", "icon": "🏗", "type": "Place"},
}
HOOK_BY_CAT = {
    "apartment":        ["청약 전략 분석", "전문가가 본 분양 포인트", "입지·분양가 분석", "꼭 알아야 할 청약 정보"],
    "officetel":        ["수익률·공실 분석", "임대 수요 점검", "1인가구 입지 비교", "임대수익 시뮬레이션"],
    "store":            ["배후 수요·유동인구 분석", "임대수익률 점검", "상권 분석 리포트", "단지내상가 포인트"],
    "knowledge-center": ["분양가 비교 분석", "임대수요·공실 점검", "세제 혜택 정리", "입주 업종 가이드"],
    "land":             ["입지·개발계획 분석", "필지 활용 가이드", "건축 용도 정리", "공급조건 정리"],
    "industrial":       ["입주 조건 비교", "클러스터 분석", "물류·교통 입지 분석", "공급가 정리"],
}

# ── status → badge ──────────────────────────────────────────────────────────
STATUS_BADGE = {
    "청약 접수 중": ("청약 접수 중", "hot"),
    "청약 예정":   ("청약 예정", ""),
    "청약 마감":   ("청약 마감", "done"),
    "분양 중":     ("분양 중", "hot"),
    "분양 예정":   ("분양 예정", ""),
    "분양 정보 확인": ("분양 정보", ""),
}

HYPE = {
    "역대급": "상당한", "초프리미엄": "프리미엄", "로또": "관심",
    "완판": "조기 마감", "대박": "주목", "줍줍": "무순위", "초피": "프리미엄",
    "불장": "강세장",
}

# ─────────────────────────────────────────────────────────────────────────────
def load_ssot():
    d = json.load(open(SSOT, encoding="utf-8"))
    return {r["slug"]: r for r in d["listings"]}, d["today"]


def hook(idx, cat):
    pool = HOOK_BY_CAT.get(cat, ["분양 정보"])
    return pool[idx % len(pool)]


def canonical(slug):
    return f"{SITE}/property/{slug}"


# one money amount, incl. ranges: "20억원", "15억~17억원", "5천만원에서 최대 1억원", "3.3㎡당 800만원"
_MONEY = r"[0-9][0-9,\.]*\s*(?:억|천\s*만|천|만)\s*원?"
_AMT = (r"(?:주변\s*시세\s*대비\s*)?(?:약\s*|최대\s*|최고\s*|기준\s*)*" + _MONEY +
        r"(?:\s*(?:~|에서)\s*(?:최대\s*|최고\s*)?" + _MONEY + r")*\s*(?:대|이상|안팎|상당)?")

_CAVEAT = "분양가 상한제 등으로 인근 실거래가와 차이가 있을 수 있으나, 실제 차익은 시장 상황에 따라 달라지며 보장되지 않습니다."


def neutralize_sise(text: str) -> str:
    """Strip every *numeric* 시세차익 claim; keep clean Korean.

    청약홈 only publishes the offer price — any specific 시세차익 figure is an
    un-sourced projection (diagnosis G2). Strategy, in order:
      1. any *sentence* (period-terminated, no inner tags) mentioning 시세차익
         together with a 억/만원 amount is replaced wholesale by an honest
         'not guaranteed' caveat — this always yields grammatical Korean;
      2. leftover *fragments* (titles, list items, headings with no period) get
         the amount+시세차익 collapsed to the neutral noun '분양가·시세 비교'.
    The bare word 시세차익 with no number attached is left untouched."""
    amt_or_sise = r"(?:" + _AMT + r"|시세\s*차익)"
    # 1) whole-sentence caveat (sentence = run without inner tags or sentence-enders)
    text = re.sub(
        r"[^.。<>]*시세\s*차익[^.。<>]*?" + _MONEY + r"[^.。<>]*[.。]",
        _CAVEAT, text)
    text = re.sub(
        r"[^.。<>]*" + _MONEY + r"[^.。<>]*?시세\s*차익[^.。<>]*[.。]",
        _CAVEAT, text)
    # 2) fragments — collapse amount±시세차익 to a neutral noun
    text = re.sub(_AMT + r"\s*(?:의|규모의)?\s*시세\s*차익", "분양가·시세 비교", text)
    text = re.sub(r"시세\s*차익(?:이|가|은|는|을|를)?\s*" + _AMT, "분양가·시세 비교", text)
    return text


def sanitize(text: str) -> str:
    """Remove hype words and un-sourced 시세차익 amounts. Grammar-preserving.

    Applied to BOTH generated and surgically-fixed HTML so the gate never sees a
    banned phrase. Kept deliberately conservative: it neutralises the specific
    speculative *number*, not the surrounding factual sentence."""
    text = neutralize_sise(text)
    # 2) hype words
    for bad, good in HYPE.items():
        text = text.replace(bad, good)
    return text


def _region_key(region: str) -> str:
    """'서울 서초구 잠원동' → '서울 서초구' for same-area ranking."""
    return " ".join((region or "").split()[:2])


def related_listings(slug, rec, records, k=4):
    """Pick k related venues: same region first, then same category. Never self."""
    cat = rec.get("category")
    mine = _region_key(rec.get("region", ""))
    pool = [r for s, r in records.items() if s != slug and r.get("category") == cat]
    pool.sort(key=lambda r: (0 if _region_key(r.get("region", "")) == mine and mine else 1, r["slug"]))
    if len(pool) < k:  # top up with other categories so a detail is never a dead-end
        extra = [r for s, r in records.items() if s != slug and r.get("category") != cat]
        extra.sort(key=lambda r: (0 if _region_key(r.get("region", "")) == mine and mine else 1, r["slug"]))
        pool = pool + extra
    return pool[:k]


def related_section(slug, rec, records):
    """A '관련 분양 현장' block of content cross-links (raises dwell + inbound;
    kills content dead-ends). Idempotent: callers strip the old block first."""
    rel = related_listings(slug, rec, records)
    if not rel:
        return ""
    cards = []
    for r in rel:
        info = CAT.get(r.get("category"), CAT["apartment"])
        txt, cls = STATUS_BADGE.get(r.get("status"), (r.get("status", "분양 정보"), ""))
        badge_cls = ("prop-badge " + cls).strip()
        loc = r.get("region", "") + (f" · {r['developer']}" if r.get("developer") else "")
        cards.append(
            f'<a href="/property/{r["slug"]}" class="prop-card">'
            f'<div class="prop-thumb">{info["icon"]}</div>'
            f'<div class="prop-body"><span class="{badge_cls}">{txt}</span>'
            f'<h3 class="prop-name">{r["name"]}</h3>'
            f'<p class="prop-location">{loc}</p></div></a>')
    return ('<!--related-->\n<section class="section related-listings">'
            '<h2 class="section-title">관련 분양 현장</h2>'
            '<p class="section-sub">같은 지역·유형의 다른 분양 현장도 함께 확인하세요</p>'
            f'<div class="prop-grid">{"".join(cards)}</div></section>')


_RELATED_RX = re.compile(r'\s*<!--related-->.*?</section>', re.S)


def inject_related(h, slug, rec, records):
    """Whitespace-normalising, idempotent injection just before </main>."""
    body = related_section(slug, rec, records)
    h = _RELATED_RX.sub("", h)                 # drop any prior block (+ leading ws)
    if not body:
        return h
    return re.sub(r"\s*</main>", "\n" + body + "\n</main>", h, count=1)


def clean_jsonld(slug, rec):
    cat = rec["category"]
    info = CAT.get(cat, CAT["apartment"])
    name = rec["name"]
    graph = [
        {
            "@type": info["type"],
            "@id": canonical(slug) + "#listing",
            "name": name,                                  # R1: 현장명 ONLY
            "url": canonical(slug),
            "description": f"{name} {info['label']} 분양 정보 — {rec.get('region','')}".strip(),
            **({"address": {"@type": "PostalAddress", "addressCountry": "KR",
                            "addressLocality": rec["region"]}} if rec.get("region") else {}),
            **({"numberOfAccommodationUnits": rec["total_units"]} if cat in ("apartment", "officetel") and rec.get("total_units") else {}),
        },
        {
            "@type": "BreadcrumbList",                     # R1: breadcrumb schema
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "홈", "item": SITE + "/"},
                {"@type": "ListItem", "position": 2, "name": info["label"], "item": SITE + info["page"]},
                {"@type": "ListItem", "position": 3, "name": name, "item": canonical(slug)},
            ],
        },
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)


# ── header / footer fragments (shared, clean URLs, logo not target=_blank) ────
def header():
    nav = "".join(
        f'<a href="{CAT[c]["page"]}">{lbl}</a>'
        for c, lbl in [("apartment", "아파트"), ("officetel", "오피스텔"), ("store", "상가"),
                       ("knowledge-center", "지식산업센터"), ("land", "토지"), ("industrial", "산업단지")]
    )
    return ('<header class="site-header"><div class="header-inner">'
            '<a href="/" class="logo">더에셋<span>스퀘어</span></a>'
            f'<nav class="nav-links">{nav}</nav>'
            '<button class="hamburger" aria-label="메뉴" aria-expanded="false">☰</button>'
            '</div></header>')


def main_cta_bar():
    return ('<div style="position:fixed;bottom:0;left:0;width:100%;height:48px;background:#2563EB;'
            'display:flex;align-items:center;justify-content:center;z-index:9999">'
            f'<a href="{MAIN}" target="_blank" rel="noopener noreferrer" '
            'style="color:#fff;font-size:16px;font-weight:700;text-decoration:none">'
            '더에셋스퀘어에서 더 보기 →</a></div>\n<div style="height:48px"></div>')


# ─────────────────────────────────────────────────────────────────────────────
def generate_template(slug, rec, idx, today_iso, records=None):
    """Rebuild a template page from SSOT — clean logic, no estimates/hype."""
    cat = rec["category"]
    info = CAT[cat]
    name = rec["name"]
    region = rec.get("region", "")
    dev = rec.get("developer", "")
    units = rec.get("total_units", "")
    sizes = rec.get("size_range", "")
    price = rec.get("price_range", "") or "모집공고문 기준"
    sched = rec.get("schedule", "") or "모집공고문 참조"
    hl = rec.get("highlights", []) or []
    sub = info["kw"]
    h = hook(idx, cat)
    status = rec.get("status", "분양 정보 확인")
    badge_txt, badge_cls = STATUS_BADGE.get(status, (status, ""))

    region_short = region.split()[1] if len(region.split()) > 1 else region
    title = sanitize(f"{name} — {region_short}{sub} {h}")[:60]
    desc = sanitize(
        f"{name}은(는) {region} {info['label']} 현장입니다. {dev} 시공·시행, "
        f"{units}. {sizes}. {sched}. 부동산분양 정보·청약 전략 정리.")[:160]
    canon = canonical(slug)

    cat_alt = {"apartment": "아파트 청약 단지", "officetel": "주거형 오피스텔 단지",
               "store": "단지내 상가 시설", "knowledge-center": "지산 단지",
               "land": "토지 공급", "industrial": "산업 용지 공급"}[cat]

    p1 = (f"{name}은(는) {region}에 들어서는 부동산분양 현장입니다. 본 현장은 {cat_alt} 카테고리에 속하며, "
          f"시공·시행은 {dev or '모집공고 기준 사업주체'}이 맡았습니다. 규모는 {units or '모집공고 참조'}, "
          f"평형은 {sizes or '모집공고 참조'}로 구성됩니다. 분양가는 {price}이며 일정은 {sched} 기준입니다. "
          f"현재 분양 상태는 '{status}'입니다(데이터 기준일 {today_iso}).")
    p2 = ("입지 측면에서 본 단지의 특징은 다음과 같습니다. " +
          " ".join(f"{i+1}) {sanitize(pt)}." for i, pt in enumerate(hl[:4])) +
          (" " if hl else "") +
          f"부동산분양 정보를 검토하실 때 입지·교통·배후수요·공급일정 4가지 축을 기준으로 비교해 보시기 바랍니다.")
    p3 = (f"청약·투자 전략 측면에서 {name}은(는) 자격 요건과 자금 계획을 먼저 확인해야 합니다. "
          f"분양가({price})를 기준으로 자기자금·중도금·잔금을 단계별로 수립하시고, 거주지 우선공급·재당첨 제한 등은 "
          f"입주자모집공고문에서 직접 확인하세요. 일정·분양가·세대수는 모집공고 발표 시점 값이 최종 기준이므로, "
          f"청약홈(applyhome.co.kr) 공고를 함께 확인하시기 바랍니다.")

    stats = [("규모", units or "—"), ("평형/면적", sizes or "—"),
             ("분양가", price), ("분양 상태", status)]
    stats_html = "".join(f'<div class="stat-item"><div class="stat-num">{v}</div>'
                         f'<div class="stat-label">{k}</div></div>' for k, v in stats)
    info_rows = [("현장명", name), ("위치", region or "—"), ("시공·시행", dev or "—"),
                 ("규모", units or "—"), ("평형/면적", sizes or "—"), ("분양가", price),
                 ("일정", sched), ("분양 상태", status), ("카테고리", cat_alt)]
    info_html = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in info_rows)
    hl_html = "".join(f"<li>{sanitize(x)}</li>" for x in hl) or "<li>모집공고문 발표 시 상세 정보가 업데이트됩니다.</li>"

    faqs = [
        (f"{name} 분양 일정은?", f"{sched} 기준입니다(데이터 기준일 {today_iso}). 최신 일정은 청약홈 또는 모집공고문을 확인하세요."),
        (f"{name} 분양가는?", f"{price}입니다. 평형/호실별로 차이가 있으며 모집공고문 발표가가 확정가입니다."),
        (f"{name} 시공·시행사는?", f"{dev or '모집공고 기준 사업주체'}입니다."),
        (f"{name} 현재 분양 상태는?", f"'{status}'입니다(데이터 기준일 {today_iso}, 청약홈 기준)."),
    ]
    faq_html = "".join(f'<div class="faq-item"><div class="faq-q">{q}<span class="arrow">▼</span></div>'
                       f'<div class="faq-a"><div class="faq-a-inner">{a}</div></div></div>' for q, a in faqs)

    jsonld = clean_jsonld(slug, rec)
    cb = int(dt.datetime(*map(int, today_iso.split("-"))).timestamp() * 1000)
    body = f"""<!--cb:{cb}-->
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="theme-color" content="#2563eb">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <link rel="canonical" href="{canon}">
  <link rel="icon" href="/favicon.ico" sizes="32x32">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{desc[:140]}">
  <meta property="og:type" content="article">
  <meta property="og:image" content="{SITE}/og-home.png">
  <meta property="og:url" content="{canon}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title}">
  <meta name="twitter:description" content="{desc[:140]}">
  <meta name="twitter:image" content="{SITE}/og-home.png">
  <meta name="robots" content="index, follow">
  <link rel="stylesheet" href="/style.css?v={CSS_VER}">
  <script type="application/ld+json">{jsonld}</script>
</head>
<body>
<a href="#main-content" class="skip-link" target="_self">본문으로 건너뛰기</a>
{header()}

<main id="main-content">
<div class="breadcrumb"><a href="/">홈</a><span>›</span><a href="{info['page']}">{info['label']}</a><span>›</span>{name}</div>

<section class="detail-hero"><div class="container">
  <h1>{name}</h1>
  <p class="subtitle">{region} · {dev} · {info['label']} · <strong>{status}</strong></p>
</div></section>

<div class="detail-content">
  <div class="stats-bar">{stats_html}</div>

  <h2>{name} 분양 개요</h2>
  <table class="info-table">{info_html}</table>

  <h2>{name} 분양 정보·분석</h2>
  <p>{p1}</p>
  <p>{p2}</p>

  <h2>{name} 핵심 포인트</h2>
  <ul class="highlight-list">{hl_html}</ul>

  <h2>부동산분양 청약·투자 전략</h2>
  <p>{p3}</p>

  <h2>자주 묻는 질문</h2>
  <div class="faq-list">{faq_html}</div>

  <div class="alert-teaser">
    <h3>{name} 분양 정보 더 자세히 확인하기</h3>
    <p>청약 결과·분양가·계약 일정 등 더 자세한 정보는 더에셋스퀘어 본 사이트에서 확인하세요.</p>
    <a href="{MAIN}" target="_blank" rel="noopener">더에셋스퀘어 본 사이트에서 확인 →</a>
  </div>
{related_section(slug, rec, records) if records else ""}
</div>
</main>

<footer class="site-footer"><p>© 2026 더에셋스퀘어. 부동산분양 전문 정보 플랫폼.</p>
<p>분양 데이터 출처: 청약홈(applyhome.co.kr)·LH·공공 분양정보 · 데이터 기준일 {today_iso}</p></footer>

<script defer src="/main.js?v={CSS_VER}"></script>
{main_cta_bar()}
</body>
</html>
"""
    return body


# ── clean-URL + cache-bust passes (applied to every page) ────────────────────
_RX_ABS = re.compile(r"(realestate1-3xh\.pages\.dev/(?:property/)?[a-z0-9\-]+)\.html")
_RX_REL = re.compile(r'href="(/(?:property/)?[a-z][a-z0-9\-]*)\.html(#[^"]*)?"')


def clean_urls(h: str) -> str:
    h = _RX_ABS.sub(r"\1", h)                       # absolute canonical / og:url
    h = _RX_REL.sub(r'href="\1\2"', h)              # relative internal links
    h = re.sub(r"\?v=20\d{8}", f"?v={CSS_VER}", h)  # cache-bust to new CSS_VER
    return h


def wrap_comp_tables(h: str) -> str:
    """Ensure every wide comparison table sits in a horizontal-scroll container
    so it never overflows the viewport on mobile (≤390px). Idempotent: tables
    already preceded by overflow-x:auto are left untouched."""
    def repl(m):
        pre = h[max(0, m.start() - 140):m.start()]
        if "overflow-x:auto" in pre:
            return m.group(0)
        return '<div style="overflow-x:auto">' + m.group(0) + "</div>"
    return re.sub(r'<table class="comp-table">.*?</table>', repl, h, flags=re.S)


def _replace_jsonld(h: str, jsonld: str) -> str:
    pat = re.compile(r'<script type="application/ld\+json">.*?</script>', re.S)
    repl = f'<script type="application/ld+json">{jsonld}</script>'
    if pat.search(h):
        return pat.sub(lambda _m: repl, h, count=1)
    # no JSON-LD present → inject before </head>
    return h.replace("</head>", f"  {repl}\n</head>", 1)


def fix_existing(slug, rec, today_iso, records=None):
    """Surgically repair a rich hand-written page; preserve its unique content."""
    path = os.path.join(ROOT, "property", f"{slug}.html")
    h = open(path, encoding="utf-8").read()
    status = rec.get("status", "분양 정보 확인")

    # R2 clean URLs + cache bust
    h = clean_urls(h)
    # responsive: wrap wide comparison tables in a scroll container
    h = wrap_comp_tables(h)
    # R1 entity: swap in clean @graph (name only + correct type + BreadcrumbList)
    h = _replace_jsonld(h, clean_jsonld(slug, rec))
    # R4 funnel: header logo should not open self in a new tab
    h = h.replace('<a href="/" class="logo" target="_blank" rel="noopener noreferrer">',
                  '<a href="/" class="logo">')
    # R3 hype + un-sourced 시세차익 (body text only; attrs/URLs unaffected)
    h = sanitize(h)
    # drop unverifiable "실시간" feed wording (no real-time feed exists yet)
    h = h.replace("실시간으로 받아보세요", "더에셋스퀘어 본 사이트에서 받아보세요")
    # drop the speculative "예상 시세차익" stat tile entirely
    h = re.sub(r'<div class="stat-item"><div class="stat-num">[^<]*</div>'
               r'<div class="stat-label">[^<]*시세\s*차익[^<]*</div></div>', "", h)
    # status sync — info-table 분양 상태 cell
    h = re.sub(r'(<th>분양\s*상태</th>\s*<td>)[^<]*(</td>)', rf'\g<1>{status}\g<2>', h)
    # expired → no "청약 접수 중", no live timeline node
    if status in ("청약 마감", "분양 종료"):
        h = h.replace("청약 접수 중", status).replace("청약중", status)
        h = h.replace('class="tl-item active"', 'class="tl-item done"')
    # honest data-source line in footer if missing
    if "데이터 기준일" not in h:
        h = re.sub(r'(분양 데이터 출처:[^<]*)</p>',
                   rf'\1 · 데이터 기준일 {today_iso}</p>', h)
    # related cross-links: strip any prior block, re-inject fresh (idempotent)
    if records:
        h = inject_related(h, slug, rec, records)
    return h


# ── home + category static pages (destale, sync badges, honest claims) ───────
_STALE = [
    ("2026년 4월 청약 가능한 실제 현장만 모았다", "지금 청약 가능한 실제 분양 현장"),
    ("2026년 4월 청약 가능한 실제 현장만",       "지금 청약 가능한 실제 현장"),
    ("2026년 4월 청약 가능한 실제 현장",         "지금 청약 가능한 실제 현장"),
    ("2026년 4월 — 지금 청약 가능한 분양 현장",   "지금 청약·분양 중인 분양 현장"),
    ("4월 청약 접수 중 — 서울 핵심",             "서울 핵심 분양 현장"),
    ("2026년 4월 분양예정 — 곧 청약 시작",        "분양 예정 — 곧 청약 시작"),
    ("4월 접수 중인",                           "최근 접수된"),
    ("2026년 4월 기준",                         "최신 데이터 기준"),
    ("2026년 4월 접수 중인",                     "최근"),
    ("부동산분양 전문가의 2026년 4월 시장 분석",   "부동산분양 전문가의 시장 분석"),
    ("2026년 4월",                             "2026년"),
    ("실시간 청약홈 연동",                       "청약홈·공공데이터 기반"),
    # home stat tile splits the false claim across two divs:
    ('<div class="stat-num">실시간</div><div class="stat-label">청약홈 연동</div>',
     '<div class="stat-num">청약홈</div><div class="stat-label">공공 분양정보 기반</div>'),
    ("실시간 업데이트됩니다",                     "정기적으로 업데이트됩니다"),
    ("실시간으로 받아보세요",                     "더에셋스퀘어 본 사이트에서 받아보세요"),
]


def _sync_badges(h: str, records: dict) -> str:
    """Rewrite every prop-card badge to match its slug's current SSOT status."""
    pat = re.compile(r'href="/property/([a-z0-9\-]+)"(?P<mid>.*?)'
                     r'<span class="prop-badge[^"]*">[^<]*</span>', re.S)

    def repl(m):
        slug = m.group(1)
        rec = records.get(slug)
        if not rec:
            return m.group(0)
        txt, cls = STATUS_BADGE.get(rec.get("status"), (rec.get("status", "분양 정보"), ""))
        cls_attr = ("prop-badge " + cls).strip()
        return f'href="/property/{slug}"{m.group("mid")}<span class="{cls_attr}">{txt}</span>'

    return pat.sub(repl, h)


def fix_static_page(path: str, records: dict, today_iso: str) -> str:
    h = open(path, encoding="utf-8").read()
    h = clean_urls(h)
    h = h.replace('<a href="/" class="logo" target="_blank" rel="noopener noreferrer">',
                  '<a href="/" class="logo">')
    h = sanitize(h)
    h = _sync_badges(h, records)
    for a, b in _STALE:
        h = h.replace(a, b)
    # honest "latest update" stat = data date
    h = re.sub(r'<div class="stat-num">2026\.0?\d+</div>',
               f'<div class="stat-num">{today_iso[:7].replace("-", ".")}</div>', h)
    return h


# ── sitemap (extension-less URLs, per-page lastmod) ──────────────────────────
def build_sitemap(records, today_iso):
    urls = [(SITE + "/", today_iso, "daily", "1.0")]
    for c in CAT:
        urls.append((SITE + CAT[c]["page"], today_iso, "daily", "0.9"))
    for slug, rec in sorted(records.items()):
        freq = "daily" if rec.get("status") in ("청약 접수 중", "분양 중", "청약 예정") else "weekly"
        prio = "0.9" if rec.get("category") in ("apartment", "officetel") else "0.8"
        urls.append((canonical(slug), today_iso, freq, prio))
    body = "".join(
        f"  <url><loc>{u}</loc><lastmod>{lm}</lastmod>"
        f"<changefreq>{cf}</changefreq><priority>{pr}</priority></url>\n"
        for u, lm, cf, pr in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemap.org/schemas/sitemap/0.9">\n'.replace("www.sitemap.org", "www.sitemaps.org")
            + body + "</urlset>\n")


# ── driver ───────────────────────────────────────────────────────────────────
def run(write=True):
    records, today_iso = load_ssot()
    # stable index per category for hook rotation
    idx_by_cat = {}
    changed = []
    for slug in sorted(records):
        rec = records[slug]
        cat = rec.get("category") or "apartment"
        i = idx_by_cat.get(cat, 0); idx_by_cat[cat] = i + 1
        path = os.path.join(ROOT, "property", f"{slug}.html")
        if rec.get("template"):
            out = generate_template(slug, rec, i, today_iso, records)
        else:
            out = fix_existing(slug, rec, today_iso, records)
        out = clean_urls(out)          # belt-and-suspenders
        if write:
            cur = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
            if cur != out:
                open(path, "w", encoding="utf-8").write(out)
                changed.append(slug)
    # home + 6 category pages + 404 recovery page (keeps their links clean)
    static = ["index.html", "404.html"] + [f"{c}.html" for c in CAT]
    for fn in static:
        p = os.path.join(ROOT, fn)
        if not os.path.exists(p):
            continue
        out = fix_static_page(p, records, today_iso)
        if write and open(p, encoding="utf-8").read() != out:
            open(p, "w", encoding="utf-8").write(out)
            changed.append(fn)
    sm = build_sitemap(records, today_iso)
    if write:
        open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write(sm)
    print(f"render.run: {len(changed)} pages rewritten (of {len(records)} listings + {len(static)} static)")
    return changed


if __name__ == "__main__":
    run()
