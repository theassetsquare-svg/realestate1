/**
 * 형제 사이트(k·m·n)와 겹치는 본문 문장을 l 원고에서 걷어낸다.
 *
 * 왜 필요한가
 *   네 사이트가 같은 40곳을 다루니 표현이 겹치기 쉽다. 한 페이지가 다른 사이트와
 *   세 문장만 같아도 네이버는 유사문서로 보고 한쪽을 검색에서 뺀다.
 *   그러면 40개를 만들어 놓고 절반이 버려진다.
 *
 * 무엇을 하나
 *   k·m·n 의 만들어진 페이지에서 문장을 전부 모으고, l 원고의 **구역 본문**에서
 *   같은 문장을 지운다. 핵심 줄·note·FAQ·요약처럼 구조가 걸린 자리는 목록으로 알려만 준다.
 *
 *   node tools/night/dedupe-sib.mjs          무엇을 지울지 보여만 준다
 *   node tools/night/dedupe-sib.mjs --apply  실제로 지운다
 */
import fs from 'node:fs';
import path from 'node:path';

const DIR = path.resolve('D:/naver-watch/repos/realestate1/tools/night/content');
const APPLY = process.argv.includes('--apply');
const SIBS = ['D:/naver-watch/repos/realestate', 'D:/naver-watch/repos/realestate2', 'D:/naver-watch/repos/realestate3'];

const strip = (h) => h
  .replace(/<script[\s\S]*?<\/script>/gi, ' ').replace(/<style[\s\S]*?<\/style>/gi, ' ')
  .replace(/<table[\s\S]*?<\/table>/gi, ' ').replace(/<[^>]+>/g, ' ')
  .replace(/&[a-z]+;/g, ' ').replace(/\s+/g, ' ');
const split = (s) => String(s).split(/(?<=[.!?])\s+/).map((x) => x.trim()).filter((x) => x.length >= 20);

const sib = new Set();
for (const root of SIBS) {
  for (let i = 1; i <= 40; i++) {
    const p = path.join(root, String(i), 'index.html');
    if (!fs.existsSync(p)) continue;
    split(strip(fs.readFileSync(p, 'utf8'))).forEach((s) => sib.add(s));
  }
}
console.log(`형제 사이트 문장 ${sib.size}개를 대조 기준으로 삼는다`);

const pathToUrl = (p) => 'file:///' + p.replace(/\\/g, '/');
const manual = [];
let removed = 0, touched = 0;

for (let n = 1; n <= 40; n++) {
  const file = path.join(DIR, `${n}.mjs`);
  if (!fs.existsSync(file)) continue;
  const c = (await import(pathToUrl(file) + `?v=${n}-${Math.floor(process.hrtime()[1] / 1e3)}`)).default;

  const drop = new Set();
  const check = (s, where) => {
    if (!sib.has(s)) return;
    if (where === 'body') drop.add(s);
    else manual.push({ n, where, s });
  };
  c.lead.forEach((p) => split(p).forEach((s) => check(s, 'lead')));
  c.answer3.forEach((p) => split(p).forEach((s) => check(s, 'answer3')));
  c.sections.forEach((sec) => {
    sec.body.forEach((p) => split(p).forEach((s) => check(s, 'body')));
    if (sec.note) split(sec.note).forEach((s) => check(s, 'note'));
    split(sec.h2).forEach((s) => check(s, 'h2'));
  });
  c.reveal.forEach((p) => split(p).forEach((s) => check(s, 'reveal')));
  split(c.action).forEach((s) => check(s, 'action'));
  c.faq.forEach((f) => { split(f.q).forEach((s) => check(s, 'faq')); split(f.a).forEach((s) => check(s, 'faq')); });
  split(c.summary).forEach((s) => check(s, 'summary'));

  if (!drop.size) continue;
  let src = fs.readFileSync(file, 'utf8');
  let hit = 0;
  for (const s of drop) {
    const esc = s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const whole = new RegExp(`^\\s*'${esc}',\\n`, 'm');
    if (whole.test(src)) { src = src.replace(whole, ''); hit++; continue; }
    const inside = new RegExp(`(${esc})\\s?`);
    if (inside.test(src)) { src = src.replace(inside, ''); hit++; continue; }
    console.log(`  ? ${n}.mjs 에서 못 지움: ${s.slice(0, 28)}…`);
  }
  if (hit) { touched++; removed += hit; if (APPLY) fs.writeFileSync(file, src, 'utf8'); }
}

console.log(`본문에서 지울 문장 ${removed}개 (${touched}개 파일)`);
if (manual.length) {
  console.log(`\n사람이 표현을 바꿔야 하는 자리 ${manual.length}건:`);
  for (const m of manual) console.log(`  ${m.n}.mjs [${m.where}] : ${m.s}`);
}
if (!APPLY) console.log('\n실제로 지우려면 --apply 를 붙인다');
