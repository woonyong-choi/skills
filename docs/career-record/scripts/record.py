"""경력 원본(<Vault>/career/)의 프로젝트 줄을 추가·병합·채움·수정·삭제하고 구조·등급을 검사한다.

사용: python3 record.py <명령> ... (명령: check, add, merge, fill, edit, remove, new-project, locate, screen, blanks, mode, since, stamp)
인자: 명령마다 프로젝트 폴더(경력 원본 기준 상대 경로 또는 절대 경로), --first·--line 줄 첫 줄, --set 칸=값(반복), --pr PR 주소, --yes 사용자 승인. screen의 PR JSON은 파일 또는 `-`(표준 입력)
출력: stdout JSON. 종료 0 성공·1 검사 위반 또는 위치 거부(파일 0개)·2 인자 오류·3 질문 필요(파일 0개, ask에 질문 문장)
설정: <설정 폴더>/career-record.json의 mode(normal|bypass, 기본 normal)와 last_recorded. 설정 폴더는 vault.json과 같은 곳
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 설치본(스킬 폴더 나란히)과 원본 저장소(docs/·git/) 두 배치의 git-issue 위치
for _scripts in (HERE.parents[1] / "git-issue" / "scripts", HERE.parents[2] / "git" / "git-issue" / "scripts"):
    if (_scripts / "project_context.py").is_file():
        sys.path.insert(0, str(_scripts))
        break
import project_context as pc  # noqa: E402

FIELDS = ("등급", "주체", "상황", "행동", "확인", "결과", "상태", "근거")
ATTRIBUTES = ("기간", "인원", "역할", "공개", "저장소", "기술")
LIST_ATTRIBUTES = ("저장소", "기술")
SECTIONS = ("맡은 일", "해결한 문제", "설계 결정", "구현", "결과", "남은 과제")
ORG_KEYS = ("구분", "기간", "역할 변화", "근거")
ORG_KINDS = ("재직", "교육", "개인")
MASTER_SECTIONS = ("기본", "기술", "기타")
RANK = {"상": 0, "중": 1, "하": 2}
UNKNOWN = "미확인"
LIMIT = 10
RESUME, PORTFOLIO, ORG, TEAM, MASTER = "이력서.md", "포트폴리오.md", "소속.md", "팀.md", "master.md"
PERSONAL = "개인"
POSTING = re.compile(r"^(?:\d{4}-\d{2}-\d{2}|상시)-")
QUESTIONS = {
    "주체": "혼자 했나요? 팀이면 몇 명이고 내가 맡은 부분은 무엇인가요?",
    "상황": "왜 이 작업이 필요했나요? 무엇이 불편하거나 막혔나요?",
    "행동": "무엇을 어떻게 만들었나요?",
    "확인": "잘 됐는지 무엇으로 확인했나요? (테스트, 측정, 운영 관찰)",
    "결과": "전과 후가 어떻게 달라졌나요? 숫자가 있으면 숫자로 적어 주세요",
    "상태": "끝났나요, 아직 진행 중인가요?",
    "근거": "PR이나 문서 링크가 있나요?",
    "기간": "언제부터 언제까지 했나요? (예: 2025.03 - 2025.09)",
    "인원": "몇 명이 함께 했나요?",
    "역할": "이 프로젝트에서 맡은 역할은 무엇인가요? (예: 백엔드)",
}


class RecordError(Exception):
    """위치 거부·형식 오류. 파일을 쓰기 전에만 발생"""


class Ask(Exception):
    """모드 규칙상 사용자 질문이 먼저 필요. 파일 0개"""


# cost: time O(1), heap O(1), stack O(1), io O(1)
# vars: 없음
# basis: estimate
def config_path() -> Path:
    return pc.config_directory() / "career-record.json"


# cost: time O(1), heap O(1), stack O(1), io O(1)
# vars: 없음
# basis: estimate
def read_config() -> dict:
    path = config_path()
    data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    if data.get("mode") not in ("normal", "bypass"):
        data["mode"] = "normal"
    return data


# cost: time O(1), heap O(1), stack O(1), io O(1)
# vars: 없음
# basis: estimate
def write_config(data: dict) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# cost: time O(1), heap O(1), stack O(1), io O(1)
# vars: 없음
# basis: estimate
def career_root() -> Path:
    """등록 Vault의 career 폴더. Vault 미등록이면 RecordError"""
    try:
        return (pc.resolve_vault() / "career").resolve()
    except pc.ContextError as error:
        raise RecordError(f"Vault 미등록: {error}") from error


# cost: time O(d), heap O(d), stack O(1), io O(1)
# vars: d = 경로 깊이
# basis: estimate
def guard(target: Path, root: Path) -> Path:
    """쓰기 위치 검사. <Vault>/career 아래 공고 폴더 밖만 허용"""
    target = (root / target if not target.is_absolute() else target).resolve()
    if target == root or not target.is_relative_to(root):
        raise RecordError(f"경력 원본 밖 위치 거부: {target} (허용: {root} 아래)")
    if POSTING.match(target.relative_to(root).parts[0]):
        raise RecordError("공고 폴더는 career 스킬 소유: 원본은 소속·개인 폴더 아래만")
    return target


# --- 이력서.md·포트폴리오.md 읽기·쓰기 ---


# cost: time O(n), heap O(n), stack O(1)
# vars: n = 파일 줄 수
# basis: estimate
def split_front(text: str) -> tuple[dict, str]:
    """YAML 머리(문자열 값, 문자열 목록만)와 본문"""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        raise RecordError("머리 속성 끝(---) 없음")
    attributes: dict = {}
    key = None
    for raw in text[4:end].splitlines():
        if not raw.strip():
            continue
        item = re.match(r"^\s+-\s*(.*)$", raw)
        if item and key is not None:
            attributes.setdefault(key, [])
            if not isinstance(attributes[key], list):
                raise RecordError(f"속성 {key}: 값과 목록을 함께 쓸 수 없음")
            attributes[key].append(item.group(1).strip())
            continue
        pair = re.match(r"^([^:\s][^:]*):\s*(.*)$", raw)
        if not pair:
            raise RecordError(f"속성 줄 형식: {raw}")
        key, value = pair.group(1).strip(), pair.group(2).strip()
        attributes[key] = value if value else []
    return attributes, text[end + 5:]


# cost: time O(a), heap O(a), stack O(1)
# vars: a = 속성 값 수
# basis: estimate
def join_front(attributes: dict, order: tuple[str, ...]) -> str:
    keys = [key for key in order if key in attributes] + [key for key in attributes if key not in order]
    out = ["---"]
    for key in keys:
        value = attributes[key]
        if isinstance(value, list):
            out.append(f"{key}:")
            out.extend(f"  - {item}" for item in value)
        else:
            out.append(f"{key}: {value}")
    return "\n".join(out + ["---", ""])


# cost: time O(n), heap O(n), stack O(1)
# vars: n = 본문 줄 수
# basis: estimate
def parse_lines(body: str) -> tuple[list[dict], list[str]]:
    """줄 목록(first, fields 순서 보존)과 형식 문제"""
    lines: list[dict] = []
    problems = []
    for number, raw in enumerate(body.splitlines(), 1):
        if not raw.strip():
            continue
        top = re.match(r"^- (.+)$", raw)
        sub = re.match(r"^  - ([^:]+):\s*(.*)$", raw)
        if top:
            lines.append({"first": top.group(1).strip(), "fields": []})
        elif sub and lines:
            lines[-1]["fields"].append((sub.group(1).strip(), sub.group(2).strip()))
        else:
            problems.append(f"{number}줄: 줄은 '- 첫 줄', 칸은 '  - 칸: 값' 형식")
    return lines, problems


# cost: time O(l), heap O(l), stack O(1)
# vars: l = 줄 수
# basis: estimate
def render_lines(lines: list[dict]) -> str:
    out = []
    for line in lines:
        out.append(f"- {line['first']}")
        out.extend(f"  - {key}: {value}" for key, value in line["fields"])
    return "\n".join(out) + ("\n" if out else "")


# cost: time O(n), heap O(n), stack O(1)
# vars: n = 포트폴리오.md 줄 수
# basis: estimate
def parse_bundles(text: str) -> list[dict]:
    """## 제목 묶음과 ### 절 이름 목록. 코드 울타리 안 제목은 무시"""
    bundles: list[dict] = []
    fenced = False
    for raw in text.splitlines():
        if raw.startswith("```"):
            fenced = not fenced
        if bundles:
            bundles[-1]["lines"].append(raw)
        if fenced:
            continue
        if raw.startswith("## "):
            bundles.append({"title": raw[3:].strip(), "sections": [], "lines": [raw]})
        elif raw.startswith("### ") and bundles:
            bundles[-1]["sections"].append(raw[4:].strip())
    return bundles


