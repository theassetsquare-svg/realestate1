import fs from 'node:fs';
import path from 'node:path';
const DIR = path.resolve('D:/naver-watch/repos/realestate1/tools/night/content');
const EDITS = [
  [17, '왜 그런지는 이 글 아래쪽에서 풀어 두겠습니다.', '그 까닭은 이 글 뒤쪽에서 짚어 두겠습니다.'],
  [18, '어느 쪽을 골라야 하는지는 이 글 아래쪽에서 풀어 두겠습니다.', '어느 쪽이 맞는지는 이 글 뒤쪽에서 짚어 두겠습니다.'],
  [25, '무엇이 그렇게 만들었는지는 이 글 아래쪽에서 풀어 두겠습니다.', '무엇이 그 습관을 만들었는지는 이 글 끝에서 밝혀 두겠습니다.'],
  [31, "a: '당디로변에서 한 번 들어가는 자리입니다. 번지를 기준으로 잡으시면 어렵지 않습니다.'", "a: '당디로변에서 한 번 들어가는 자리입니다. 번지를 손에 쥐고 가시면 헤맬 일이 없습니다.'"],
  [33, '밖에서 안을 읽을 수 있다는 것은 이 구역이 가진 드문 이점입니다.', '밖을 보고 안을 가늠할 수 있다는 것은 이런 구역에서만 가능한 일입니다.'],
  [34, '왜 그런지는 이 글 아래쪽에서 풀어 두겠습니다.', '어째서 그런지는 이 글 뒤쪽에서 짚어 두겠습니다.'],
  [36, '어느 쪽이 나은지는 이 글 아래쪽에서 풀어 두겠습니다.', '어느 쪽이 나은 선택인지는 이 글 끝에서 밝혀 두겠습니다.'],
  [36, '그러면 그날 본 것이 그대로 남습니다.', '그러면 그날 눈으로 본 것만 기억에 남습니다.'],
  [37, '무엇을 안 했길래 그랬는지는 이 글 아래쪽에서 풀어 두겠습니다.', '무엇을 빠뜨렸길래 그랬는지는 이 글 끝에서 밝혀 두겠습니다.'],
  [38, "note: '신분증 · 돌아올 방법 · 주머니에 들어갈 것'", "note: '신분증과 돌아올 방법, 그리고 주머니에 들어가는 것'"],
  [39, "note: '먼저 가서 자리를 잡고 일행을 뒤로 부른다'", "note: '자리를 먼저 잡아 두고 일행은 조금 뒤로 부른다'"],
];
const files = new Map();
const read = (n) => { if (!files.has(n)) files.set(n, fs.readFileSync(path.join(DIR, `${n}.mjs`), 'utf8')); return files.get(n); };
let n = 0;
for (const [no, from, to] of EDITS) {
  const src = read(no);
  if (!src.includes(from)) { console.log('★ 못 찾음', no, from.slice(0, 30)); continue; }
  files.set(no, src.replace(from, to)); n++;
}
for (const [no, src] of files) fs.writeFileSync(path.join(DIR, `${no}.mjs`), src, 'utf8');
console.log('표현 바꿈', n, '건');
