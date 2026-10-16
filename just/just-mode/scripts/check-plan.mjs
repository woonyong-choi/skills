#!/usr/bin/env node
import fs from "node:fs";
import process from "node:process";

const RULE =
	"테스트만으로는 검증이 충분하지 않다. PR은 단위, 실사용, 성능 상자가 모두 체크됐을 때만 검증된 것이다.";
const LANES = /PR head에서 `[^`<>]+` 역할 모델로 검증 항목 10개를 돌린다/;
const SUB_BLOCKS = [
	"선행 PR.",
	"파일.",
	"구현.",
	"확인할 결과.",
	"검증, 단위.",
	"검증, 실사용.",
	"검증, 성능.",
	"리뷰 게이트.",
	"머지.",
];
const PROGRAM_H3 = ["프로그램 시작 준비", "담당자 띄우기", "PR 절차", "판정과 머지", "부팅 절차"];
const PROGRAM_MARKERS = ["git show origin/HEAD:", "1시간마다 주기적으로 다시 깨우기", "상태 메시지"];
const HOW_TO_READ_MARKERS = [
	"상자 하나가 작업 단위 하나다",
	"증거를 적는다",
	"증거가 있을 때만 상자를 체크한다",
	"playbooks/",
	RULE,
];
const PERF_ITEMS = ["지표.", "측정.", "기준값.", "판정."];
const HOW_TO_READ = "읽는 법";
const PROGRAM = "프로그램 체크리스트";
const CLOSE = "프로그램 마무리";
const APPENDIX = "부록";
const PROTOTYPE = "프로토타입 증거";
const BOX = /^\s*- \[[ x]\] (.*)$/;

const file = process.argv[2];
if (!file) {
	console.error("사용법: node check-plan.mjs <plan.md>");
	process.exit(2);
}

const raw = fs.readFileSync(file, "utf8").split(/\r?\n/);
const problems = [];
const fail = (line, message) => problems.push(`${file}:${line}: ${message}`);

let start = 0;
if (raw[0] === "---") {
	start = raw.indexOf("---", 1) + 1;
}

const lines = [];
let fence = null;
const openingFence = (text) => {
	const match = text.match(/^ {0,3}(`{3,}|~{3,})(.*)$/);
	if (!match || (match[1][0] === "`" && match[2].includes("`"))) return null;
	return { char: match[1][0], length: match[1].length };
};
const closingFence = (text, opening) => {
	const match = text.match(/^ {0,3}(`+|~+)[ \t]*$/);
	return Boolean(
		match &&
		match[1][0] === opening.char &&
		match[1].length >= opening.length,
	);
};
for (let i = start; i < raw.length; i++) {
	const text = raw[i];
	const n = i + 1;
	let code = Boolean(fence);
	if (fence && closingFence(text, fence)) {
		code = false;
		fence = null;
	} else if (!fence) {
		fence = openingFence(text);
		code = Boolean(fence);
	}
	lines.push({ n, text, code });
	if (code) continue;
	const prose = text
		.replace(/`[^`]*`/g, "`")
		.replace(/!\[[^\]]*\]\([^)]*\)/g, "")
		.replace(/\]\([^)]*\)/g, "]");
	if (/[\u2013\u2014]/.test(prose)) fail(n, "긴 대시");
	if (/[\u2018\u2019\u201c\u201d]/.test(prose)) fail(n, "둥근 따옴표");
	if (/: \S/.test(prose)) fail(n, "문장 중간 콜론");
}

const h2 = (l) => (!l.code && l.text.startsWith("## ") ? l.text.slice(3).trim() : null);
const sections = [];
for (const l of lines) {
	const title = h2(l);
	if (title !== null) sections.push({ title, n: l.n, body: [] });
	else if (sections.length) sections.at(-1).body.push(l);
}
const find = (title) => sections.find((s) => s.title === title);
const bodyText = (s) => s.body.map((l) => l.text).join("\n");
const boxes = (ls) => ls.filter((l) => !l.code && BOX.test(l.text)).map((l) => ({ n: l.n, text: l.text.match(BOX)[1] }));

const h1 = lines.findIndex((l) => !l.code && l.text.startsWith("# "));
if (h1 === -1) fail(1, "H1 제목 없음");
const howToRead = find(HOW_TO_READ);
if (!howToRead) fail(1, `"## ${HOW_TO_READ}" 절 없음`);
if (h1 !== -1 && howToRead) {
	const intro = lines.slice(h1 + 1).filter((l) => l.n < howToRead.n && l.text.trim() !== "");
	if (intro.length >= 10) fail(lines[h1].n, `도입부가 ${intro.length}줄. 열 줄 미만이어야 함`);
	for (const marker of HOW_TO_READ_MARKERS) {
		if (!bodyText(howToRead).includes(marker)) fail(howToRead.n, `${HOW_TO_READ} 절에 "${marker}" 없음`);
	}
}

const program = find(PROGRAM);
if (!program) fail(1, `"## ${PROGRAM}" 절 없음`);
else {
	const h3s = program.body.filter((l) => !l.code && l.text.startsWith("### ")).map((l) => l.text.slice(4).trim());
	let cursor = 0;
	for (const name of PROGRAM_H3) {
		const at = h3s.findIndex((t, i) => i >= cursor && t.startsWith(name));
		if (at === -1) fail(program.n, `${PROGRAM}에 "### ${name}"이 순서대로 없음`);
		else cursor = at + 1;
	}
	for (const marker of PROGRAM_MARKERS) {
		if (!bodyText(program).includes(marker)) fail(program.n, `${PROGRAM}에 "${marker}" 없음`);
	}
}