# cost: time O(f), heap O(1), stack O(1)
# vars: f = 칸 수
# basis: estimate
def grade(fields: dict) -> str:
    """상: 운영 결과 수치(결과에 숫자, 확인에 운영)·근거 링크·본인 주도(주체가 본인으로 시작) 셋 다. 중: 하나 빠짐. 하: 결과 미확인·단순 참여(주체가 참여로 시작)·둘 이상 빠짐"""
    result, actor = fields.get("결과", UNKNOWN), fields.get("주체", UNKNOWN)
    if result == UNKNOWN or actor.startswith("참여") or "단순 참여" in actor:
        return "하"
    missing = sum((
        not (re.search(r"\d", result) and "운영" in fields.get("확인", "")),
        not re.search(r"https?://", fields.get("근거", "")),
        not actor.startswith("본인"),
    ))
    return "상" if missing == 0 else "중" if missing == 1 else "하"


# cost: time O(l log l), heap O(l), stack O(1)
# vars: l = 줄 수
# basis: estimate
def normalize(lines: list[dict]) -> list[dict]:
    """8칸 순서로 채우고 등급 계산, 등급 순 정렬(같은 등급은 기존 순서 = 최근 먼저)"""
    for line in lines:
        values = dict(line["fields"])
        values = {key: values.get(key, UNKNOWN) or UNKNOWN for key in FIELDS}
        values["등급"] = grade(values)
        line["fields"] = [(key, values[key]) for key in FIELDS]
    return sorted(lines, key=lambda line: RANK[dict(line["fields"])["등급"]])


