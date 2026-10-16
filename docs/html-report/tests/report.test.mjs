// html-report 생성기 시험. 원문 해석·판정 절·결과 형식·CSS 토큰은 의존성 없이, 생성은 npm ci 뒤에 실행한다.
import assert from 'node:assert/strict';
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync, cpSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, relative } from 'node:path';
import { test } from 'node:test';
import { runInNewContext } from 'node:vm';

import { cssViolations, judgedSections, splitSource } from '../scripts/report-core.mjs';

const ROOT = new URL('..', import.meta.url).pathname;
const EXAMPLES = join(ROOT, 'tests', 'examples');
const HAS_DEPS = existsSync(join(ROOT, 'scripts', 'node_modules', 'document-engine'));
const NEEDS_DEPS = HAS_DEPS ? false : 'scripts 폴더에서 npm ci 필요';

// cost: time O(n), heap O(n), stack O(d)
// vars: n = 폴더 안 파일 수, d = 폴더 깊이
// basis: estimate
function files(folder) {
  return readdirSync(folder, { recursive: true, withFileTypes: true })
    .filter((entry) => entry.isFile())
    .map((entry) => relative(folder, join(entry.parentPath, entry.name)))
    .sort();
}

test('front matter와 첫 문단을 머리 정보와 요약으로 나눈다', () => {
  const source = readFileSync(join(EXAMPLES, 'decision', 'report.md'), 'utf8');
  const { meta, summary, body } = splitSource(source);
  assert.deepEqual(meta, { kind: 'decision', title: '목차 위치 고르기', target: 'homepage-toc', version: '1' });
  assert.equal(summary, '본문 오른쪽 목차와 본문 위 목차 중 하나를 고른다.');
  assert.match(body, /^## 목차 위치/);
});

test('원문 규칙 위반은 이유와 함께 거부한다', () => {
  const head = (extra) => `---\nkind: decision\ntitle: T\ntarget: t\n${extra}---\n\n요약.\n\n`;
  const cases = [
    ['---\nkind: memo\ntitle: T\ntarget: t\n---\n\n요약.\n\n## 정리\n', /kind/],
    [head('') + '## 정리\n', /version/],
    [head('version: 1\n') + '## 1. 첫 절\n\n## 정리\n', /번호/],
    [head('version: 1\n') + ':::warning[주의]\n내용\n:::\n\n## 정리\n', /warning/],
    [head('version: 1\n') + '## 첫 절\n', /정리/],
  ];
  for (const [source, reason] of cases) assert.throws(() => splitSource(source), reason);
});

test('판정 대상은 그림 격자가 있는 ## 절이고 정리 절은 제외한다', () => {
  const body = [
    '## 설명만',
    '글.',
    '## 목차 위치',
    '```ui:figure-grid\ncolumns: 2\nitems:\n  - src: a.png\n    alt: a\n  - src: b.png\n    alt: b\n  - src: c.png\n    alt: c\n```',
    '## 코드 예',
    '````md\n```ui:figure-grid\n```\n````',
    '## 정리',
    '```ui:figure-grid\nitems:\n  - src: a.png\n    alt: a\n```',
  ].join('\n\n');
  assert.deepEqual(judgedSections(body), [{ index: 1, title: '목차 위치', figures: 3 }]);
});

test('결과 JSON은 target, version, questions(title, choice, note) 형식', () => {
  const code = readFileSync(join(ROOT, 'assets', 'report.js'), 'utf8');
  const sandbox = {};
  runInNewContext(code, sandbox);
  const result = sandbox.ReportCore.result(
    { target: 'homepage-toc', version: '1', questions: [{ id: 'a', title: '목차 위치' }, { id: 'b', title: '글꼴' }] },
    { a: { choice: 'A', note: '긴 문서' } },
  );
  assert.deepEqual(JSON.parse(JSON.stringify(result)), {
    target: 'homepage-toc',
    version: '1',
    questions: [
      { title: '목차 위치', choice: 'A', note: '긴 문서' },
      { title: '글꼴', choice: null, note: '' },
    ],
  });
  assert.equal(sandbox.ReportCore.storageKey({ target: 't', version: '1' }), 'html-report:t:1');
  assert.notEqual(sandbox.ReportCore.storageKey({ target: 't', version: '2' }), sandbox.ReportCore.storageKey({ target: 't', version: '1' }));
});

test('report.css에는 토큰 변수 밖의 색·길이 값이 없다', () => {
  const css = readFileSync(join(ROOT, 'assets', 'report.css'), 'utf8');
  assert.deepEqual(cssViolations(css), []);
  assert.deepEqual(cssViolations('a{color:#fff;margin:4px;width:calc(var(--x) + 2rem)}@media (max-width: 640px){b{gap:0}}'), ['#fff', '4px', '2rem']);
});

test('세 종류 원문으로 생성하고 출력 폴더 파일 목록이 맞다', { skip: NEEDS_DEPS }, async () => {
  const { buildReport } = await import('../scripts/build_report.mjs');
  for (const kind of ['explain', 'decision', 'result']) {
    const work = mkdtempSync(join(tmpdir(), 'report-'));
    try {
      cpSync(join(EXAMPLES, kind), work, { recursive: true });
      const out = join(work, 'out');
      await buildReport(join(work, 'report.md'), out);
      const list = files(out);
      for (const name of ['index.html', 'report.md', 'report.css', 'report.js', 'theme/tokens.css', 'theme/styles.css']) assert.ok(list.includes(name), `${kind}: ${name}`);
      assert.ok(list.some((name) => name.startsWith('theme/assets/fonts/')), `${kind}: 글꼴`);
      const html = readFileSync(join(out, 'index.html'), 'utf8');
      assert.doesNotMatch(html, /(?:src|href)="\/(?!\/)/, `${kind}: 절대 경로 없음`);
      assert.doesNotMatch(html, /https?:\/\/(?!www\.w3\.org)/, `${kind}: 외부 주소 없음`);
      if (kind === 'explain') assert.ok(list.some((name) => /^diagrams\/[0-9a-f]{64}\.html$/.test(name)));
      else assert.deepEqual(list.filter((name) => name.startsWith('assets/')), ['assets/a.png', 'assets/b.png']);
    } finally {
      rmSync(work, { recursive: true, force: true });
    }
  }
});

test('도표 실패면 생성 실패, 기존 출력 보존', { skip: NEEDS_DEPS }, async () => {
  const { buildReport } = await import('../scripts/build_report.mjs');
  const work = mkdtempSync(join(tmpdir(), 'report-'));
  try {
    cpSync(join(EXAMPLES, 'explain'), work, { recursive: true });
    const out = join(work, 'out');
    await buildReport(join(work, 'report.md'), out);
    const before = readFileSync(join(out, 'index.html'), 'utf8');
    const source = readFileSync(join(work, 'report.md'), 'utf8').replace('session -> hook "상태"', 'session -> missing "상태"');
    writeFileSync(join(work, 'report.md'), source);
    await assert.rejects(buildReport(join(work, 'report.md'), out), /도표/);
    assert.equal(readFileSync(join(out, 'index.html'), 'utf8'), before);
  } finally {
    rmSync(work, { recursive: true, force: true });
  }
});
