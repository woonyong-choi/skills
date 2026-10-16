#!/usr/bin/env node
// 보고서 원문 Markdown을 document-engine으로 그려 정본 문서 배치에 조립한 보고서 폴더를 만든다.
// 인자: 원문 Markdown 경로, 선택 출력 폴더(기본 원문 폴더)
// 출력: 출력 폴더의 index.html, 원문 Markdown, theme/(정본 CSS·글꼴), report.css, report.js, diagrams/, assets/. stdout index.html 경로, stderr 실패 이유, 종료 0 성공·1 실패·2 인자 오류
// 실행 조건: Node.js 22.12 이상, 이 폴더에서 npm ci, git-issue 스킬과 등록 Vault. 출력은 Vault의 보고서 위치만. 설명 검사·원문 규칙·도표 실패면 기존 출력 폴더의 파일 유지
import { spawnSync } from 'node:child_process';
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { judgedSections, lintSource, readWords, splitSource } from './report-core.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const ASSETS = join(HERE, '..', 'assets');
const WORDS = join(HERE, '..', 'references', 'unfamiliar-words.md');
const ASSET_PREFIX = '/__report__/assets/';
// 설치본(스킬 폴더 나란히)과 원본 저장소(docs/·git/) 두 배치의 git-issue 위치
const CONTEXT_SCRIPTS = [join(HERE, '..', '..', 'git-issue', 'scripts'), join(HERE, '..', '..', '..', 'git', 'git-issue', 'scripts')];
// project_context의 Vault 해석·쓰기 검사를 그대로 쓰고 보고서 폴더 위치만 더 좁힌다
const DESTINATION_CHECK = `
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import project_context as pc
cwd, target = Path(sys.argv[2]), Path(sys.argv[3]).resolve()
def done(**value):
    print(json.dumps(value, ensure_ascii=False))
    raise SystemExit(0)
try:
    vault = pc.resolve_vault()
except Exception as error:
    done(ok=False, error=str(error))
legacy = (vault / "legacy" / "reports").resolve()
try:
    project = pc.check_project(cwd)
except Exception:
    project = None
if project:
    try:
        pc.check_write(project, target)
    except Exception as error:
        done(ok=False, error=str(error))
    reports = (Path(project["area"]) / "docs" / "reports").resolve()
    if target.parent.parent == reports:
        done(ok=True, kind="project", root=str(reports))
if target.parent.parent == legacy:
    done(ok=True, kind="legacy", root=str(legacy))
expected = str((Path(project["area"]) / "docs" / "reports").resolve()) + "/{YYYY-MM-DD}-{주제}/ 또는 " if project else ""
done(ok=False, error=f"보고서 폴더는 {expected}{legacy}/{{YYYY-MM-DD}}-{{주제}}/ 아래만")
`;

// cost: time O(p) + Python 실행 시간, heap O(1), stack O(1), io O(p)
// vars: p = 등록 프로젝트 수
// basis: estimate
/**
 * 보고서 폴더 위치 검사. 등록 프로젝트는 <Vault>/worktree/<프로젝트>/docs/reports/, 프로젝트 무관은 <Vault>/legacy/reports/.
 * Vault 미등록·저장소 안·그 밖의 위치는 이유와 함께 실패. 파일을 쓰기 전에만 부른다
 */
export function checkDestination(outDir, { cwd = process.cwd(), env = process.env } = {}) {
  const scripts = CONTEXT_SCRIPTS.find((folder) => existsSync(join(folder, 'project_context.py')));
  if (!scripts) throw new Error('git-issue project_context.py를 찾을 수 없음: git-issue 스킬 설치 필요');
  const run = spawnSync('python3', ['-c', DESTINATION_CHECK, scripts, cwd, join(resolve(outDir), 'report.md')], { env, encoding: 'utf8', timeout: 30000 });
  let result;
  try {
    result = JSON.parse(run.stdout);
  } catch {
    throw new Error(`보고서 위치 검사 실패: ${run.stderr || run.error?.message || '응답 없음'}`);
  }
  if (!result.ok) throw new Error(`보고서 위치 거부: ${result.error}`);
  return result;
}

