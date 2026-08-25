/**
 * 2차 걷어내기 — 페이지끼리 겹치는 **본문 문장 전부**를 원고에서 지운다.
 *
 * 왜 또 필요한가
 *   dedupe.mjs 는 안내 성격 문장만 지운다(확인·방침·자료 …).
 *   그런데 같은 앵글을 쓰는 페이지끼리는 내용 문장도 표현이 겹친다.
 *   한 쌍에 세 문장만 겹쳐도 검문 G5 가 막고, 네이버는 유사문서로 보고 한쪽을 버린다.
 *
 * 무엇을 하나
 *   두 파일 이상에 똑같이 들어간 20자 이상 문장을 찾아, 가장 앞 번호 파일에만 남기고
 *   나머지 파일의 **구역 본문(body)** 에서만 지운다.
 *   핵심 줄(answer3)·note·FAQ·요약·제목은 건드리지 않고 목록으로 알려만 준다.
 *   구조가 걸린 자리는 사람이 표현을 바꿔야 하기 때문이다.
 *
 *   node tools/night/dedupe2.mjs          무엇을 지울지 보여만 준다
 *   node tools/night/dedupe2.mjs --apply  실제로 지운다
 */
import fs from 'node:fs';
import path from 'node:path';

const DIR = path.resolve('D:/naver-watch/repos/realestate1/tools/night/content');
const APPLY = process.argv.includes('--apply');

const nums = fs.readdirSync(DIR).filter((f) => f.endsWith('.mjs'))
  .map((f) => Number(path.basename(f, '.mjs'))).filter(Number.isFinite).sort((a, b) => a - b);

const load = async (n) => (await import(pathToUrl(path.join(DIR, `${n}.mjs`)) + `?v=${Date.now()}`)).default;
function pathToUrl(p) { return 'file:///' + p.replace(/\\/g, '/'); }

const split = (s) => String(s).split(/(?<=[.!?])\s+/).map((x) => x.trim()).filter((x) => x.length >= 20);

/* 문장 → 처음 나온 페이지 번호 */
const first = new Map();
/* 페이지 → 그 페이지에서 지워야 할 문장들 */
const toDrop = new Map();
/* 구조가 걸려 사람이 손봐야 하는 자리 */
const manual = [];

for (const n of nums) {
  const c = await load(n);
  const seenHere = new Set();
  const note = (s, where) => {
    if (seenHere.has(s)) return;
    seenHere.add(s);
    if (!first.has(s)) { first.set(s, n); return; }
    if (first.get(s) === n) return;
    if (where === 'body') {
      if (!toDrop.has(n)) toDrop.set(n, new Set());
      toDrop.get(n).add(s);
    } else {
      manual.push({ n, where, s, firstAt: first.get(s) });
    }
  };
  c.lead.forEach((p) => split(p).forEach((s) => note(s, 'lead')));
  c.answer3.forEach((p) => split(p).forEach((s) => note(s, 'answer3')));
  c.sections.forEach((sec) => {
    sec.body.forEach((p) => split(p).forEach((s) => note(s, 'body')));
    if (sec.note) split(sec.note).forEach((s) => note(s, 'note'));
    split(sec.h2).forEach((s) => note(s, 'h2'));
  });
  c.reveal.forEach((p) => split(p).forEach((s) => note(s, 'reveal')));
  split(c.action).forEach((s) => note(s, 'action'));
  c.faq.forEach((f) => { split(f.q).forEach((s) => note(s, 'faq')); split(f.a).forEach((s) => note(s, 'faq')); });
  split(c.summary).forEach((s) => note(s, 'summary'));
}

/* 지우기 — body 안의 문장만 손댄다 */
let removed = 0, filesTouched = 0;
for (const [n, set] of [...toDrop].sort((a, b) => a[0] - b[0])) {
  const p = path.join(DIR, `${n}.mjs`);
  let src = fs.readFileSync(p, 'utf8');
  let hit = 0;
  for (const s of set) {
    const esc = s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    /* 문단 전체가 그 문장이면 줄째로 지운다 */
    const whole = new RegExp(`^\\s*'${esc}',\\n`, 'm');
    if (whole.test(src)) { src = src.replace(whole, ''); hit++; continue; }
    /* 문단 안의 한 문장이면 그 문장만 뺀다 */
    const inside = new RegExp(`(${esc})\\s?`);
    if (inside.test(src)) { src = src.replace(inside, ''); hit++; continue; }
    console.log(`  ? ${n}.mjs 에서 못 지움: ${s.slice(0, 28)}…`);
  }
  if (hit) { filesTouched++; removed += hit; if (APPLY) fs.writeFileSync(p, src, 'utf8'); }
}

console.log(`본문에서 지울 문장 ${removed}개 (${filesTouched}개 파일)`);
if (manual.length) {
  console.log(`\n사람이 표현을 바꿔야 하는 자리 ${manual.length}건:`);
  for (const m of manual) console.log(`  ${m.n}.mjs [${m.where}] ← ${m.firstAt}.mjs : ${m.s}`);
}
if (!APPLY) console.log('\n실제로 지우려면 --apply 를 붙인다');
