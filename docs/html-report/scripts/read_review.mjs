#!/usr/bin/env node
// 보고서 원문만 새 세션에 주고 세 질문(처음 보는 말, 예 없는 추상 문장, 할 일 한 문장)에 답하게 하는 읽기 검토.
// 인자: 원문 Markdown 경로, --host claude 또는 codex(기본 claude)
// 출력: stdout 검토 세션의 답과 마지막 줄 `사용 토큰: N`, stderr 실패 이유, 종료 0 성공·1 실패·2 인자 오류
// 실행 조건: 해당 공급자 CLI 로그인. 모델은 공급자마다 가장 저렴한 모델, 생각 수준 low 고정. 더 비싼 모델·높은 생각 수준 지정 금지
// Claude --bare(훅 생략)는 API 키 인증만 받아 구독 로그인에서 실패하므로 쓰지 않음
// 연결 예정: #91 교차 리뷰의 호스트 어댑터(continuity.py HOSTS의 review 명령)가 머지되면 그 명령에 모델 지정만 더해 바꿈
import { spawn } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

/** 공급자마다 가장 저렴한 모델. 바꿀 때 이 상수만 수정 */
export const CHEAPEST = Object.freeze({ claude: 'haiku', codex: 'gpt-6-luna' });

export const QUESTIONS = `아래 보고서를 처음 읽는 사람으로서 세 질문에 번호를 붙여 답하라. 보고서 밖 지식으로 보충하지 말 것.
1. 처음 보는 말이 있었나? 있으면 그 줄을 그대로 적어라. 없으면 "없음"
2. 예 없이 추상적인 문장이 있었나? 있으면 그 줄을 그대로 적어라. 없으면 "없음"
3. 다 읽고 무엇을 하면 되는지 한 문장으로 말하라. 말할 수 없으면 "모름"`;

// cost: time O(1), heap O(1), stack O(1)
// vars: 없음
// basis: estimate
/** 공급자 CLI 명령. 프롬프트는 표준 입력으로 넘긴다 */
export function reviewCommand(host, options = {}) {
  if (!Object.hasOwn(CHEAPEST, host)) throw new Error(`host는 ${Object.keys(CHEAPEST).join(', ')} 중 하나: ${host}`);
  if (options.model !== undefined && options.model !== CHEAPEST[host]) throw new Error(`읽기 검토 모델은 ${CHEAPEST[host]} 고정, 다른 모델 지정 금지`);
  return host === 'claude'
    ? ['claude', '-p', '--model', CHEAPEST.claude, '--effort', 'low', '--output-format', 'json']
    : ['codex', 'exec', '--model', CHEAPEST.codex, '-c', 'model_reasoning_effort=low', '--json', '-'];
}

// cost: time O(n), heap O(n), stack O(1)
// vars: n = CLI 출력 글자 수
// basis: estimate
/** CLI 출력에서 답과 사용 토큰. Claude는 결과 JSON 하나, Codex는 이벤트 JSON 줄 */
export function parseOutput(host, output) {
  if (host === 'claude') {
    const data = JSON.parse(output);
    const usage = data.usage ?? {};
    const tokens = ['input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens'].reduce((sum, key) => sum + (usage[key] ?? 0), 0);
    return { answer: String(data.result ?? '').trim(), tokens };
  }
  let answer = '';
  let tokens = 0;
  for (const line of output.split('\n')) {
    if (!line.trim().startsWith('{')) continue;
    const event = JSON.parse(line);
    if (event.type === 'item.completed' && event.item?.type === 'agent_message') answer = event.item.text ?? '';
    if (event.type === 'turn.completed') tokens += (event.usage?.input_tokens ?? 0) + (event.usage?.output_tokens ?? 0);
  }
  return { answer: answer.trim(), tokens };
}

// cost: time O(s) + 모델 응답 시간, heap O(s), stack O(1), io 1
// vars: s = 원문 글자 수
// basis: estimate
/** 원문만 넘겨 답과 사용 토큰을 받는다. 작성 대화·재료는 넘기지 않는다 */
export function run(source, host = 'claude', env = process.env) {
  const [command, ...args] = reviewCommand(host);
  return new Promise((done, fail) => {
    const child = spawn(command, args, { env: { ...process.env, ...env }, stdio: ['pipe', 'pipe', 'pipe'] });
    let out = '';
    let err = '';
    child.stdout.on('data', (chunk) => { out += chunk; });
    child.stderr.on('data', (chunk) => { err += chunk; });
    child.on('error', fail);
    child.on('close', (code) => (code === 0 ? done(parseOutput(host, out)) : fail(new Error(`${command} 종료 ${code}: ${err.trim()}`))));
    child.stdin.end(`${QUESTIONS}\n\n---\n\n${source}`);
  });
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  const at = args.indexOf('--host');
  const host = at >= 0 ? args.splice(at, 2)[1] : 'claude';
  if (args.length !== 1) {
    process.stderr.write('사용: node read_review.mjs <원문.md> [--host claude|codex]\n');
    process.exit(2);
  }
  try {
    const review = await run(readFileSync(resolve(args[0]), 'utf8'), host);
    process.stdout.write(`${review.answer}\n사용 토큰: ${review.tokens}\n`);
  } catch (error) {
    process.stderr.write(`${error.message}\n`);
    process.exit(1);
  }
}