const close = find(CLOSE);
if (!close) fail(1, `"## ${CLOSE}" 절 없음`);
const programIndex = sections.indexOf(program);
const closeIndex = sections.indexOf(close);
const prSections = programIndex === -1 || closeIndex === -1 ? [] : sections.slice(programIndex + 1, closeIndex);
if (prSections.length === 0) fail(1, `${PROGRAM}와 ${CLOSE} 사이에 PR 절 없음`);

const report = [];
for (const pr of prSections) {
	const heads = [];
	for (const l of pr.body) {
		if (l.code) continue;
		const m = l.text.match(/^\*\*([^*]+)\*\*(.*)$/);
		if (m && SUB_BLOCKS.includes(m[1])) heads.push({ name: m[1], n: l.n, rest: m[2].trim(), lines: [] });
		else if (heads.length) heads.at(-1).lines.push(l);
	}
	const names = heads.map((h) => h.name);
	if (names.join("|") !== SUB_BLOCKS.join("|")) {
		fail(pr.n, `${pr.title}: 하위 블록이 [${names.join(", ")}]. 기대값 [${SUB_BLOCKS.join(", ")}]`);
	}
	const block = (name) => heads.find((h) => h.name === name);
	const counts = {};
	for (const h of heads) counts[h.name] = boxes(h.lines).length;

	const depends = block(SUB_BLOCKS[0]);
	if (depends && depends.rest === "") fail(depends.n, `${pr.title}: ${SUB_BLOCKS[0]} 내용 없음`);
	for (const name of ["파일.", "구현.", "확인할 결과.", "검증, 단위.", "머지."]) {
		const b = block(name);
		if (b && boxes(b.lines).length === 0) fail(b.n, `${pr.title}: ${name} 상자 없음`);
	}
	for (const name of ["검증, 단위.", "검증, 실사용.", "검증, 성능."]) {
		const b = block(name);
		if (b && !b.rest.startsWith(RULE)) fail(b.n, `${pr.title}: ${name} 블록이 검증 규칙 문장으로 시작하지 않음`);
	}

	const live = block("검증, 실사용.");
	if (live) {
		if (!LANES.test(live.rest)) fail(live.n, `${pr.title}: 검증, 실사용 블록에 역할을 채운 "PR head에서 \`<swarm 작업자 역할>\` 역할 모델로 검증 항목 10개를 돌린다" 없음`);
		const lanes = boxes(live.lines).map((b) => ({ ...b, m: b.text.match(/^검증 항목 (\d+)\. /) }));
		const numbers = lanes.filter((b) => b.m).map((b) => Number(b.m[1])).sort((a, b) => a - b);
		if (numbers.join(",") !== "1,2,3,4,5,6,7,8,9,10") fail(live.n, `${pr.title}: 검증 항목 번호가 [${numbers.join(",")}]. 1부터 10까지여야 함`);
		for (const lane of lanes) {
			if (!lane.m) fail(lane.n, `${pr.title}: 실사용 상자가 검증 항목이 아님`);
			else if (!/`[^`]+` 저장/.test(lane.text)) fail(lane.n, `${pr.title}: 검증 항목 ${lane.m[1]}에 저장할 스크린샷 없음`);
			else if (!lane.text.includes("통과 조건")) fail(lane.n, `${pr.title}: 검증 항목 ${lane.m[1]}에 통과 조건 없음`);
		}
	}

	const perf = block("검증, 성능.");
	if (perf) {
		const items = boxes(perf.lines).map((b) => b.text.split(" ")[0]);
		if (items.join("|") !== PERF_ITEMS.join("|")) fail(perf.n, `${pr.title}: 성능 상자가 [${items.join(", ")}]. 기대값 [${PERF_ITEMS.join(", ")}]`);
	}

	const gate = block("리뷰 게이트.");
	if (gate) {
		const gateBoxes = boxes(gate.lines);
		if (gate.rest.startsWith("없음.")) {
			if (gateBoxes.length) fail(gate.n, `${pr.title}: 리뷰 게이트가 없음인데 상자가 있음`);
		} else {
			const text = gate.lines.map((l) => l.text).join("\n");
			if (gateBoxes.length === 0) fail(gate.n, `${pr.title}: 리뷰 게이트 상자 없음`);
			for (const word of ["스크린샷", "영상", "사용자"]) {
				if (!text.includes(word)) fail(gate.n, `${pr.title}: 리뷰 게이트에 "${word}" 없음`);
			}
		}
	}

	const total = boxes(pr.body).length;
	const cells = SUB_BLOCKS.slice(1).map((s) => `${s.replace(/[ ,.]+/g, "-").replace(/-$/, "").toLowerCase()}=${counts[s] ?? 0}`);
	report.push(`${pr.title}  boxes=${total}  ${cells.join(" ")}`);
}

if (closeIndex !== -1) {
	const tail = sections.slice(closeIndex + 1);
	for (const s of tail) {
		if (!s.title.startsWith(APPENDIX)) fail(s.n, `${CLOSE} 뒤의 "## ${s.title}"는 부록이 아님`);
	}
	if (!tail.some((s) => s.title.includes(PROTOTYPE))) fail(close.n, `"## ${APPENDIX} ... ${PROTOTYPE}" 절 없음`);
}

for (const line of report) console.log(line);
console.log(`PR 절 ${prSections.length}개, 문제 ${problems.length}개`);
for (const p of problems) console.error(p);
process.exit(problems.length ? 1 : 0);