class Project:
    """프로젝트 폴더 하나의 이력서.md·포트폴리오.md. save 전에는 파일을 쓰지 않는다"""

    # cost: time O(n), heap O(n), stack O(1), io 2
    # vars: n = 두 파일 줄 수
    # basis: estimate
    def __init__(self, folder: Path, root: Path):
        self.folder, self.root = folder, root
        resume = folder / RESUME
        if not resume.is_file():
            raise RecordError(f"프로젝트 아님(이력서.md 없음): {self.name}")
        self.attributes, body = split_front(resume.read_text(encoding="utf-8"))
        self.lines, problems = parse_lines(body)
        if problems:
            raise RecordError(f"{self.name}/이력서.md: " + "; ".join(problems))
        portfolio = folder / PORTFOLIO
        self.portfolio = portfolio.read_text(encoding="utf-8") if portfolio.is_file() else ""

    @property
    def name(self) -> str:
        return str(self.folder.relative_to(self.root))

    # cost: time O(l), heap O(1), stack O(1)
    # vars: l = 줄 수
    # basis: estimate
    def find(self, first: str) -> dict:
        for line in self.lines:
            if line["first"] == first:
                return line
        raise RecordError(f"{self.name}: 줄 없음 \"{first}\"")

    # cost: time O(p), heap O(p), stack O(1)
    # vars: p = 포트폴리오.md 줄 수
    # basis: estimate
    def has_bundle(self, first: str) -> bool:
        return any(bundle["title"] == first for bundle in parse_bundles(self.portfolio))

    # cost: time O(p), heap O(p), stack O(1)
    # vars: p = 포트폴리오.md 줄 수
    # basis: estimate
    def drop_bundle(self, first: str) -> None:
        lines = self.portfolio.splitlines()
        bundles = parse_bundles(self.portfolio)
        preamble = lines[: len(lines) - sum(len(bundle["lines"]) for bundle in bundles)]
        kept = preamble + [raw for bundle in bundles if bundle["title"] != first for raw in bundle["lines"]]
        self.portfolio = "\n".join(kept).rstrip("\n") + "\n" if any(raw.strip() for raw in kept) else ""

    # cost: time O(l + p), heap O(l + p), stack O(1), io 2
    # vars: l = 줄 수, p = 포트폴리오.md 글자 수
    # basis: estimate
    def save(self) -> list[str]:
        self.lines = normalize(self.lines)
        (self.folder / RESUME).write_text(join_front(self.attributes, ATTRIBUTES) + "\n" + render_lines(self.lines), encoding="utf-8")
        written = [self.name + "/" + RESUME]
        if self.portfolio.strip() or (self.folder / PORTFOLIO).is_file():
            (self.folder / PORTFOLIO).write_text(self.portfolio, encoding="utf-8")
            written.append(self.name + "/" + PORTFOLIO)
        return written


# --- 모드 규칙 ---


# cost: time O(1), heap O(1), stack O(1)
# vars: 없음
# basis: estimate
def decide(mode: str, action: str, *, grade_value: str = "하", bundle: bool = False, locations: int = 1) -> str:
    """ask 또는 run. normal은 추가·병합·삭제 전부 질문. bypass는 위치 후보 여럿, 상·중 줄 삭제, 묶음 있는 줄 삭제만 질문"""
    if mode != "bypass":
        return "ask"
    if locations != 1:
        return "ask"
    if action == "remove" and (grade_value in ("상", "중") or bundle):
        return "ask"
    return "run"


# cost: time O(1), heap O(1), stack O(1)
# vars: 없음
# basis: estimate
def label(line: dict) -> str:
    values = dict(line["fields"])
    result = values.get("결과", UNKNOWN)
    return "\"" + line["first"] + (f" ({result})" if result != UNKNOWN else "") + "\""


