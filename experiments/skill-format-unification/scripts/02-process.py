"""raw/ -> processed/*.csv. 입력은 data/raw만."""
import csv, glob, json, os, re, subprocess, sys, tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
RAW = os.path.join(EXP, "data", "raw")
OUT = os.path.join(EXP, "data", "processed")
TOOLS = os.environ.get("TOOLS", os.path.expanduser("~/.cache/skill-exp-tools"))
os.makedirs(OUT, exist_ok=True)

VERSIONS = ["before", "r1", "r2", "r3", "after"]
WRITER_FILES = ["AGENTS.md", "README.md", "docs/architecture.md",
                "docs/decisions/2026-09-20-provider-stdio.md", "docs/decisions/README.md"]

TOK_JS = r"""
const fs=require('fs');const o=require('gpt-tokenizer/encoding/o200k_base');const a=require('@anthropic-ai/tokenizer');
const files=JSON.parse(fs.readFileSync(0,'utf8'));const out={};
for(const [k,s] of Object.entries(files)){out[k]={o200k:o.encode(s).length,claude:a.countTokens(s)};}
process.stdout.write(JSON.stringify(out));
"""


def tokens(texts):
    env = dict(os.environ, NODE_PATH=os.path.join(TOOLS, "node_modules"))
    r = subprocess.run(["node", "-e", TOK_JS], input=json.dumps(texts), capture_output=True,
                       text=True, env=env, check=True)
    return json.loads(r.stdout)


def parse(s):
    name = re.search(r"^name: (.+)$", s, re.M).group(1).strip().strip('"')
    desc = re.search(r'^description: "?(.*?)"?$', s, re.M).group(1)
    body = s.split("---", 2)[2]
    base = re.search(r"^- 기반: ([a-z0-9-]+) 먼저 적용", body, re.M)
    return {"name": name, "text": s, "desc": desc, "base": base.group(1) if base else None}


def load(ver):
    skills = {}
    with tarfile.open(os.path.join(RAW, f"skills-{ver}.tar.gz")) as bundle:
        for member in bundle.getmembers():
            if member.isfile() and member.name.startswith("skills/") and member.name.endswith("/SKILL.md"):
                skills[os.path.basename(os.path.dirname(member.name))] = parse(bundle.extractfile(member).read().decode())
    return skills


NOUN_OK = ('흐름', '알림', '없음', '다음', '포함', '결함', '마음', '처음', '이름', '모음', '요금', '그림', '묶음', '느낌', '믿음', '물음', '걸음', '기본값', '보관함', '수신함')
NAME_OK = ('안 함', '막힘')
BAD_END = re.compile(r'(다|함|음|임|됨|봄|름|룸|듦|눔|힘|움|씀|셈|뺌|김|춤|침|줌|둠|꿈|옮|듬|숨|엶|앎|삶|짐|킴|림|핌|닮)$')


def check_text(s, me, names):
    errs = []
    lines = s.split('\n')
    m = re.search(r'^description: "(.*)"$', s, re.M)
    if not m:
        errs.append('description 형식')
    else:
        d = m.group(1)
        for n in names:
            if n != me and re.search(r'(?<![\w-])' + re.escape(n) + r'(?![a-z-])', d):
                errs.append('description에 다른 스킬 이름: ' + n)
        if '함께' in d:
            errs.append('description에 함께')
    if not re.search(r'^name: [a-z0-9-]+$', s, re.M):
        errs.append('name 형식')
    body = s.split('---', 2)[2].lstrip('\n').split('\n')
    if not body[0].startswith('# '):
        errs.append('제목 없음')
    head = [line for line in body[1:6] if line.startswith('- ')]
    if not head or head[0] != '- 저장소 안에 같은 역할의 규칙이 있으면 그것 우선. 없으면 이 스킬이 다른 규칙보다 우선':
        errs.append('머리 1줄')
    if len(head) < 2 or not (head[1].startswith('- 기반: ') or head[1].startswith('- 범위: ')):
        errs.append('머리 2줄')
    fence = 0
    for number, line in enumerate(lines, 1):
        if fence == 0 and line.startswith('```'):
            fence = len(line) - len(line.lstrip('`'))
            continue
        if fence and re.fullmatch('`{%d}' % fence, line.strip()):
            fence = 0
            continue
        if fence or number <= 4 or not line.strip() or line.startswith('#') or line.startswith('name:') or line.startswith('description:') or line == '---':
            continue
        text = re.sub(r'`[^`]*`', '', line)
        cells = [cell.strip() for cell in text.split('|')] if text.startswith('|') else [text]
        for cell in cells:
            cell = re.sub(r'^[-0-9. ]+', '', cell).strip().rstrip('.').strip()
            cell = re.sub(r'\([^()]*\)$', '', cell).strip()
            if not cell or set(cell) <= set('-: ') or cell in NAME_OK:
                continue
            word = cell.split()[-1]
            if BAD_END.search(word) and not word.endswith(NOUN_OK):
                errs.append(f'{number}: 끝말 {word}')
    return errs


