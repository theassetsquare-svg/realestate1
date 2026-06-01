#!/usr/bin/env python3
"""Insert new property cards into each category page.

Adds a new <section> "2026년 6월 신규" right after the page hero search bar,
so the new listings surface first. Each card links to property/<slug>.html.
Idempotent: re-running skips slugs already present on the page.
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "tools", "data", "new_listings_2026-06.json")

CAT_FILE = {
    "apartment": "apartment.html",
    "officetel": "officetel.html",
    "store": "store.html",
    "knowledge-center": "knowledge-center.html",
    "land": "land.html",
    "industrial": "industrial.html",
}

ICON = {
    "apartment": "🏢", "officetel": "🏬", "store": "🛒",
    "knowledge-center": "🏭", "land": "🌳", "industrial": "🏗",
}

CAT_LABEL = {
    "apartment": "아파트분양", "officetel": "오피스텔분양", "store": "상가분양",
    "knowledge-center": "지식산업센터", "land": "토지분양", "industrial": "산업단지분양",
}


def card_html(e):
    cat = e["category"]
    name = e["name_ko"]
    region = e["region"]
    dev = e["developer"]
    info_bits = [b for b in [e.get("total_units"), e.get("size_range"), e.get("schedule")] if b and b != "미정"][:3]
    info_html = "".join(f"<span>{b}</span>" for b in info_bits)
    return (
        f'    <a href="/property/{e["slug"]}.html" class="prop-card" target="_blank" rel="noopener noreferrer">\n'
        f'      <div class="prop-thumb">{ICON[cat]}</div>\n'
        f'      <div class="prop-body">\n'
        f'        <span class="prop-badge hot">2026.06 신규</span>\n'
        f'        <h3 class="prop-name">{name}</h3>\n'
        f'        <p class="prop-location">{region} · {dev}</p>\n'
        f'        <div class="prop-info">{info_html}</div>\n'
        f'      </div>\n'
        f'    </a>\n'
    )


def inject_section(html, cards, cat):
    """Insert new <section> directly after the search-wrap div."""
    title = f"2026년 6월 신규 — {CAT_LABEL[cat]}"
    sub = f"청약홈·LH·뉴스 공식 정보 기반 {CAT_LABEL[cat]} 신규 현장"
    block = (
        '\n<section class="section">\n'
        f'  <h2 class="section-title">{title}</h2>\n'
        f'  <p class="section-sub">{sub}</p>\n'
        '  <div class="prop-grid">\n\n'
        + "\n".join(cards) +
        '\n  </div>\n'
        '</section>\n'
    )
    new_html, n = re.subn(
        r'(</div>\s*</div>\s*</div>\s*)(?=\s*<section)',
        r'\1' + block,
        html, count=1, flags=re.DOTALL,
    )
    if n == 0:
        # fallback — insert after first </header>
        new_html, n = re.subn(
            r'(</section>\s*<div class="search-wrap">.*?</div>\s*</div>)',
            r'\1' + block, html, count=1, flags=re.DOTALL,
        )
    if n == 0:
        # final fallback — after first <main ...>
        new_html, n = re.subn(
            r'(<main\b[^>]*>)',
            r'\1' + block, html, count=1,
        )
    return new_html, n


def main():
    entries = json.load(open(DATA, encoding="utf-8"))
    by_cat = {}
    for e in entries:
        by_cat.setdefault(e["category"], []).append(e)

    for cat, items in by_cat.items():
        path = os.path.join(ROOT, CAT_FILE[cat])
        s = open(path, encoding="utf-8").read()
        new_cards = []
        for e in items:
            if f'/property/{e["slug"]}.html' in s:
                continue
            new_cards.append(card_html(e))
        if not new_cards:
            print(f"{cat}: nothing to add")
            continue
        s2, n = inject_section(s, new_cards, cat)
        if n == 0:
            print(f"{cat}: ⚠ no injection point matched")
            continue
        open(path, "w", encoding="utf-8").write(s2)
        print(f"{cat}: +{len(new_cards)} cards → {CAT_FILE[cat]}")


if __name__ == "__main__":
    main()
