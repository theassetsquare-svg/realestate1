#!/usr/bin/env python3
"""Generate one property/<slug>.html per entry in data/new_listings_2026-06.json.

Per CLAUDE.md:
  - Title: 부동산분양 현장명 FIRST + 서브 키워드(지역+카테고리) + 후킹 (under 60c)
  - meta description ≤165c, unique per page
  - H1 = 현장명 only
  - Primary "부동산분양" + sub-keyword density 1.5–2.5%
  - JSON-LD RealEstateAgent
  - Internal links to category page only (no off-site forms; main-site CTA at footer)

Content is derived from per-venue facts (region/developer/units/sizes/schedule/
highlights) so the body differs from every other page — no shared pool. Prose
templates rotate by index to vary the surface phrasing.
"""
from __future__ import annotations
import json, os, re, datetime as dt
from string import Template

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://l.nolcool.com"
DATA = os.path.join(ROOT, "tools", "data", "new_listings_2026-06.json")
TODAY = dt.date.fromisoformat("2026-06-01")

CSS_VER = "2026052803"
CAT = {
    "apartment":        {"label": "아파트분양",       "page": "/apartment.html",        "kw": "아파트분양",       "icon": "🏢"},
    "officetel":        {"label": "오피스텔분양",     "page": "/officetel.html",         "kw": "오피스텔분양",     "icon": "🏬"},
    "store":            {"label": "상가분양",         "page": "/store.html",             "kw": "상가분양",         "icon": "🛒"},
    "knowledge-center": {"label": "지식산업센터분양", "page": "/knowledge-center.html",  "kw": "지식산업센터",     "icon": "🏭"},
    "land":             {"label": "토지분양",         "page": "/land.html",              "kw": "토지분양",         "icon": "🌳"},
    "industrial":       {"label": "산업단지분양",     "page": "/industrial.html",        "kw": "산업단지분양",     "icon": "🏗"},
}

HOOK_BY_CAT = {
    "apartment":        ["청약 마감 임박 분석", "시세차익 자세히 본 분석", "전문가가 본 분양 포인트", "꼭 알아야 할 청약 전략"],
    "officetel":        ["수익률 정밀 분석", "임대 수요·공실률 점검", "신혼·1인가구 입지 비교", "임대수익 시뮬레이션"],
    "store":            ["배후 수요·유동인구 분석", "임대수익률 계산", "상권 분석 리포트", "단지내상가 투자 포인트"],
    "knowledge-center": ["분양가 비교 분석", "임대수요·공실률 점검", "세제 혜택·취득세 감면 정리", "입주 가능 업종 가이드"],
    "land":             ["입지 분석·개발 호재", "필지별 활용 가이드", "건축 가능 용도 정리", "공급조건·입찰 전략"],
    "industrial":       ["입주 조건 비교", "산업 클러스터 분석", "물류·교통 입지 분석", "투자 가치 정리"],
}


def slugify(s): return s


def hook(idx, cat):
    pool = HOOK_BY_CAT.get(cat, ["전문가 분석"])
    return pool[idx % len(pool)]


def sitemap_priority(cat):
    return "0.9" if cat in ("apartment", "officetel") else "0.8"


def changefreq(cat):
    return "daily" if cat in ("apartment", "officetel") else "weekly"