def closure_before(sk, start):
    # 옛 구조: description에 이름이 나온 스킬을 함께 불러옴
    seen, todo = set(), list(start)
    while todo:
        n = todo.pop()
        if n in seen or n not in sk:
            continue
        seen.add(n)
        for m in sk:
            if m != n and re.search(r"(?<![\w-])" + re.escape(m) + r"(?![a-z-])", sk[n]["desc"]):
                todo.append(m)
    return seen


def closure_after(sk, start):
    # 새 구조: 기반 줄만 따라감. 조건부 스킬은 시나리오가 직접 지정
    seen, todo = set(), list(start)
    while todo:
        n = todo.pop()
        if n in seen or n not in sk:
            continue
        seen.add(n)
        if sk[n]["base"]:
            todo.append(sk[n]["base"])
    return seen


# 시나리오: (id, 요청, 옛 시작 스킬, 새 시작 스킬). 새 시작 스킬에는 조건이 참인 조건부 스킬 포함
SCENARIOS = [
    ("s01", "README 작성(그림 없음)", ["repo-docs-readme"], ["repo-docs-readme"]),
    ("s02", "README 대표 그림 교체", ["repo-docs-readme"], ["repo-docs-readme", "repo-docs-figures"]),
    ("s03", "아키텍처 문서 작성(그림 없음)", ["repo-docs-design"], ["repo-docs-design"]),
    ("s04", "아키텍처 문서와 구성 요소 그림", ["repo-docs-design"], ["repo-docs-design", "repo-docs-figures"]),
    ("s05", "명령 문서(cli.md) 작성", ["repo-docs-spec"], ["repo-docs-spec"]),
    ("s06", "판단 기록에서 결정 기록 작성", ["repo-docs-decision"], ["repo-docs-decision", "repo-docs-journal"]),
    ("s07", "실험 설계 작성", ["repo-docs-experiment"], ["repo-docs-experiment"]),
    ("s08", "실험 보고서와 결과 차트", ["repo-docs-experiment"], ["repo-docs-experiment", "repo-docs-figures"]),
    ("s09", "개발 기록 작성", ["repo-docs-note"], ["repo-docs-note"]),
    ("s10", "AGENTS.md 작성", ["repo-docs-root"], ["repo-docs-root"]),
    ("s11", "Rust 코드 작성", ["code-style-rust"], ["code-style-rust"]),
    ("s12", "Rust 리팩터링 기법 선택", ["code-style-rust"], ["code-style-rust", "code-refactoring"]),
    ("s13", "커밋 메시지 작성", ["git-commit"], ["git-commit"]),
    ("s14", "PR 본문 작성", ["git-pull-request"], ["git-pull-request"]),
]