# cost: time O(s), heap O(s), stack O(1)
# vars: s = --set 인자 수
# basis: estimate
def parse_sets(items: list[str]) -> dict:
    values = {}
    for item in items or []:
        key, sep, value = item.partition("=")
        key = key.strip()
        if not sep or key not in FIELDS[1:]:
            raise RecordError(f"--set 칸 이름은 {', '.join(FIELDS[1:])} 중 하나: {item}")
        values[key] = value.strip() or UNKNOWN
    return values


# cost: time O(1), heap O(1), stack O(1)
# vars: 없음
# basis: estimate
def append_value(old: str, new: str, sep: str) -> str:
    if old == UNKNOWN or not old:
        return new
    if new in [part.strip() for part in old.split(sep.strip())]:
        return old
    return old + sep + new


# --- 명령 ---


# cost: time O(l), heap O(l), stack O(1), io 2
# vars: l = 프로젝트 줄 수
# basis: estimate
def add(project: Project, first: str, values: dict, *, mode: str, yes: bool, similar: str | None = None,
        replace: str | None = None, locations: int = 1) -> list[str]:
    first = first.strip()
    if not first:
        raise RecordError("첫 줄이 비었음")
    if any(line["first"] == first for line in project.lines):
        raise RecordError(f"같은 첫 줄이 이미 있음: \"{first}\". 같은 작업이면 merge")
    new = normalize([{"first": first, "fields": list(values.items())}])[0]
    new_grade = dict(new["fields"])["등급"]
    report = []
    if len(project.lines) >= LIMIT:
        lowest = project.lines[-1] if replace is None else project.find(replace)
        low_grade = dict(lowest["fields"])["등급"]
        bundle = project.has_bundle(lowest["first"])
        choice = decide(mode, "remove", grade_value=low_grade, bundle=bundle, locations=locations)
        if not yes and (choice == "ask" or RANK[new_grade] >= RANK[low_grade]):
            raise Ask(
                f"{project.name}에 줄이 {LIMIT}개라 더 넣을 수 없어요. 먼저 병합할 줄이 있는지 봤나요?\n"
                f"새 줄: {label(new)} (등급 {new_grade})\n"
                f"가장 낮은 줄: {label(lowest)} (등급 {low_grade}{', 포트폴리오 묶음 있음' if bundle else ''})\n"
                "→ 가장 낮은 줄 지우고 추가 / 병합 / 건너뛰기"
            )
        project.lines.remove(lowest)
        if bundle:
            project.drop_bundle(lowest["first"])
        report.append(f"경력 삭제: {project.name} \"{lowest['first']}\" ({low_grade})")
    elif not yes and decide(mode, "add", locations=locations) == "ask":
        question = f"경력에 추가할까요? → {project.name}\n{label(new)} (등급 {new_grade})"
        if similar:
            question += f"\n비슷한 줄: \"{similar}\" → 병합 / 새 줄 / 건너뛰기"
        raise Ask(question)
    project.lines.insert(0, new)
    report.append(f"경력 추가: {project.name} \"{first}\" ({new_grade})")
    return report


# cost: time O(l), heap O(l), stack O(1), io 2
# vars: l = 프로젝트 줄 수
# basis: estimate
def merge(project: Project, first: str, values: dict, *, mode: str, yes: bool, locations: int = 1) -> list[str]:
    """결과는 ' → '로, 확인·근거는 ', '로 뒤에 붙임. 상태는 바꿈. 주체·상황·행동은 미확인일 때만 채움"""
    line = project.find(first)
    current = dict(line["fields"])
    for key, value in values.items():
        if key == "결과":
            current[key] = append_value(current.get(key, UNKNOWN), value, " → ")
        elif key in ("확인", "근거"):
            current[key] = append_value(current.get(key, UNKNOWN), value, ", ")
        elif key == "상태":
            current[key] = value
        elif current.get(key, UNKNOWN) == UNKNOWN:
            current[key] = value
    preview = normalize([{"first": first, "fields": list(current.items())}])[0]
    new_grade = dict(preview["fields"])["등급"]
    if not yes and decide(mode, "merge", locations=locations) == "ask":
        raise Ask(f"경력에 병합할까요? → {project.name}\n{label(preview)} (등급 {new_grade})\n→ 병합 / 새 줄 / 건너뛰기")
    line["fields"] = preview["fields"]
    project.lines.remove(line)
    project.lines.insert(0, line)
    return [f"경력 병합: {project.name} \"{first}\" ({new_grade})"]


# cost: time O(l), heap O(1), stack O(1), io 2
# vars: l = 프로젝트 줄 수
# basis: estimate
def fill(project: Project, first: str, values: dict) -> list[str]:
    """빈칸 답 반영. 미확인 칸만 채움, 이미 값이 있으면 거부(병합·수정 사용)"""
    line = project.find(first)
    current = dict(line["fields"])
    for key, value in values.items():
        if current.get(key, UNKNOWN) != UNKNOWN:
            raise RecordError(f"\"{first}\" {key}: 이미 값이 있음. 새 측정은 merge, 고침은 edit")
        current[key] = value
    line["fields"] = list(current.items())
    return [f"경력 채움: {project.name} \"{first}\" {', '.join(values)}"]


