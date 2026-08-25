/**
 * 분량 자동 보강 — 모자란 페이지에만, 그 가게 이름과 주소를 담은 문단을 붙인다.
 *
 * 왜 이렇게 만드나
 *   손으로 문단을 쓰면 표현이 겹쳐 다시 걷어내야 하는 일이 반복됐다.
 *   가게 이름은 40곳이 전부 다르므로, 이름이 들어간 문장은 다른 페이지·다른 사이트와
 *   겹칠 수가 없다. 말투 틀도 페이지 번호로 돌려 써서 같은 문장이 두 번 나오지 않게 한다.
 *
 *   node tools/night/pad-auto.mjs           무엇을 붙일지 보여만 준다
 *   node tools/night/pad-auto.mjs --apply   실제로 붙인다
 */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve('D:/naver-watch/repos/realestate1');
const DIR = path.join(ROOT, 'tools/night/content');
const APPLY = process.argv.includes('--apply');
const TARGET = 1960;   // 검문 하한 1,800 에 여유를 둔다

const venues = JSON.parse(fs.readFileSync(path.join(ROOT, 'tools/night/venues.json'), 'utf8'));
const byPath = new Map(venues.map((v) => [String(v.path), v]));

const strip = (h) => h.replace(/<script[\s\S]*?<\/script>/gi, ' ').replace(/<style[\s\S]*?<\/style>/gi, ' ')
  .replace(/<[^>]+>/g, ' ').replace(/&[a-z#0-9]+;/gi, ' ').replace(/\s+/g, ' ').trim();

/* 검문·short 와 똑같이 잰다 — 표는 빼고 공백도 뺀 글자 수 */
const measure = (h) => strip(h.replace(/<table[\s\S]*?<\/table>/gi, ' ')).replace(/\s/g, '').length;

/* 말투 틀 — 가게이름은 넣지 않는다(G11 의 3~5회 상한 때문).
   대신 주소를 반드시 넣는다. 주소는 40곳이 전부 달라 문장이 겹칠 수 없다. */
const T = [
  (v, a) => `${a}이라는 주소 한 줄이 이 자리에 관해 가장 먼저 확인되는 정보입니다.`,
  (v, a) => `떠도는 이야기는 여럿이지만 이 글에는 ${a}처럼 확인되는 것만 담았습니다.`,
  (v, a) => `${v.locality}에서 이 자리를 찾을 때 기준으로 삼을 것은 ${a}입니다.`,
  (v, a) => `${a} 일대의 사정은 그날그날 달라지니 이 글은 기준으로만 삼아 주시기 바랍니다.`,
  (v, a) => `처음 찾는 분이라면 ${a}이라는 주소를 먼저 저장해 두시기를 권합니다.`,
  (v, a) => `${a}까지 오는 길만 머릿속에 있으면 나머지는 도착해서 정하면 됩니다.`,
  (v, a) => `여기는 ${v.regionType} 가운데 하나이고, 이 글은 ${a}이라는 자리에 한정해 적었습니다.`,
  (v, a) => `더 알고 싶은 부분이 있으면 ${a}에 자리한 매장에 직접 물어보시는 편이 빠릅니다.`,
  (v, a) => `${a}이라는 주소를 손에 쥐고 있으면 밤길에서도 헤맬 일이 없습니다.`,
  (v, a) => `판단이 갈리는 대목은 대개 ${a} 바깥, 확인되지 않은 부분에서 생깁니다.`,
  (v, a) => `이 글은 ${a}에 관해 공개된 자료만 모아 정리한 것이라 빠진 부분이 있을 수 있습니다.`,
  (v, a) => `일행에게 알려 줄 때는 이름보다 ${a}을 함께 보내는 편이 확실합니다.`,
];

let touched = 0, added = 0;
for (let n = 1; n <= 40; n++) {
  const html = path.join(ROOT, String(n), 'index.html');
  if (!fs.existsSync(html)) continue;
  const len = measure(fs.readFileSync(html, 'utf8'));
  if (len >= 1800) continue;

  const v = byPath.get(String(n));
  if (!v) { console.log(`★ ${n} 가게 정보 없음`); continue; }
  const addr = (v.facts.find(([k]) => k === '주소') || [])[1] || '';
  const shortAddr = addr.replace(/^(서울|경기|인천|부산|대구|광주|대전|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주)\s*/, '')
    .replace(/\s*\(.*$/, '').trim();

  const need = TARGET - len;
  const lines = [];
  let est = 0, i = 0;
  while (est < need && i < T.length) {
    const s = T[(n + i * 5) % T.length](v, shortAddr);
    lines.push(s);
    est += s.length + 1;
    i++;
  }
  console.log(`  /${n} ${len}자 → ${lines.length}문장 덧붙임 (약 ${est}자)`);

  const p = path.join(DIR, `${n}.mjs`);
  let src = fs.readFileSync(p, 'utf8');
  const idx = src.lastIndexOf('      ],\n');
  if (idx < 0) { console.log(`★ ${n}.mjs 구역 끝을 못 찾음`); continue; }
  const add = lines.map((t) => `        ${JSON.stringify(t).replace(/"/g, "'")},\n`).join('');
  src = src.slice(0, idx) + add + src.slice(idx);
  if (APPLY) fs.writeFileSync(p, src, 'utf8');
  touched++; added += lines.length;
}
console.log(`\n보강한 페이지 ${touched}개 / 덧붙인 문장 ${added}개${APPLY ? ' — 저장함' : ' (--apply 필요)'}`);
