/**
 * l 보정 1차 — dedupe 가 지운 FAQ 답 복구 + FAQ 질문 유일화
 *   node tools/night/fix-l.mjs --apply
 */
import fs from 'node:fs';
import path from 'node:path';

const DIR = path.resolve('D:/naver-watch/repos/realestate1/tools/night/content');
const APPLY = process.argv.includes('--apply');

const EDITS = [
  /* dedupe 가 통째로 비워 버린 답 */
  [14, "{ q: '가방을 맡길 수 있나요?', a: '' }", "{ q: '가방을 맡길 수 있나요?', a: '맡기는 방식은 매장이 정하는 부분이라 미리 여쭤보시는 편이 확실합니다.' }"],

  /* 너무 짧게 잘린 답 늘리기 */
  [12, "a: '의정부중앙역이 가장 가깝습니다.'", "a: '의정부중앙역이 가장 가깝습니다. 몇 분 거리인지까지는 공개 자료로 특정하지 못했습니다.'"],
  [12, "a: '깔끔한 정도면 충분한 편입니다.'", "a: '깔끔한 정도면 충분한 편입니다. 오래 서 있어도 괜찮은 신발이 더 중요합니다.'"],
  [13, "a: '의정부중앙역 방면입니다.'", "a: '의정부중앙역 방면입니다. 엘마트라는 건물 이름을 기준으로 삼으시면 빠릅니다.'"],
  [16, "a: '고양시 일산동구 마두동입니다.'", "a: '고양시 일산동구 마두동입니다. 마두역 8번 출구가 기준점이 됩니다.'"],
  [17, "a: '모란역 생활권 안쪽입니다.'", "a: '모란역 생활권 안쪽입니다. 오가는 길에 자연스럽게 걸리는 자리입니다.'"],
  [22, "a: '상록수역이 가장 가깝습니다.'", "a: '상록수역이 가장 가깝습니다. 걸리는 시간은 자료로 특정하지 못했습니다.'"],
  [23, "a: '신중동역 인근입니다.'", "a: '신중동역 인근입니다. 정확히 몇 분인지는 공개 자료에서 찾지 못했습니다.'"],
  [27, "a: '쌍용(나사렛대)역입니다.'", "a: '쌍용(나사렛대)역입니다. 도보 시간은 공개 자료로 특정하지 못했습니다.'"],

  /* FAQ 질문 겹침 */
  [14, "q: '건물 어디에 있나요?'", "q: '은산빌딩 어느 층인가요?'"],
  [24, "q: '몇 개 층을 쓰나요?'", "q: '맘모스빌딩 몇 개 층인가요?'"],
  [27, "q: '새벽에 이동이 되나요?'", "q: '쌍용동에서 새벽에 움직일 수 있나요?'"],
  [28, "q: '다른 도시에 같은 이름이 있나요?'", "q: '청주 말고 다른 곳에도 같은 이름이 있나요?'"],
  [31, "q: '큰길에서 들어가야 하나요?'", "q: '당디로에서 안으로 들어가야 하나요?'"],
  [39, "q: '언제 사람이 많나요?'", "q: '월계동 쪽은 언제 붐비나요?'"],
];

const files = new Map();
const read = (no) => {
  if (!files.has(no)) files.set(no, fs.readFileSync(path.join(DIR, `${no}.mjs`), 'utf8'));
  return files.get(no);
};

let n = 0, miss = 0;
for (const [no, from, to] of EDITS) {
  const src = read(no);
  if (!src.includes(from)) { console.log(`★ ${no}.mjs 에서 못 찾음: ${from.slice(0, 40)}…`); miss++; continue; }
  files.set(no, src.replace(from, to));
  n++;
}
if (APPLY) for (const [no, src] of files) fs.writeFileSync(path.join(DIR, `${no}.mjs`), src, 'utf8');
console.log(`고친 곳 ${n}개 / 못 찾은 것 ${miss}개${APPLY ? ' — 저장함' : ' (--apply 필요)'}`);