# cost: time O(l), heap O(1), stack O(1), io 2
# vars: l = 프로젝트 줄 수
# basis: estimate
def edit(project: Project, first: str, values: dict, new_first: str | None) -> list[str]:
    """상태 변화·오류 고침. 첫 줄을 바꾸면 짝 묶음 제목도 함께"""
    line = project.find(first)
    current = dict(line["fields"])
    current.update(values)
    line["fields"] = list(current.items())
    if new_first and new_first != first:
        if any(other["first"] == new_first for other in project.lines):
            raise RecordError(f"같은 첫 줄이 이미 있음: \"{new_first}\"")
        line["first"] = new_first
        project.portfolio = re.sub(rf"^## {re.escape(first)}$", f"## {new_first}", project.portfolio, flags=re.M)
    return [f"경력 수정: {project.name} \"{line['first']}\""]


# cost: time O(l + p), heap O(p), stack O(1), io 2
# vars: l = 줄 수, p = 포트폴리오.md 줄 수
# basis: estimate
def remove(project: Project, first: str, *, mode: str, yes: bool) -> list[str]:
    line = project.find(first)
    line_grade = dict(line["fields"]).get("등급", "하")
    bundle = project.has_bundle(first)
    if not yes and decide(mode, "remove", grade_value=line_grade, bundle=bundle) == "ask":
        raise Ask(f"경력에서 지울까요? → {project.name}\n{label(line)} (등급 {line_grade}{', 포트폴리오 묶음도 함께 지움' if bundle else ''})\n→ 지우기 / 두기")
    project.lines.remove(line)
    if bundle:
        project.drop_bundle(first)
    return [f"경력 삭제: {project.name} \"{first}\" ({line_grade})"]


# cost: time O(f), heap O(f), stack O(d), io O(f)
# vars: f = career 아래 파일 수, d = 폴더 깊이
# basis: estimate
def projects(root: Path) -> list[Path]:
    return sorted(
        path.parent for path in root.rglob(RESUME)
        if not POSTING.match(path.relative_to(root).parts[0])
    )


DOC_FILE = re.compile(r"(?:^|/)(?:docs?/.*|[^/]+\.(?:md|mdx|txt|rst|adoc)|LICENSE[^/]*|\.github/ISSUE_TEMPLATE/.*)$", re.I)
DEPENDENCY_FILE = re.compile(r"(?:^|/)(?:package(?:-lock)?\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|Pipfile\.lock|requirements[^/]*\.txt|Cargo\.(?:toml|lock)|go\.(?:mod|sum)|Gemfile\.lock|gradle\.lockfile|libs\.versions\.toml)$")
EXCLUDED_TYPE = re.compile(r"^(?:docs|style)(?:\([^)]*\))?!?:|^(?:chore|build)\(deps[^)]*\)!?:", re.I)


# cost: time O(f), heap O(f), stack O(1)
# vars: f = PR 변경 파일 수
# basis: estimate
def screen(pr: dict, user: str) -> dict:
    """기계로 가를 수 있는 제외만 판정(gh pr view --json author,title,files,url). 나머지는 AI가 본문·코드로 판단"""
    author = ((pr.get("author") or {}).get("login") or "").lower()
    if author != user.lower():
        return {"skip": f"사용자 계정 PR 아님: {author or '작성자 미확인'}"}
    files = [item.get("path", "") for item in pr.get("files") or []]
    title = pr.get("title", "")
    if EXCLUDED_TYPE.match(title):
        return {"skip": "문서·포맷·의존성 PR"}
    if files and all(DEPENDENCY_FILE.search(path) for path in files):
        return {"skip": "의존성 버전만 바뀜"}
    if files and all(DOC_FILE.search(path) for path in files):
        return {"skip": "문서만 바뀜"}
    return {
        "judge": "동작·결과 변화(기능 추가, 성능 개선, 장애·버그 해결, 구조 변경, 운영 자동화)와 검증(테스트, 측정, 운영 관찰)을 PR 본문·코드로 확인. 이름만 바꾼 PR은 제외",
        "tests_changed": any(re.search(r"(?:^|/)(?:tests?|__tests__|spec)/|[._-](?:test|spec)\.", path) for path in files),
        "pr": pr.get("url"),
    }


# cost: time O(1), heap O(1), stack O(1)
# vars: 없음
# basis: estimate
def identity(remote: str) -> str:
    """원격 주소의 host/owner/repo 소문자. https·ssh·.git 차이 무시, 해석 불가면 원문"""
    try:
        return pc.normalize_remote(remote.strip()).lower()
    except pc.ContextError:
        return remote.strip().lower()


