// 보고서 원문의 머리 정보·요약·판정 절 판별과 report.css 토큰 검사. 외부 의존성 없이 시험한다.

export const KINDS = Object.freeze(['explain', 'decision', 'result']);
export const SUMMARY_SECTION = '정리';

// cost: time O(n), heap O(n), stack O(1)
// vars: n = 머리 정보 줄 수
// basis: estimate
/** front matter. 값 한 줄짜리 키와 `related` 목록(title, href)만 받는다 */
function parseFrontMatter(text) {
  const meta = {};
  let list;
  for (const line of text.split('\n')) {
    if (!line.trim()) continue;
    const item = line.match(/^\s+-\s+(\w+):\s*(.*)$/);
    const field = line.match(/^\s+(\w+):\s*(.*)$/);
    const key = line.match(/^(\w+):\s*(.*)$/);
    if (key) {
      list = key[2] === '' ? (meta[key[1]] = []) : undefined;
      if (key[2] !== '') meta[key[1]] = unquote(key[2]);
    } else if (item && list) list.push({ [item[1]]: unquote(item[2]) });
    else if (field && list?.length) list.at(-1)[field[1]] = unquote(field[2]);
    else throw new Error(`front matter 줄을 읽을 수 없음: ${line}`);
  }
  return meta;
}

