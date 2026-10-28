import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { expect, test } from "bun:test";

const checker = join(import.meta.dir, "check-plan.mjs");
const rule =
	"테스트만으로는 검증이 충분하지 않다. PR은 단위, 실사용, 성능 상자가 모두 체크됐을 때만 검증된 것이다.";

const validPlan = `# 데모

## 읽는 법
상자 하나가 작업 단위 하나다. 모든 상자는 증거를 적는다. 증거가 있을 때만 상자를 체크한다. playbooks/ 참고.
${rule}

## 프로그램 체크리스트
### 프로그램 시작 준비
### 담당자 띄우기
### PR 절차(모든 PR 공통)
### 판정과 머지(모든 PR 공통)
### 부팅 절차
\`git show origin/HEAD:\` 1시간마다 주기적으로 다시 깨우기. 상태 메시지.

## PR 1
**선행 PR.** 없음.
**파일.**
- [ ] 한다.
**구현.**
- [ ] 한다.
**확인할 결과.**
- [ ] 한다.
**검증, 단위.** ${rule}
- [ ] 확인한다.
**검증, 실사용.** ${rule} 부팅 절차대로 PR head에서 \`code\` 역할 모델로 검증 항목 10개를 돌린다.
${Array.from({ length: 10 }, (_, i) => `- [ ] 검증 항목 ${i + 1}. \`lane-${i + 1}.png\` 저장. 통과 조건은 증거가 있을 때.`).join("\n")}
**검증, 성능.** ${rule}
- [ ] 지표. 기록함.
- [ ] 측정. 기록함.
- [ ] 기준값. 기록함.
- [ ] 판정. 기록함.
**리뷰 게이트.** 없음.
**머지.**
- [ ] 승인되면 머지한다.

## 프로그램 마무리
마무리.

## 부록 A. 프로토타입 증거
기록함.
`;

const runPlan = (example: string, expectedExit: number) => {
	const directory = mkdtempSync(join(tmpdir(), "check-plan-test-"));
	const file = join(directory, "plan.md");
	writeFileSync(file, validPlan + example);
	try {
		const result = spawnSync("node", [checker, file], { encoding: "utf8" });
		expect(result.status).toBe(expectedExit);
		return result;
	} finally {
		rmSync(directory, { recursive: true, force: true });
	}
};

test("accepts ordinary, indented, and longer closing fences", () => {
	for (const indent of ["", " ", "  ", "   "])
		runPlan(`${indent}\`\`\`markdown\n## Example only\n${indent}\`\`\`\n`, 0);
	runPlan("```markdown\n## Example only\n````\n", 0);
});

test("accepts nested backticks and tilde info strings", () => {
	runPlan("````markdown\n```markdown\n## Example only\n```\n````\n", 0);
	runPlan("~~~markdown `info`\n## Example only\n ~~~\n", 0);
});

test("keeps mismatched, shorter, and suffixed closers inside the fence", () => {
	runPlan("````markdown\n~~~\n## Example only\n````\n", 0);
	runPlan("````markdown\n```\n## Example only\n````\n", 0);
	runPlan("````markdown\n``` info\n## Example only\n````\n", 0);
});

test("rejects headings and prose outside a proper close", () => {
	for (const suffix of ["  ", "\t"]) {
		const heading = runPlan(`\`\`\`markdown\n## Example only\n\`\`\`${suffix}\n## Example only\n`, 1);
		expect(heading.stderr).toContain('프로그램 마무리 뒤의 "## Example only"는 부록이 아님');
	}

	const prose = runPlan("```markdown\nThis prose has a mid-sentence colon: inside code\n```\nThis prose has a mid-sentence colon: bad.\n", 1);
	expect(prose.stderr).toContain("문장 중간 콜론");
});

test("rejects backtick info strings containing a backtick", () => {
	const result = runPlan("```markdown `invalid`\n## Example only\n```\n", 1);
	expect(result.stderr).toContain('프로그램 마무리 뒤의 "## Example only"는 부록이 아님');
});

test("accepts Korean prose and flags only the banned punctuation", () => {
	runPlan("한국어 문장은 가운뎃점·괄호(예시)와 시각 10:30을 써도 된다. https://example.com 도 된다.\n", 0);
	const dash = runPlan("긴 대시\u2014금지.\n", 1);
	expect(dash.stderr).toContain("긴 대시");
	const quote = runPlan("\u201c둥근 따옴표\u201d 금지.\n", 1);
	expect(quote.stderr).toContain("둥근 따옴표");
});

test("rejects a plan missing Korean structure", () => {
	const directory = mkdtempSync(join(tmpdir(), "check-plan-test-"));
	const file = join(directory, "plan.md");
	writeFileSync(file, validPlan.replace("통과 조건은 증거가 있을 때.", "끝.").replace("## 부록 A. 프로토타입 증거", "## 부록 A. 메모"));
	try {
		const result = spawnSync("node", [checker, file], { encoding: "utf8" });
		expect(result.status).toBe(1);
		expect(result.stderr).toContain("검증 항목 1에 통과 조건 없음");
		expect(result.stderr).toContain("프로토타입 증거\" 절 없음");
	} finally {
		rmSync(directory, { recursive: true, force: true });
	}
});