# cost: time O(f), heap O(f), stack O(d), io O(f)
# vars: f = career 아래 파일 수, d = 폴더 깊이
# basis: estimate
def locate(root: Path, remote: str, author: str | None) -> dict:
    """저장소 원격과 이력서.md 저장소 속성 대조. 1개면 위치, 여럿·0개면 질문 후보"""
    target = identity(remote)
    parts = target.split("/")
    owner, repo = (parts[1], parts[2].removesuffix(".git")) if len(parts) >= 3 else ("", target)
    matches = []
    for folder in projects(root):
        attributes, _ = split_front((folder / RESUME).read_text(encoding="utf-8"))
        repos = attributes.get("저장소") or []
        if isinstance(repos, str):
            repos = [repos]
        if any(item != UNKNOWN and identity(item) == target for item in repos):
            matches.append(str(folder.relative_to(root)))
    personal = bool(author) and owner.lower() == author.lower()
    if len(matches) == 1:
        return {"location": matches[0], "personal": personal}
    if matches:
        return {"ask": "어느 프로젝트에 넣을까요?\n" + "\n".join(f"{i}. {m}" for i, m in enumerate(matches, 1)), "candidates": matches, "personal": personal}
    recent = sorted(projects(root), key=lambda folder: max(p.stat().st_mtime for p in folder.iterdir() if p.is_file()), reverse=True)[:3]
    candidates = ([f"{PERSONAL}/{repo} (새 프로젝트)"] if personal else []) + [str(f.relative_to(root)) for f in recent] + ["새 프로젝트(소속 선택)"]
    return {"ask": "어느 프로젝트에 넣을까요?\n" + "\n".join(f"{i}. {c}" for i, c in enumerate(candidates, 1)), "candidates": candidates, "personal": personal}


# cost: time O(f), heap O(f), stack O(d), io O(f)
# vars: f = career 아래 파일 수, d = 폴더 깊이
# basis: estimate
def blanks(root: Path) -> str:
    items = []
    for folder in projects(root):
        project = Project(folder, root)
        for key in ("기간", "인원", "역할"):
            if project.attributes.get(key, UNKNOWN) in (UNKNOWN, "", []):
                items.append(f"{project.name} - {key}: {QUESTIONS[key]}")
        for line in project.lines:
            for key, value in line["fields"]:
                if value == UNKNOWN and key in QUESTIONS:
                    items.append(f"{project.name} {line['first']} - {key}: {QUESTIONS[key]}")
    if not items:
        return "채울 칸 없음"
    return f"채워 주세요 ({len(items)}개)\n" + "\n".join(f"{i}. {item}" for i, item in enumerate(items, 1))


# cost: time O(n), heap O(n), stack O(1), io 1
# vars: n = 파일 글자 수
# basis: estimate
def parent_names(path: Path, root: Path) -> list[str]:
    """파일 안에 쓰면 안 되는 상위 폴더 이름(소속·팀). 개인은 일반 낱말이라 제외"""
    names = list(path.parent.relative_to(root).parts)
    if path.name in (RESUME, PORTFOLIO):
        names = names[:-1]
    return [name for name in names if name != PERSONAL and len(name) >= 2]