// cost: time O(1), heap O(1), stack O(1)
// vars: 없음
// basis: estimate
function unquote(value) {
  return value.trim().replace(/^(['"])(.*)\1$/, '$2');
}

// cost: time O(1), heap O(1), stack O(1)
// vars: 없음
// basis: estimate
/** 펜스 열기·닫기 줄이면 다음 펜스 상태(열린 표식 또는 빈 글자), 아니면 undefined. 닫기 줄은 정보 글자 없음 */
function fenceStep(line, fence) {
  const marker = line.match(/^\s*(`{3,}|~{3,})(.*)$/);
  if (!marker) return undefined;
  if (!fence) return marker[1];
  return marker[1][0] === fence[0] && marker[1].length >= fence.length && !marker[2].trim() ? '' : undefined;
}

// cost: time O(n), heap O(n), stack O(1)
// vars: n = 원문 글자 수
// basis: estimate
/** 코드 펜스 안 줄을 지운 본문. 절 판별·규칙 검사가 예시 코드에 걸리지 않게 한다 */
function withoutFences(text) {
  const lines = [];
  let fence = '';
  for (const line of text.split('\n')) {
    const step = fenceStep(line, fence);
    if (step !== undefined) {
      lines.push(fence ? '' : line);
      fence = step;
      continue;
    }
    lines.push(fence ? '' : line);
  }
  return lines.join('\n');
}

// cost: time O(n), heap O(n), stack O(1)
// vars: n = 원문 글자 수
// basis: estimate
/**
 * 원문을 머리 정보·요약 한 문장·본문으로 나누고 원문 규칙을 검사한다.
 * @returns {{ meta: object, summary: string, body: string }}
 */
export function splitSource(source) {
  const match = source.match(/^---\n([\s\S]*?)\n---\n+([\s\S]*)$/);
  if (!match) throw new Error('원문 첫 줄은 front matter(---)');
  const meta = parseFrontMatter(match[1]);
  if (!KINDS.includes(meta.kind)) throw new Error(`kind는 ${KINDS.join(', ')} 중 하나: ${meta.kind}`);
  for (const key of ['title', 'target']) if (!meta[key]) throw new Error(`front matter ${key} 필요`);
  if (meta.kind !== 'explain' && !meta.version) throw new Error('비교 보고서는 front matter version 필요');
  const [first, ...rest] = match[2].split(/\n\s*\n/);
  if (!first || first.startsWith('#')) throw new Error('front matter 뒤 첫 문단은 요약 한 문장');
  const summary = first.replace(/\s*\n\s*/g, ' ').trim();
  const body = rest.join('\n\n').trim() + '\n';
  const plain = withoutFences(body);
  const headings = [...plain.matchAll(/^##\s+(.+)$/gm)].map((heading) => heading[1].trim());
  const numbered = [...plain.matchAll(/^#{2,6}\s+(\d+[.)]|[A-Z][.)]\s)/gm)];
  if (numbered.length) throw new Error(`제목에 번호 금지: ${numbered[0][0]}`);
  if (/^:::warning/m.test(plain)) throw new Error(':::warning 사용 금지, :::note[추천] 또는 :::note[판단] 사용');
  if (headings.at(-1) !== SUMMARY_SECTION) throw new Error(`마지막 ## 절은 ${SUMMARY_SECTION}`);
  return { meta, summary, body };
}

// cost: time O(n), heap O(n), stack O(1)
// vars: n = 본문 글자 수
// basis: estimate
/**
 * 판정 대상 절: 그림 격자(ui:figure-grid)가 있는 ## 절. 정리 절과 코드 예 안 격자는 제외.
 * index는 본문의 ## 절 순서(0부터), figures는 첫 격자의 그림 수.
 */
export function judgedSections(body) {
  const sections = [];
  let fence = '';
  let grid = false;
  let current;
  for (const line of body.split('\n')) {
    const step = fenceStep(line, fence);
    if (step !== undefined) {
      grid = Boolean(step) && Boolean(current) && /^\s*`{3,}ui:figure-grid\b/.test(line);
      if (grid) current.grids.push(0);
      fence = step;
      continue;
    }
    if (fence) {
      if (grid) current.grids[current.grids.length - 1] += (line.match(/^\s*-\s+src:|"src"\s*:/g) ?? []).length;
      continue;
    }
    const heading = line.match(/^##\s+(.+)$/);
    if (heading) {
      current = { index: sections.length, title: heading[1].trim(), grids: [] };
      sections.push(current);
    }
  }
  return sections
    .filter((section) => section.grids.length && section.title !== SUMMARY_SECTION)
    .map(({ index, title, grids }) => ({ index, title, figures: grids[0] }));
}

// cost: time O(n), heap O(n), stack O(1)
// vars: n = CSS 글자 수
// basis: estimate
/**
 * 토큰 변수 밖의 색·길이 값. @media 조건, 주석, 0, 단위 없는 수, fr은 허용한다.
 * @returns {string[]} 위반 값 목록
 */
export function cssViolations(css) {
  const text = css.replace(/\/\*[\s\S]*?\*\//g, '').replace(/@media[^{]*\{/g, '{');
  const values = [...text.matchAll(/\{([^{}]*)\}/g)].flatMap((block) => block[1].split(';'))
    .map((declaration) => declaration.split(':').slice(1).join(':'))
    .map((value) => value.replace(/var\(--[\w-]+\)/g, ''));
  const found = [];
  for (const value of values) {
    for (const hit of value.matchAll(/#[0-9a-f]{3,8}\b|\b(?:rgba?|hsla?|oklch|lab|lch)\(|(?<![\w-])-?\d*\.?\d+(?:px|r?em|%|vh|vw|vmin|vmax|ch|ex|pt|cqw|cqh)\b/gi)) {
      found.push(hit[0]);
    }
  }
  return found;
}

// ---- 설명 강제 자동 검사 ----
const EXAMPLE_SLOT = /(?:^|[\s(])(예를 들면|예|근거):\s*(.*)$/;
const CONCRETE = /\d|`|[A-Za-z]|["“”'‘’「」]/;
const CODE_NAME = /`?\b(?:[a-z][a-z0-9]*_[a-z0-9_]+(?:\.[a-z]+)?|[\w-]+\.(?:py|mjs|js|ts|sh|json))\b`?/g;
const UNIT = /(\d+(?:\.\d+)?)\s*(px|ms|%|KB|MB)(?![A-Za-z])/g;
const SENTENCE_LIMIT = 80;

// cost: time O(w), heap O(w), stack O(1)
// vars: w = 목록 파일 글자 수
// basis: estimate
/** 낯선 말 목록 파일(references/unfamiliar-words.md)의 `- 말` 줄 */
export function readWords(text) {
  return [...text.matchAll(/^-\s+(\S+)\s*$/gm)].map((match) => match[1].replace(/[`:]/g, ''));
}

// cost: time O(n), heap O(n), stack O(1)
// vars: n = 원문 글자 수
// basis: estimate
/** 검사할 본문 줄: front matter와 코드 펜스 안은 빈 줄로 두어 줄 번호를 지킨다 */
function proseLines(source) {
  const lines = source.split('\n');
  const end = lines[0] === '---' ? lines.indexOf('---', 1) : -1;
  let fence = '';
  return lines.map((line, at) => {
    if (at <= end) return '';
    const step = fenceStep(line, fence);
    if (step !== undefined) {
      fence = step;
      return '';
    }
    return fence ? '' : line;
  });
}

// cost: time O(1), heap O(1), stack O(1)
// vars: 없음
// basis: estimate
/** 글자 수를 셀 문장: 링크 주소와 마크다운 표식 제외 */
function visible(text) {
  return text.replace(/\]\([^)]*\)/g, ']').replace(/[`*_[\]]/g, '').replace(/^\s*(?:[-*]|\d+\.)\s+/, '').replace(/^#+\s+/, '').trim();
}

// cost: time O(n * w), heap O(n), stack O(1)
// vars: n = 원문 글자 수, w = 낯선 말 수
// basis: estimate
/**
 * 설명 강제 검사. 걸리면 { line, reason } 목록(줄 번호는 원문 기준 1부터).
 * 빈 칸·남은 {자리}, 숫자·이름·코드 없는 예·근거, 풀이 없이 처음 나온 낯선 말, 80자 넘는 문장, 비교 대상 없는 단위 숫자
 */
export function lintSource(source, words = []) {
  const problems = [];
  const seen = new Set();
  const add = (line, reason) => problems.push({ line, reason });
  proseLines(source).forEach((line, at) => {
    const number = at + 1;
    if (!line.trim()) return;
    if (/^\s*-\s+[^:]+:\s*$/.test(line)) add(number, '빈 칸');
    const placeholder = line.replace(/`[^`]*`/g, '').match(/\{[^}\n]*\}/);
    if (placeholder) add(number, `채우지 않은 자리 ${placeholder[0]}`);
    const slot = line.match(EXAMPLE_SLOT);
    if (slot && slot[2].trim() && !CONCRETE.test(slot[2])) add(number, `예에 숫자·고유 이름·코드 표기 없음: ${slot[1]}`);
    const names = [...words.map((word) => ({ word, pattern: new RegExp(`${word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}[가-힣]*`, 'g') })), { word: undefined, pattern: CODE_NAME }];
    for (const { word, pattern } of names) {
      for (const hit of line.matchAll(pattern)) {
        const name = word ?? hit[0].replace(/`/g, '');
        if (seen.has(name)) continue;
        seen.add(name);
        if (!/^\s*\(/.test(line.slice(hit.index + hit[0].length))) add(number, `낯선 말 '${name}' 풀이 없음(처음 나올 때 괄호로 풀이)`);
      }
    }
    for (const sentence of visible(line).split(/(?<=[.!?])\s+/)) {
      if ([...sentence].length > SENTENCE_LIMIT) add(number, `문장 ${[...sentence].length}자, ${SENTENCE_LIMIT}자 이하로 나누기`);
      for (const hit of sentence.matchAll(UNIT)) {
        const before = sentence.slice(0, hit.index);
        if (before.split('(').length > before.split(')').length) continue;
        const after = sentence.slice(hit.index + hit[0].length);
        if (!/^\s*(?:[가-힣]+\s*)?\(/.test(after) && !/^\s*(?:보다|의)/.test(after) && !/보다/.test(sentence)) add(number, `${hit[1]}${hit[2]}에 비교 대상 없음(괄호 설명 또는 ~보다)`);
      }
    }
  });
  return problems;
}
