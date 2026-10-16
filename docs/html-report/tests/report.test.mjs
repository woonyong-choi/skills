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
  assert.deepEqual(meta, { kind: 'decision', title: '목차 위치 고르기', target: 'homepage 문서 페이지', version: '시안-1' });
  assert.match(summary, /^질문 1개\. 목차 위치는 A를 추천/);
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
  assert.deepEqual(judgedSections('## 고르기\n\n```ui:figure-grid\n{ "items": [\n  { "src": "a.png" }, { "src": "b.png" }\n] }\n```\n'), [{ index: 0, title: '고르기', figures: 2 }]);
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

// ---- 2단계: 설명 강제 자동 검사, 옛 저장 형식, 읽기 검토 모델 ----
const WORDS = ['정본', '토큰', '렌더'];
// cost: time O(n), heap O(n), stack O(1)
// vars: n = 원문 글자 수
// basis: estimate
const lint = async (body) => {
  const { lintSource } = await import('../scripts/report-core.mjs');
  return lintSource(`---\nkind: explain\ntitle: T\ntarget: t\n---\n\n${body}`, WORDS).map((item) => `${item.line}:${item.reason}`);
};

test('자동 검사: 빈 칸과 남은 {자리}', async () => {
  assert.match((await lint('요약.\n\n## 절\n\n- 한 줄로:\n'))[0], /^11:빈 칸/);
  assert.match((await lint('요약 {결론 한 문장}.\n'))[0], /^7:채우지 않은 자리/);
  assert.deepEqual(await lint('요약.\n\n## 절\n\n- 한 줄로: 체크포인트가 남는다\n'), []);
});

test('자동 검사: 예·근거 칸에 숫자·이름·코드가 없음', async () => {
  assert.match((await lint('요약.\n\n- 예를 들면: 찾기가 느림\n'))[0], /^9:예에 숫자/);
  assert.match((await lint('요약.\n\n- 좋아지는 것: 찾기. 예: 금방 보임\n'))[0], /^9:예에 숫자/);
  assert.deepEqual(await lint('요약.\n\n- 예를 들면: 토픽 40개에서 `order.paid` 찾기\n'), []);
  assert.deepEqual(await lint('요약.\n\n- 근거: 제목 아래 간격 24px(본문 문단 간격과 같음)\n'), []);
});

test('자동 검사: 낯선 말이 풀이 없이 처음 나옴', async () => {
  assert.match((await lint('정본 값을 쓴다.\n'))[0], /^7:낯선 말 '정본'/);
  assert.match((await lint('요약.\n\n`gen_llms.py`를 실행한다.\n'))[0], /낯선 말 'gen_llms.py'/);
  assert.deepEqual(await lint('정본(디자인 저장소에 정해 둔 값)을 쓴다. 정본을 다시 쓴다.\n'), []);
  assert.deepEqual(await lint('렌더링(화면에 그리기)을 한다.\n'), []);
});

test('자동 검사: 한 문장 80자 초과', async () => {
  const long = '가'.repeat(80) + '.';
  assert.match((await lint(`${long}\n`))[0], /^7:문장 81자/);
  assert.deepEqual(await lint(`${'가'.repeat(79)}.\n`), []);
});

test('자동 검사: 단위 숫자에 비교 대상', async () => {
  assert.match((await lint('목차 폭은 680px로 둔다.\n'))[0], /^7:680px에 비교 대상/);
  assert.deepEqual(await lint('목차 폭은 680px(1920px 화면의 3분의 1 정도)로 둔다.\n'), []);
  assert.deepEqual(await lint('응답이 120ms보다 빨라진다.\n'), []);
  assert.match((await lint('사용률 30%로 내린다.\n'))[0], /30%에 비교 대상/);
});

test('자동 검사: 코드 블록 안은 검사하지 않는다', async () => {
  assert.deepEqual(await lint('요약.\n\n```thinkflow\nthinkflow\ntitle "정본 680px {자리}"\n```\n'), []);
});

test('판정 저장 옛 형식은 빈 값으로 시작한다', () => {
  const code = readFileSync(join(ROOT, 'assets', 'report.js'), 'utf8');
  const sandbox = {};
  runInNewContext(code, sandbox);
  const restore = sandbox.ReportCore.restore;
  for (const raw of [null, 'undefined', '[]', '{"a":"A"}', '{"a":{"choice":7,"note":null}}', '{oops']) {
    const state = restore(raw);
    assert.equal(JSON.stringify(state).includes('undefined'), false, raw);
    assert.equal(state.a?.choice ?? null, null, raw);
    assert.equal(state.a?.note ?? '', '', raw);
  }
  assert.deepEqual(JSON.parse(JSON.stringify(restore('{"a":{"choice":"B","note":"좋음"}}'))), { a: { choice: 'B', note: '좋음' } });
});

test('읽기 검토는 공급자마다 가장 저렴한 모델로 실행한다', async () => {
  const { reviewCommand, CHEAPEST } = await import('../scripts/read_review.mjs');
  const work = mkdtempSync(join(tmpdir(), 'review-'));
  try {
    const log = join(work, 'argv.json');
    for (const name of ['claude', 'codex']) {
      writeFileSync(join(work, name), `#!/usr/bin/env node\nrequire('fs').writeFileSync(${JSON.stringify(log)}, JSON.stringify(process.argv.slice(2)));\nprocess.stdout.write('1. 없음\\n2. 없음\\n3. 목차 위치를 고르면 된다');\n`, { mode: 0o755 });
    }
    const { run } = await import('../scripts/read_review.mjs');
    for (const host of ['claude', 'codex']) {
      const answer = await run('# 보고서\n', host, { PATH: `${work}:${process.env.PATH}` });
      const argv = JSON.parse(readFileSync(log, 'utf8'));
      assert.ok(argv.includes(CHEAPEST[host]), `${host}: ${argv}`);
      assert.match(answer, /목차 위치/);
      assert.deepEqual(reviewCommand(host).slice(0, 1), [host]);
    }
    assert.equal(CHEAPEST.claude, 'haiku');
    assert.throws(() => reviewCommand('claude', { model: 'opus' }), /모델/);
  } finally {
    rmSync(work, { recursive: true, force: true });
  }
});