def write(name, rows, fields):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main():
    sets = {v: load(v) for v in VERSIONS}

    # 1. 스킬별 크기
    texts = {}
    for v, sk in sets.items():
        for n, s in sk.items():
            texts[f"{v}|{n}|body"] = s["text"]
            texts[f"{v}|{n}|desc"] = f"{n}: {s['desc']}"
    tk = tokens(texts)
    rows = []
    for v, sk in sets.items():
        for n in sorted(sk):
            b, d = tk[f"{v}|{n}|body"], tk[f"{v}|{n}|desc"]
            rows.append({"version": v, "skill": n, "bytes": len(sk[n]["text"].encode()),
                         "o200k": b["o200k"], "claude_legacy": b["claude"],
                         "desc_o200k": d["o200k"], "desc_claude_legacy": d["claude"]})
    write("skill_tokens.csv", rows, list(rows[0]))
    size = {(r["version"], r["skill"]): r for r in rows}

    # 2. 시나리오별 로드량(before, after)
    srows = []
    for sid, req, st_b, st_a in SCENARIOS:
        for v, st, fn in (("before", st_b, closure_before), ("after", st_a, closure_after)):
            sk = sets[v]
            ld = sorted(fn(sk, st))
            srows.append({"scenario": sid, "request": req, "version": v, "skills": " ".join(ld),
                          "o200k": sum(size[(v, n)]["o200k"] for n in ld),
                          "claude_legacy": sum(size[(v, n)]["claude_legacy"] for n in ld),
                          "catalog_o200k": sum(size[(v, n)]["desc_o200k"] for n in sk),
                          "catalog_claude_legacy": sum(size[(v, n)]["desc_claude_legacy"] for n in sk)})
    write("scenario_load.csv", srows, list(srows[0]))

    # 3. 문체 검사
    crows = []
    for v, sk in sets.items():
        kinds = {}
        for name in sorted(sk):
            for error in check_text(sk[name]["text"], name, sk):
                kind = '끝말' if '끝말' in error else error.split(':')[0]
                kinds[kind] = kinds.get(kind, 0) + 1
        kinds['total'] = sum(kinds.values())
        for kind, count in kinds.items():
            crows.append({"version": v, "kind": kind, "count": count})
    write("style_check.csv", crows, ["version", "kind", "count"])

    # 4. 트리거
    exp = json.load(open(os.path.join(RAW, "expected.json")))
    trows = []
    for p in sorted(glob.glob(os.path.join(RAW, "trigger-*.json"))):
        run = os.path.basename(p)[8:-5]
        ver = run.rsplit("-", 1)[0]
        got = json.load(open(p))
        sk = sets[ver]
        fn = closure_before if ver == "before" else closure_after
        for k in sorted(exp, key=int):
            e, g = set(exp[k]), set(got.get(k, []))
            if ver == "before":  # 옛 구조에는 code-refactoring이 없고 code-style이 그 내용을 담음
                e = {"code-style" if x == "code-refactoring" else x for x in e}
            gc = fn(sk, g)
            trows.append({"run": run, "prompt": int(k), "expected": " ".join(sorted(e)), "chosen": " ".join(sorted(g)),
                          "hit_catalog": int(e <= g), "hit_after_base": int(e <= gc),
                          "missing": " ".join(sorted(e - gc)), "extra": " ".join(sorted(g - e))})
    write("trigger.csv", trows, list(trows[0]))

    # 5. 결정성: 같은 라운드 두 작성자의 줄 차이
    drows = []
    for rnd in ("r1", "r2", "r3", "r4"):
        a, b = os.path.join(RAW, "writers", rnd + "-1"), os.path.join(RAW, "writers", rnd + "-2")
        fa = sorted(os.path.relpath(p, a) for p in glob.glob(a + "/**", recursive=True) if os.path.isfile(p) and "READ_LOG" not in p)
        fb = sorted(os.path.relpath(p, b) for p in glob.glob(b + "/**", recursive=True) if os.path.isfile(p) and "READ_LOG" not in p)
        for f in WRITER_FILES:
            la = open(os.path.join(a, f), encoding="utf-8").read().split("\n")
            lb = open(os.path.join(b, f), encoding="utf-8").read().split("\n")
            d = subprocess.run(["diff", os.path.join(a, f), os.path.join(b, f)], capture_output=True, text=True)
            diff_lines = sum(1 for l in d.stdout.split("\n") if l.startswith("<"))
            ha = [l for l in la if l.startswith("#")]
            hb = [l for l in lb if l.startswith("#")]
            drows.append({"round": rnd, "file": f, "nonblank_lines": sum(1 for l in la if l.strip()),
                          "diff_lines": diff_lines, "same_headings": int(ha == hb),
                          "same_file_set": int(fa == fb)})
    write("determinism.csv", drows, list(drows[0]))

    # 6. 누락 대조 결과
    arows = []
    for n, name in ((1, "audit-findings.jsonl"), (2, "audit-findings-2.jsonl")):
        for l in open(os.path.join(RAW, name), encoding="utf-8"):
            if l.strip():
                arows.append({"pass": n, **json.loads(l)})
    write("audit.csv", arows, list(arows[0]))


if __name__ == "__main__":
    main()