# cost: time O(f·n), heap O(n), stack O(d), io O(f)
# vars: f = career 아래 파일 수, n = 파일 하나 글자 수, d = 폴더 깊이
# basis: estimate
def check(root: Path) -> list[str]:
    problems = []
    if (root / "cases").exists():
        problems.append("cases/ 폐지: 사례는 프로젝트 폴더의 포트폴리오.md 묶음으로 이동")
    master = root / MASTER
    if master.is_file():
        heads = re.findall(r"^# (.+)$", master.read_text(encoding="utf-8"), re.M)
        extra = [head for head in heads if head.strip() not in MASTER_SECTIONS]
        if extra:
            problems.append(f"master.md 절은 {', '.join(MASTER_SECTIONS)}만: {', '.join(extra)} 이동(소속 → 소속.md, 프로젝트 → 프로젝트 폴더)")
    for org_file in sorted(root.glob(f"*/{ORG}")):
        attributes, _ = split_front(org_file.read_text(encoding="utf-8"))
        name = org_file.parent.name
        missing = [key for key in ORG_KEYS if key not in attributes]
        if missing:
            problems.append(f"{name}/소속.md 속성 없음: {', '.join(missing)}")
        if attributes.get("구분") not in ORG_KINDS:
            problems.append(f"{name}/소속.md 구분은 {'|'.join(ORG_KINDS)}")
        if name == PERSONAL and attributes.get("구분") != PERSONAL:
            problems.append("개인/소속.md 구분: 개인")
    for folder in projects(root):
        name = str(folder.relative_to(root))
        parent = folder.parent
        org = parent if (parent / ORG).is_file() else parent.parent if (parent / TEAM).is_file() and (parent.parent / ORG).is_file() else None
        if org is None or org.parent != root:
            problems.append(f"{name}: 프로젝트는 {{소속}}/ 또는 {{소속}}/{{팀}}/ 아래, 소속 폴더에 소속.md·팀 폴더에 팀.md 필요")
        try:
            project = Project(folder, root)
        except RecordError as error:
            problems.append(str(error))
            continue
        missing = [key for key in ATTRIBUTES if key not in project.attributes]
        if missing:
            problems.append(f"{name}/이력서.md 속성 없음: {', '.join(missing)}")
        if project.attributes.get("공개") not in ("공개", "비공개", UNKNOWN, None):
            problems.append(f"{name}/이력서.md 공개: 공개|비공개|미확인")
        for key in LIST_ATTRIBUTES:
            if key in project.attributes and not isinstance(project.attributes[key], list):
                problems.append(f"{name}/이력서.md {key}: 목록(  - 값)")
        if len(project.lines) > LIMIT:
            problems.append(f"{name}: 줄 {len(project.lines)}개, {LIMIT}개 이하")
        firsts = [line["first"] for line in project.lines]
        if len(set(firsts)) != len(firsts):
            problems.append(f"{name}: 같은 첫 줄 중복")
        ranks = []
        for line in project.lines:
            keys = [key for key, _ in line["fields"]]
            if keys != list(FIELDS):
                problems.append(f"{name} \"{line['first']}\": 칸 순서 {', '.join(FIELDS)} 필요(빈칸은 미확인)")
                continue
            values = dict(line["fields"])
            if values["등급"] != grade(values):
                problems.append(f"{name} \"{line['first']}\": 등급 {values['등급']} → 계산값 {grade(values)}")
            ranks.append(RANK.get(values["등급"], 9))
        if ranks != sorted(ranks):
            problems.append(f"{name}: 줄 순서는 등급(상 → 중 → 하)")
        seen = set()
        for bundle in parse_bundles(project.portfolio):
            if bundle["title"] not in firsts:
                problems.append(f"{name}/포트폴리오.md 짝 없는 묶음: \"{bundle['title']}\" (제목 = 이력서.md 줄 첫 줄)")
            if bundle["title"] in seen:
                problems.append(f"{name}/포트폴리오.md 묶음 중복: \"{bundle['title']}\"")
            seen.add(bundle["title"])
            if bundle["sections"] != list(SECTIONS):
                problems.append(f"{name}/포트폴리오.md \"{bundle['title']}\" 절: {', '.join(SECTIONS)} 순서 필요")
    for path in sorted([*root.rglob(RESUME), *root.rglob(PORTFOLIO), *root.rglob(TEAM)]):
        if POSTING.match(path.relative_to(root).parts[0]):
            continue
        text = path.read_text(encoding="utf-8")
        for parent in parent_names(path, root):
            if parent in text:
                problems.append(f"{path.relative_to(root)}: 상위 폴더 이름 \"{parent}\" 금지(소속·팀은 폴더 위치로만)")
    return problems


# cost: time O(1), heap O(1), stack O(1), io O(1)
# vars: 없음
# basis: estimate
def new_project(root: Path, relative: str, attributes: dict, org: dict) -> list[str]:
    folder = guard(Path(relative), root)
    parts = folder.relative_to(root).parts
    if len(parts) not in (2, 3):
        raise RecordError("새 프로젝트 위치: {소속}/{프로젝트} 또는 {소속}/{팀}/{프로젝트}")
    if (folder / RESUME).exists():
        raise RecordError(f"이미 있는 프로젝트: {relative}")
    org_folder = root / parts[0]
    planned = []
    if not (org_folder / ORG).is_file():
        kind = org.get("구분") or (PERSONAL if parts[0] == PERSONAL else None)
        if kind not in ORG_KINDS:
            raise RecordError(f"새 소속 {parts[0]}: --org 구분={'|'.join(ORG_KINDS)} 필요")
        values = {key: org.get(key, UNKNOWN) for key in ORG_KEYS}
        values["구분"] = kind
        planned.append((org_folder / ORG, join_front(values, ORG_KEYS)))
    if len(parts) == 3 and not (root / parts[0] / parts[1] / TEAM).is_file():
        planned.append((root / parts[0] / parts[1] / TEAM, join_front({"기간": UNKNOWN, "역할": UNKNOWN}, ("기간", "역할"))))
    values = {key: ([] if key in LIST_ATTRIBUTES else UNKNOWN) for key in ATTRIBUTES}
    values.update(attributes)
    planned.append((folder / RESUME, join_front(values, ATTRIBUTES)))
    for path, text in planned:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return [str(path.relative_to(root)) for path, _ in planned]