// cost: time O(1), heap O(1), stack O(1)
// vars: 없음
// basis: estimate
const escape = (value) => String(value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);

// cost: time O(h), heap O(h), stack O(1)
// vars: h = 본문 HTML 글자 수
// basis: estimate
/** 최상위 h2마다 절로 감싼다. 판정 런타임과 필터가 절 단위로 동작한다 */
function wrapSections(html, ids) {
  const parts = html.split(/(?=<h2[\s>])/);
  const head = parts[0].startsWith('<h2') ? '' : parts.shift();
  return head + parts.map((part, at) => `<section class="report-section" data-report-section="${escape(ids[at] ?? `section-${at}`)}">${part}</section>`).join('');
}

// cost: time O(c), heap O(c), stack O(1), io O(u)
// vars: c = styles.css 글자 수, u = url() 수
// basis: estimate
/** 정본 styles.css가 url()로 가리키는 파일(글꼴·아이콘)을 theme/ 아래 같은 상대 위치로 */
function themeFiles(root) {
  const css = readFileSync(join(root, 'styles.css'), 'utf8');
  const names = new Set([...css.matchAll(/url\(\s*['"]?(?:\.\/)?([^'")]+?)['"]?\s*\)/g)].map((match) => match[1]).filter((name) => !/^(?:data:|https?:|#)/.test(name)));
  return ['tokens.css', 'styles.css', ...names];
}

// cost: time O(f), heap O(1), stack O(1), io O(f)
// vars: f = 복사할 파일 수
// basis: estimate
function copyInto(stage, files) {
  for (const [from, to] of files) {
    mkdirSync(dirname(join(stage, to)), { recursive: true });
    copyFileSync(from, join(stage, to));
  }
}

// cost: time O(s + d * t), heap O(s + d), stack O(1), io O(f)
// vars: s = 원문 글자 수, d = 도표 수, t = 도표 하나 생성 시간, f = 출력 파일 수
// basis: estimate
/**
 * 보고서 폴더를 만든다. 모든 파일을 임시 폴더에 다 만든 뒤에만 출력 폴더로 옮기므로 실패하면 기존 출력이 그대로다.
 * @returns {Promise<string>} index.html 경로
 */
export async function buildReport(sourcePath, outDir = dirname(sourcePath), context = {}) {
  checkDestination(outDir, context);
  const source = readFileSync(sourcePath, 'utf8');
  const { meta, summary, body } = splitSource(source);
  const problems = lintSource(source, readWords(readFileSync(WORDS, 'utf8')));
  if (problems.length) throw new Error(`설명 검사 ${problems.length}건\n${problems.map((item) => `${item.line}줄: ${item.reason}`).join('\n')}`);
  const engine = await import('document-engine');
  const ui = await import('@woonyong-choi/design-tokens/components');
  const themeRoot = fileURLToPath(engine.DEFAULT_THEME_FILES.root);
  const assetDir = join(dirname(sourcePath), 'assets');
  const exists = (name) => existsSync(join(assetDir, name));

  const document = await engine.parseDocument(body, { id: sourcePath, pageId: 'report', assets: { exists } });
  const { diagrams, assets: diagramFiles } = await engine.compileDiagrams(document.metadata.diagrams.map((diagram) => diagram.source));
  const failed = [...diagrams.values()].filter((diagram) => diagram.error);
  if (failed.length) throw new Error(`도표 생성 실패 ${failed.length}개: ${failed.map((diagram) => diagram.error).join(' / ')}`);
  const output = await engine.renderDocument(document, { assets: { url: (name) => ASSET_PREFIX + name }, diagrams });
  const errors = output.diagnostics.filter((item) => item.severity === 'error');
  if (errors.length) throw new Error(`원문 오류: ${errors.map((item) => `${item.line ?? '?'}줄 ${item.message}`).join(' / ')}`);
  if (output.diagrams.some((diagram) => diagram.status !== 'embedded')) throw new Error('도표 생성 실패: 삽입되지 않은 도표');

  const sections = output.headings.filter((heading) => heading.level === 2);
  const judged = meta.kind === 'explain' ? [] : judgedSections(body);
  const questions = judged.map(({ index, title, figures }) => ({ id: sections[index]?.id ?? `section-${index}`, title, figures }));
  const html = wrapSections(output.html, sections.map((section) => section.id))
    .replaceAll(`"${ASSET_PREFIX}`, '"assets/')
    .replaceAll('"/diagrams/', '"diagrams/');

  const related = Array.isArray(meta.related) && meta.related.length
    ? `<nav class="report-related" aria-label="관련 보고서"><h2>관련 보고서</h2><ul>${meta.related.map((item) => `<li><a href="${escape(item.href)}">${escape(item.title)}</a></li>`).join('')}</ul></nav>`
    : '';
  const outline = String(ui.DocumentOutline({ sections: output.headings.filter((heading) => heading.level <= 3) })) + related;
  const article = ui.DocumentArticle({ title: meta.title, lead: ui.trusted(escape(summary)), metadata: ui.trusted(''), body: ui.trusted(html) });
  const layout = String(ui.DocumentLayout({ outline: outline ? ui.trusted(outline) : undefined, content: article }));
  const data = JSON.stringify({ kind: meta.kind, target: meta.target, version: meta.version ?? null, questions }).replace(/</g, '\\u003c');
  const page = readFileSync(join(ASSETS, 'template.html'), 'utf8')
    .replace('{{title}}', escape(meta.title))
    .replace('{{data}}', data)
    .replace('{{layout}}', layout);

  const stage = mkdtempSync(join(tmpdir(), 'html-report-'));
  try {
    writeFileSync(join(stage, 'index.html'), page);
    for (const [src, html] of diagramFiles) {
      mkdirSync(join(stage, 'diagrams'), { recursive: true });
      writeFileSync(join(stage, src.replace(/^\//, '')), html);
    }
    copyInto(stage, [
      [sourcePath, basename(sourcePath)],
      [join(ASSETS, 'report.css'), 'report.css'],
      [join(ASSETS, 'report.js'), 'report.js'],
      ...themeFiles(themeRoot).map((name) => [join(themeRoot, name), join('theme', name)]),
      ...output.assets.map(({ name }) => [join(assetDir, name), join('assets', name)]),
    ]);
    publish(stage, resolve(outDir));
  } finally {
    rmSync(stage, { recursive: true, force: true });
  }
  return join(resolve(outDir), 'index.html');
}

// cost: time O(f), heap O(f), stack O(d), io O(f)
// vars: f = 출력 파일 수, d = 폴더 깊이
// basis: estimate
/** 다 만든 임시 폴더의 파일을 출력 폴더로 덮어쓴다 */
function publish(stage, outDir) {
  for (const entry of readdirSync(stage, { recursive: true, withFileTypes: true })) {
    if (!entry.isFile()) continue;
    const from = join(entry.parentPath, entry.name);
    const to = join(outDir, from.slice(stage.length + 1));
    mkdirSync(dirname(to), { recursive: true });
    copyFileSync(from, to);
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [input, out] = process.argv.slice(2);
  if (!input || process.argv.length > 4) {
    process.stderr.write('사용: node build_report.mjs <원문.md> [출력 폴더]\n');
    process.exit(2);
  }
  try {
    process.stdout.write(`${await buildReport(resolve(input), out ? resolve(out) : undefined)}\n`);
  } catch (error) {
    process.stderr.write(`${error.message}\n`);
    process.exit(1);
  }
}