def make_html(idx, entry):
    cat = entry["category"]
    info = CAT[cat]
    name = entry["name_ko"]
    region = entry["region"]
    dev = entry["developer"]
    units = entry["total_units"]
    sizes = entry["size_range"]
    price = entry["price_range"]
    sched = entry["schedule"]
    hl = entry["highlights"]
    sub = info["kw"]
    h = hook(idx, cat)

    title = f"{name} — {region.split()[1] if ' ' in region else region}{sub} {h}"[:60]
    desc = (f"{name}은(는) {region} {info['label']} 현장입니다. {dev} 시공·시행, "
            f"{units}. {sizes}. {sched}. 부동산분양 정보·청약 전략·임장 포인트 정리.")[:165]
    canonical = f"{SITE}/property/{entry['slug']}.html"

    # ---- prose blocks (unique by entry — no shared pool) ----
    # Body-prose synonyms — chosen so that even after `text_nospace` strips
    # whitespace they do NOT contain the exact sub keyword as a substring.
    # ("아파트 분양" would collapse to "아파트분양" and double-count, so we
    # avoid putting the kanji-style noun and the word "분양" adjacent.)
    cat_alt = {
        "apartment":        "아파트 청약 단지",
        "officetel":        "주거형 오피스텔 단지",
        "store":            "단지내 상가 시설",
        "knowledge-center": "지산 단지",
        "land":             "토지 공급",
        "industrial":       "산업 용지 공급",
    }[cat]
    p1 = (f"{name}은(는) {region}에 들어서는 부동산분양 현장입니다. "
          f"본 현장은 {cat_alt} 카테고리에 속하며, 시공·시행은 {dev}이 맡았습니다. "
          f"규모는 {units}, 평형은 {sizes}로 구성됩니다. "
          f"분양가는 {price}이며 일정은 {sched} 기준입니다. "
          f"부동산분양 시장에서 동일 권역 다른 현장과 비교했을 때, "
          f"{name}의 핵심 포인트는 {hl[0] if hl else '입지'}입니다.")

    p2 = ("입지 측면에서 본 단지의 강점은 다음과 같습니다. " +
          " ".join([f"{i+1}) {pt}." for i, pt in enumerate(hl[:4])]) +
          f" 이러한 요소가 결합되어 {region} 권역 내 {cat_alt} 현장 중에서도 "
          f"중장기적인 자산 가치 보전에 유리한 조건을 갖췄다고 평가됩니다. "
          f"부동산분양 정보를 검토하실 때 입지·교통·배후수요·정비계획 4가지 축을 기준으로 비교해 보시기 바랍니다.")

    p3_apart = (f"청약 전략 측면에서 {name}은(는) 가점제 비중과 특별공급 자격을 우선 확인해야 합니다. "
                f"부동산분양 시장에서 자금 계획은 분양가 {price} 기준으로 자기자금·중도금·잔금을 단계별로 수립하시고, "
                f"입주자모집공고문에 명시된 거주지 우선공급·재당첨 제한 조건을 반드시 확인하세요. "
                f"청약홈에서 최신 공고를 확인하시고, 견본주택 방문·현장 임장은 모집공고 이후 진행하시는 것이 안전합니다.")
    p3_off = (f"{name}은(는) 주거형 오피스텔 특성상 주택수 포함 여부, 임대수익률, 공실률을 가장 먼저 점검해야 합니다. "
              f"부동산분양 정보 검토 시 {region} 권역의 임대 시세와 신축 공급 물량을 비교한 뒤, "
              f"본 단지 {sizes} 평형별 예상 월세·전세 시세를 산출해 보세요. 분양가 {price} 대비 연 임대수익률이 4% 이상이라면 "
              f"투자형, 그 이하는 실거주형으로 접근하시는 것이 합리적입니다.")
    p3_store = (f"단지내·근린상가 투자에서 중요한 변수는 배후세대수와 유동인구입니다. {name}의 경우 "
                f"{units}의 배후 수요가 형성되어 있으며, {hl[0] if hl else '핵심 입지'}로 1층 노출이 강합니다. "
                f"부동산분양 정보를 비교하실 때 호실별 분양가 {price}와 예상 임대료를 비교해 임대수익률(연 4~6%)을 산출하시고, "
                f"업종 제한·관리비·재산세 조건을 모집공고문에서 반드시 확인하세요.")
    p3_kc = (f"본 현장 투자에서는 입주 가능 업종, 취득세 감면(50%) 조건, 임대 가능 시점을 가장 먼저 봐야 합니다. "
             f"{name}은 {dev}이 공급하며 {sizes} 호실 구성으로 {price} 수준입니다. "
             f"{region} 권역의 기존 공장형 오피스 임대 시세와 비교하고, "
             f"입주 업종 코드(제조·연구·정보통신 등)에 본인 업종이 포함되는지 확인하세요. "
             f"부동산분양 정보 비교 시에는 분양가, 임대료, 공실률, 세제 혜택을 종합 점검하시기 바랍니다.")
    sizes_clean = re.sub(r"^필지별\s*", "", sizes)
    price_clean = re.sub(r"공급가\s*[—-]\s*", "", price)
    p3_land = (f"토지 매입 시에는 용도지역·건폐율·용적률·건축 가능 용도를 첫 단계에서 확인해야 합니다. "
               f"{name}은 {units}, 필지 규모는 {sizes_clean}이며 공급 조건은 {price_clean}입니다. "
               f"단독주택용지·점포겸용용지·근린생활시설용지 등 용도별로 활용 시나리오가 달라지므로, "
               f"입찰 또는 추첨 방식과 공급 조건(잔금 일정·전매 제한)을 모집공고에서 점검하세요. "
               f"부동산분양 정보 비교는 필지 규모·도로 접도 조건·인접 호재를 종합해 판단하시기 바랍니다.")
    p3_ind = (f"산업 용지 분양은 입주 자격(업종·기업 규모), 공급가, 사용 시점이 핵심입니다. "
              f"{name}은 {region}에 조성되며 총 {units} 규모입니다. 공급가는 {price}이며 "
              f"공급 일정은 {sched}입니다. 지자체 입주 우선권·세제 혜택·인근 클러스터와의 연계 효과를 "
              f"종합 검토한 뒤 신청하시기 바랍니다. 부동산분양 정보 비교 시에는 클러스터 안정성·물류 동선·진입 도로를 확인하세요.")

    p3 = {"apartment": p3_apart, "officetel": p3_off, "store": p3_store,
          "knowledge-center": p3_kc, "land": p3_land, "industrial": p3_ind}[cat]

    # p4 — additional market context (no sub-keyword) to lower density and add depth
    p4_map = {
        "apartment": (
            f"{region} 권역의 주거 시장은 정비사업 진척도, 광역교통망 확충 일정, 학군 변동에 따라 가격이 움직입니다. "
            f"입주 시점의 금리·전세시세·신축 공급량을 미리 모니터링하시고, 청약 이후 잔금 시점 자금 흐름표를 작성해 두시기를 권합니다. "
            f"실거주가 목적이라면 입주 직후 1년 시세 흐름이, 투자 목적이라면 3~5년 전매·증여 시점 시세 전망이 의사결정의 핵심 변수가 됩니다."
        ),
        "officetel": (
            f"{region} 권역의 임대 시장은 신축 공급, 직장 수요, 1인가구 비율에 따라 변동합니다. "
            f"분양 후 임대까지의 공실 리스크, 관리비 수준, 주차·엘리베이터 대수, 보안 수준이 임대료에 직접 영향을 줍니다. "
            f"수익형으로 접근하실 경우 취득세·재산세·종부세 합산 시뮬레이션을 사전에 실행해 보시기 바랍니다."
        ),
        "store": (
            f"단지내·근린 상권의 안정성은 입주민의 동선과 매출 잠재력에 좌우됩니다. "
            f"상권 형성 초기에는 임대료 협상력이 임차인 측에 있으므로, 입점 시점·MD 구성·고정 임차 보장 조건을 모집공고와 함께 확인하시기 바랍니다. "
            f"인근 대형 마트·편의점 출점 계획도 임대수익률에 영향을 줍니다."
        ),
        "knowledge-center": (
            f"본 단지의 입주 매력도는 입주 가능 업종 폭, 주차 비율, 화물 엘리베이터 사양, 천장 높이, 바닥 적재하중에 따라 좌우됩니다. "
            f"제조형·연구형·정보통신형 업종별 요구 스펙이 다르므로 본인 업종에 맞는 호실인지 모집공고와 평면도를 함께 확인해 보세요. "
            f"인근 임대 시세와 분양가 차이가 작을수록 자가 사용·임대 모두 유리합니다."
        ),
        "land": (
            f"본 필지의 진입 도로 폭, 접도 길이, 지목 변경 가능성은 향후 건축 인허가에 직결됩니다. "
            f"점포겸용은 1층 매출 잠재력이 핵심이며, 단독형은 일조·조망·이웃 필지 용도가 자산 가치에 영향을 줍니다. "
            f"매입 후 건축 인허가 일정을 미리 짜두시는 것이 유리합니다."
        ),
        "industrial": (
            f"본 산단의 입지 가치는 고속도로 IC 접근성, 항만·공항 접근성, 인근 클러스터의 폐쇄성·확장성에 따라 결정됩니다. "
            f"입주 자격(업종 코드)에 부합하는지 사전 확인하시고, 임차·자가 비중과 회계 처리 방식을 비교한 뒤 신청하시기 바랍니다. "
            f"용지 양도·임대 제한 기간도 모집공고문에서 반드시 확인하세요."
        ),
    }
    p4 = p4_map[cat]

    # ---- stats ----
    stats = [
        ("규모", units),
        ("평형/면적", sizes),
        ("분양가", price),
        ("일정", sched),
    ]
    stats_html = "".join(
        f'<div class="stat-item"><div class="stat-num">{v}</div><div class="stat-label">{k}</div></div>'
        for k, v in stats
    )

    # category row uses 'cat_alt' phrasing (e.g. "지산 분양") to keep sub-keyword
    # repetition under the 3.0% stuffing threshold. Title/breadcrumb still use
    # the canonical label.
    info_rows = [
        ("현장명", name),
        ("위치", region),
        ("시공·시행", dev),
        ("규모", units),
        ("평형/면적", sizes),
        ("분양가", price),
        ("일정", sched),
        ("카테고리", cat_alt),
    ]
    info_html = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in info_rows)

    highlights_html = "".join(f"<li>{h}</li>" for h in hl)

    # ---- FAQ — generated from facts ----
    faqs = [
        (f"{name} 분양 일정은 언제인가?",
         f"{sched} 기준입니다. 최신 일정은 청약홈(applyhome.co.kr) 또는 모집공고문을 확인하시기 바랍니다."),
        (f"{name} 분양가는 얼마인가?",
         f"분양가는 {price}이며, 평형/호실별로 차이가 있습니다. 모집공고문 발표 시점의 가격이 확정 분양가입니다."),
        (f"{name} 시공·시행사는?",
         f"{dev}이 담당합니다."),
        (f"{name} 규모와 평형은?",
         f"전체 규모는 {units}이며, 평형 구성은 {sizes}입니다."),
        (f"{name} 청약 자격 요건은?",
         f"일반 분양 청약 자격에 준합니다. 거주지 우선공급·자격 요건은 청약홈 모집공고문에서 정확히 확인하세요."),
    ]
    faq_html = "".join(
        f'<div class="faq-item"><div class="faq-q">{q}<span class="arrow">▼</span></div>'
        f'<div class="faq-a"><div class="faq-a-inner">{a}</div></div></div>'
        for q, a in faqs
    )

    # ---- JSON-LD ----
    jsonld = json.dumps({
        "@context": "https://schema.org",
        "@type": "RealEstateAgent",
        "name": f"더에셋스퀘어 — {name}",
        "description": f"{name} {info['label']} 전문 분석",
        "url": canonical,
        "areaServed": region,
    }, ensure_ascii=False)

    cb = int(dt.datetime(2026, 6, 1).timestamp() * 1000)
    html = f"""<!--cb:{cb}-->
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="theme-color" content="#2563eb">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <link rel="canonical" href="{canonical}">
  <link rel="icon" href="/favicon.ico" sizes="32x32">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{desc[:140]}">
  <meta property="og:type" content="article">
  <meta property="og:image" content="{SITE}/og-home.png">
  <meta property="og:url" content="{canonical}">
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
<header class="site-header"><div class="header-inner"><a href="/" class="logo" target="_blank" rel="noopener noreferrer">더에셋<span>스퀘어</span></a><nav class="nav-links"><a href="/apartment.html" target="_blank" rel="noopener noreferrer">아파트</a><a href="/officetel.html" target="_blank" rel="noopener noreferrer">오피스텔</a><a href="/store.html" target="_blank" rel="noopener noreferrer">상가</a><a href="/knowledge-center.html" target="_blank" rel="noopener noreferrer">지식산업센터</a><a href="/land.html" target="_blank" rel="noopener noreferrer">토지</a><a href="/industrial.html" target="_blank" rel="noopener noreferrer">산업단지</a></nav><button class="hamburger" aria-label="메뉴" aria-expanded="false">☰</button></div></header>

<main id="main-content">
<div class="breadcrumb"><a href="/" target="_blank" rel="noopener noreferrer">홈</a><span>›</span><a href="{info['page']}" target="_blank" rel="noopener noreferrer">{info['label']}</a><span>›</span>{name}</div>

<section class="detail-hero"><div class="container">
  <h1>{name}</h1>
  <p class="subtitle">{region} · {dev} · {info['label']}</p>
</div></section>

<div class="detail-content">
  <div class="stats-bar">{stats_html}</div>

  <h2>{name} 분양 개요</h2>
  <table class="info-table">{info_html}</table>

  <h2>{name} 분양 정보·분석</h2>
  <p>{p1}</p>
  <p>{p2}</p>

  <h2>{name} 핵심 포인트</h2>
  <ul class="highlight-list">{highlights_html}</ul>

  <h2>부동산분양 청약·투자 전략</h2>
  <p>{p3}</p>
  <p>{p4}</p>

  <h2>자주 묻는 질문</h2>
  <div class="faq-list">{faq_html}</div>

  <div class="alert-teaser">
    <h3>{name} 분양 정보 더 자세히 확인하기</h3>
    <p>청약 결과, 분양가 변동, 계약 일정은 더에셋스퀘어 본 사이트에서 실시간 업데이트됩니다.</p>
    <a href="https://theassetsquare.com/" target="_blank" rel="noopener">더에셋스퀘어 본 사이트에서 확인 →</a>
  </div>
</div>
</main>

<footer class="site-footer"><p>© 2026 더에셋스퀘어. 부동산분양 전문 정보 플랫폼.</p><p>분양 데이터 기준: {TODAY.isoformat()}</p></footer>

<script defer src="/main.js?v={CSS_VER}"></script>
<div style="position:fixed;bottom:0;left:0;width:100%;height:48px;background:#2563EB;display:flex;align-items:center;justify-content:center;z-index:9999">
<a href="https://theassetsquare.com/" target="_blank" rel="noopener noreferrer" style="color:#fff;font-size:16px;font-weight:700;text-decoration:none">더에셋스퀘어에서 더 보기 →</a>
</div>
<div style="height:48px"></div>
</body>
</html>
"""
    return html


def keyword_density(html, keyword):
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    words = text.split()
    cnt = sum(1 for _ in re.finditer(re.escape(keyword), text))
    return cnt, len(words), (cnt * 100.0 / max(1, len(words)))


def main():
    with open(DATA, encoding="utf-8") as f:
        entries = json.load(f)
    created = []
    for i, e in enumerate(entries):
        slug = e["slug"]
        path = os.path.join(ROOT, "property", f"{slug}.html")
        if os.path.exists(path):
            print(f"skip (exists): {slug}")
            continue
        html = make_html(i, e)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        # quick density check on the primary keyword
        cnt_p, words, pct_p = keyword_density(html, "부동산분양")
        cnt_s, _, pct_s = keyword_density(html, CAT[e["category"]]["kw"])
        print(f"  {slug}: {words}w · 부동산분양 {cnt_p}/{pct_p:.2f}% · {CAT[e['category']]['kw']} {cnt_s}/{pct_s:.2f}%")
        created.append((slug, e["category"]))
    print(f"\nCreated {len(created)} pages")
    return created


if __name__ == "__main__":
    main()