# cost: time O(a), heap O(a), stack O(1)
# vars: a = 인자 수
# basis: estimate
def attribute_sets(items: list[str], allowed: tuple[str, ...]) -> dict:
    values: dict = {}
    for item in items or []:
        key, sep, value = item.partition("=")
        key = key.strip()
        if not sep or key not in allowed:
            raise RecordError(f"속성 이름은 {', '.join(allowed)} 중 하나: {item}")
        if key in LIST_ATTRIBUTES:
            values.setdefault(key, []).extend(part.strip() for part in value.split(",") if part.strip())
        else:
            values[key] = value.strip() or UNKNOWN
    return values


# cost: time O(1), heap O(1), stack O(1)
# vars: 없음
# basis: estimate
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="경력 원본 기록")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check").add_argument("--root", type=Path)
    for name in ("add", "merge", "fill", "edit", "remove"):
        command = commands.add_parser(name)
        command.add_argument("project")
        command.add_argument("--first" if name == "add" else "--line", required=True, dest="first")
        if name != "remove":
            command.add_argument("--set", action="append", default=[])
        if name in ("add", "merge"):
            command.add_argument("--pr")
            command.add_argument("--locations", type=int, default=1)
        if name in ("add", "merge", "remove"):
            command.add_argument("--yes", action="store_true")
        if name == "add":
            command.add_argument("--similar")
            command.add_argument("--replace")
        if name == "edit":
            command.add_argument("--new-first")
    created = commands.add_parser("new-project")
    created.add_argument("project")
    created.add_argument("--set", action="append", default=[])
    created.add_argument("--org", action="append", default=[])
    located = commands.add_parser("locate")
    located.add_argument("--remote", required=True)
    located.add_argument("--author")
    screened = commands.add_parser("screen")
    screened.add_argument("pr_json", type=Path)
    screened.add_argument("--user", required=True)
    commands.add_parser("blanks")
    mode = commands.add_parser("mode")
    mode.add_argument("value", nargs="?", choices=("normal", "bypass"))
    commands.add_parser("since")
    stamp = commands.add_parser("stamp")
    stamp.add_argument("--at")
    return parser


# cost: time O(f·n), heap O(n), stack O(d), io O(f)
# vars: f = career 아래 파일 수, n = 파일 하나 글자 수, d = 폴더 깊이
# basis: estimate
def run(argv: list[str]) -> tuple[int, dict]:
    args = build_parser().parse_args(argv)
    config = read_config()
    if args.command == "mode":
        if args.value:
            write_config({**config, "mode": args.value})
        return 0, {"mode": args.value or config["mode"]}
    if args.command == "since":
        return 0, {"last_recorded": config.get("last_recorded")}
    if args.command == "stamp":
        at = args.at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        write_config({**config, "last_recorded": at})
        return 0, {"last_recorded": at}
    if args.command == "screen":
        return 0, screen(json.loads(sys.stdin.read() if str(args.pr_json) == "-" else args.pr_json.read_text(encoding="utf-8")), args.user)
    root = career_root() if args.command != "check" or args.root is None else args.root.resolve()
    if args.command == "check":
        problems = check(root)
        return (1 if problems else 0), {"problems": problems}
    if args.command == "locate":
        return 0, locate(root, args.remote, args.author)
    if args.command == "blanks":
        return 0, {"blanks": blanks(root)}
    if args.command == "new-project":
        files = new_project(root, args.project, attribute_sets(args.set, ATTRIBUTES), attribute_sets(args.org, ORG_KEYS))
        return 0, {"files": files}
    folder = guard(Path(args.project), root)
    project = Project(folder, root)
    values = parse_sets(getattr(args, "set", []))
    if getattr(args, "pr", None):
        values["근거"] = append_value(values.get("근거", UNKNOWN), args.pr, ", ")
    mode = config["mode"]
    if args.command == "add":
        report = add(project, args.first, values, mode=mode, yes=args.yes, similar=args.similar, replace=args.replace, locations=args.locations)
    elif args.command == "merge":
        report = merge(project, args.first, values, mode=mode, yes=args.yes, locations=args.locations)
    elif args.command == "fill":
        report = fill(project, args.first, values)
    elif args.command == "edit":
        report = edit(project, args.first, values, args.new_first)
    else:
        report = remove(project, args.first, mode=mode, yes=args.yes)
    return 0, {"report": report, "files": project.save(), "mode": mode}


# cost: time O(f·n), heap O(n), stack O(d), io O(f)
# vars: f = career 아래 파일 수, n = 파일 하나 글자 수, d = 폴더 깊이
# basis: estimate
def main(argv: list[str] | None = None) -> int:
    try:
        code, result = run(sys.argv[1:] if argv is None else argv)
    except Ask as question:
        code, result = 3, {"ask": str(question), "files": []}
    except RecordError as error:
        code, result = 1, {"error": str(error), "files": []}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
