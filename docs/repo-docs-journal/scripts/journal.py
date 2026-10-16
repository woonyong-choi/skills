"""판단 기록의 기록 기준 판정, 저장 경로 계산·검사, 기록 형식 검사, 놓친 것 모으기, 모드 설정.

사용: python3 journal.py <명령> ... (명령: screen, path, check, misses, mode)
인자: screen은 --source 근거 파일(반복)·--alternative·--assumption 인용문·--structure 목록 이름, path는 --kind·--topic·선택 --date·--project
출력: stdout JSON. 종료 0 통과·1 기준 미충족·형식 위반·위치 거부(파일 0개)·2 인자 오류
설정: <설정 폴더>/journal.json의 mode(normal|bypass, 기본 normal). 설정 폴더는 vault.json과 같은 곳
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 설치본(스킬 폴더 나란히)과 원본 저장소(docs/·git/) 두 배치의 git-issue 위치
for _scripts in (HERE.parents[1] / "git-issue" / "scripts", HERE.parents[2] / "git" / "git-issue" / "scripts"):
    if (_scripts / "project_context.py").is_file():
        sys.path.insert(0, str(_scripts))
        break
import project_context as pc  # noqa: E402

STRUCTURES = (
    "저장 위치",
    "폴더·파일 구조",
    "데이터 형식",
    "저장소·스킬 사이 경계와 역할",
    "외부 계약(명령·설정·API)",
    "작업 흐름(언제 무엇이 자동으로 도는지)",
)
# 확인하지 못한 전제를 드러내는 말. 인용문에 하나 이상 필요
ASSUMPTION_MARKERS = ("아마", "일 것", "할 것", "될 것", "고 보고", "라고 가정", "가정하고", "가정해", "확인 안 했", "확인하지 않", "확인 못", "추정", "것 같", "듯하", "으로 보고", "로 보고")
KINDS = {"판단": "판단", "판단 변경": "판단", "작업 일지": "작업일지"}
PRINCIPLES = "principles.md"
NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)\.md$")
HANGUL = re.compile(r"[가-힣]")
OLD_HEAD = re.compile(r"^\|\s*항목\s*\|\s*값\s*\|", re.M)
OLD_TABLE = re.compile(r"^\|\s*확인한 근거\s*\|\s*남은 가정\s*\|", re.M)
WIKI = re.compile(r"\[\[([^\]|#]+)")


class JournalError(Exception):
    """위치 거부·형식 오류. 파일을 쓰기 전에만 발생"""


# cost: time O(n), heap O(n), stack O(1)
# vars: n = 글자 수
# basis: estimate
def squash(text: str) -> str:
    """인용 대조용: 공백·줄바꿈·Markdown 강조 기호 무시"""
    return re.sub(r"[\s*_`>]+", "", text)


# cost: time O(s·q), heap O(s), stack O(1)
# vars: s = 근거 글자 수, q = 인용 글자 수
# basis: estimate
def screen(sources: list[str], alternative: str, assumption: str, structure: str) -> dict:
    """기록 기준 세 칸. 대안·가정은 근거 원문에 그대로 있는 인용, 구조는 목록 이름. 하나라도 못 대면 탈락"""
    corpus = squash("\n".join(sources))
    reasons = []
    if not alternative.strip():
        reasons.append("대안 문장 없음")
    elif squash(alternative) not in corpus:
        reasons.append("대안 인용이 근거 원문에 없음")
    if not assumption.strip():
        reasons.append("가정 문장 없음")
    elif squash(assumption) not in corpus:
        reasons.append("가정 인용이 근거 원문에 없음")
    elif not any(marker in assumption for marker in ASSUMPTION_MARKERS):
        reasons.append("가정 문장 없음(확인하지 못한 전제를 드러내는 말 없음)")
    if structure not in STRUCTURES:
        reasons.append(f"구조 목록 밖: {structure or '없음'}")
    if reasons:
        return {"pass": False, "reason": "기록 기준 미충족: " + ", ".join(reasons)}
    return {"pass": True, "criteria": {"대안": alternative.strip(), "가정": assumption.strip(), "구조": structure}}


# cost: time O(1), heap O(1), stack O(1)
# vars: 없음
# basis: estimate
def topic_slug(topic: str) -> str:
    """주제 한국어 2~5단어 → 공백을 `-`로. 한글 없음·단어 수 밖·경로 문자면 JournalError"""
    words = topic.split()
    if not 2 <= len(words) <= 5:
        raise JournalError(f"주제는 2~5단어: {topic}")
    if not HANGUL.search(topic):
        raise JournalError(f"비공개 기록 이름은 한국어: {topic}")
    if re.search(r"[/\\:*?\"<>|_]", topic):
        raise JournalError(f"주제에 경로·특수 문자 금지: {topic}")
    return "-".join(words)


# cost: time O(p), heap O(p), stack O(1), io O(p)
# vars: p = 등록 프로젝트 수
# basis: estimate
def target(kind: str, topic: str, day: str, project_path: Path | None) -> dict:
    """저장 경로 계산과 검사. 등록 프로젝트면 영역 docs/, 아니면 Vault legacy/. 실패면 JournalError(파일 0개)"""
    if kind not in KINDS:
        raise JournalError(f"종류는 {', '.join(KINDS)} 중 하나")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise JournalError(f"날짜 형식 YYYY-MM-DD: {day}")
    name = f"{day}-{topic_slug(topic)}.md"
    try:
        vault = pc.resolve_vault()
    except pc.ContextError as error:
        raise JournalError(f"Vault 미등록: {error}") from error
    project = None
    if project_path is not None:
        try:
            project = pc.check_project(project_path)
        except (pc.ContextError, OSError, ValueError, IndexError):
            project = None
    folder = (Path(project["area"]) / "docs" if project else vault / "legacy") / KINDS[kind]
    path = (folder / name).resolve()
    try:
        if project:
            pc.check_write(project, path)
        elif not path.is_relative_to((vault / "legacy").resolve()):
            raise pc.ContextError("legacy 밖")
    except pc.ContextError as error:
        raise JournalError(f"쓰기 위치 거부: {error}") from error
    return {"path": str(path), "scope": "project" if project else "legacy", "principles": str(vault.resolve() / PRINCIPLES)}


# cost: time O(n), heap O(n), stack O(1)
# vars: n = 파일 줄 수
# basis: estimate
def front(text: str) -> dict:
    """Obsidian 속성(YAML 머리). 문자열과 문자열 목록만"""
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        return {}
    values: dict = {}
    key = None
    for raw in text[4:text.index("\n---\n", 4)].splitlines():
        item = re.match(r"^\s+-\s*(.*)$", raw)
        if item and key:
            values.setdefault(key, [])
            if isinstance(values[key], list):
                values[key].append(item.group(1).strip().strip('"'))
            continue
        pair = re.match(r"^([^:\s][^:]*):\s*(.*)$", raw)
        if pair:
            key = pair.group(1).strip()
            values[key] = pair.group(2).strip().strip('"') or []
    return values


# cost: time O(n), heap O(n), stack O(1), io 1
# vars: n = 파일 글자 수
# basis: estimate
def check_record(path: Path) -> list[str]:
    """판단·판단 변경·작업 일지 한 파일의 이름·속성·옛 양식 검사"""
    text = path.read_text(encoding="utf-8")
    problems = []
    match = NAME.match(path.name)
    if not match:
        problems.append(f"{path.name}: 이름은 {{YYYY-MM-DD}}-{{주제}}.md")
    else:
        try:
            topic_slug(match.group(2).replace("-", " "))
        except JournalError as error:
            problems.append(f"{path.name}: {error}")
    values = front(text)
    for key in ("날짜", "종류", "관련"):
        if key not in values:
            problems.append(f"{path.name}: 속성 {key} 없음")
    kind = values.get("종류")
    if kind not in KINDS:
        problems.append(f"{path.name}: 종류는 {'|'.join(KINDS)}")
    elif path.parent.name != KINDS[kind]:
        problems.append(f"{path.name}: {kind}는 {KINDS[kind]}/ 폴더")
    if match and values.get("날짜") != match.group(1):
        problems.append(f"{path.name}: 날짜 속성과 파일 이름 날짜 다름")
    if kind == "판단 변경":
        previous = values.get("이전 판단")
        links = WIKI.findall(previous if isinstance(previous, str) else " ".join(previous or []))
        if not links:
            problems.append(f"{path.name}: 판단 변경은 이전 판단 속성에 [[기록]] 링크 필수")
        for link in links:
            if not any(candidate.stem == link.strip() for candidate in path.parent.glob("*.md")):
                problems.append(f"{path.name}: 이전 판단 [[{link}]] 파일 없음")
    if OLD_HEAD.search(text):
        problems.append(f"{path.name}: 머리 | 항목 | 값 | 표 대신 속성(YAML)")
    if OLD_TABLE.search(text):
        problems.append(f"{path.name}: 판단 절의 확인한 근거 | 남은 가정 표 삭제(알던 것과 모르던 것과 중복)")
    if "서사" in text:
        problems.append(f"{path.name}: 서사 → 작업 일지")
    return problems


# cost: time O(n), heap O(n), stack O(1), io 1
# vars: n = principles.md 글자 수
# basis: estimate
def check_principles(path: Path) -> list[str]:
    """원칙 절마다 링크 2개 이상(두 번째 같은 원인에서 생성), 링크 수 내림차순"""
    text = path.read_text(encoding="utf-8")
    sections = re.split(r"^## ", text, flags=re.M)[1:]
    counts = []
    problems = []
    for section in sections:
        title = section.splitlines()[0].strip()
        links = len(WIKI.findall(section))
        if links < 2:
            problems.append(f"principles.md \"{title}\": 링크 {links}개, 같은 원인이 두 번째 나올 때 생성(링크 2개 이상)")
        counts.append(links)
    if counts != sorted(counts, reverse=True):
        problems.append("principles.md: 절 순서는 링크 수 내림차순")
    return problems


# cost: time O(f·n), heap O(n), stack O(d), io O(f)
# vars: f = 기록 파일 수, n = 파일 하나 글자 수, d = 폴더 깊이
# basis: estimate
def record_files(vault: Path) -> list[Path]:
    roots = [vault / "legacy", *sorted((vault / "worktree").glob("*/docs"))]
    return sorted(path for root in roots for folder in sorted(set(KINDS.values())) for path in (root / folder).glob("*.md"))


# cost: time O(f·n), heap O(f), stack O(d), io O(f)
# vars: f = 판단 변경 파일 수, n = 파일 하나 글자 수, d = 폴더 깊이
# basis: estimate
def misses(vault: Path) -> list[dict]:
    """모든 판단 변경의 놓친 것 표 행(분류, 원인, 기록). 같은 분류·원인 두 번째면 원칙 생성"""
    rows = []
    for path in record_files(vault):
        text = path.read_text(encoding="utf-8")
        if front(text).get("종류") != "판단 변경" or "## 놓친 것" not in text:
            continue
        table = text.split("## 놓친 것", 1)[1].split("\n## ", 1)[0]
        for line in table.splitlines():
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and line.startswith("|") and cells[0] not in ("분류", "") and not set(cells[0]) <= {"-", ":"}:
                rows.append({"분류": cells[0], "원인": cells[1], "기록": path.stem})
    return rows


# cost: time O(1), heap O(1), stack O(1), io O(1)
# vars: 없음
# basis: estimate
def config(mode: str | None = None) -> dict:
    path = pc.config_directory() / "journal.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    if mode:
        data["mode"] = mode
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if data.get("mode") not in ("normal", "bypass"):
        data["mode"] = "normal"
    return data


# cost: time O(f·n), heap O(n), stack O(d), io O(f)
# vars: f = 검사 파일 수, n = 파일 하나 글자 수, d = 폴더 깊이
# basis: estimate
def run(argv: list[str]) -> tuple[int, dict]:
    parser = argparse.ArgumentParser(description="판단 기록")
    commands = parser.add_subparsers(dest="command", required=True)
    screened = commands.add_parser("screen")
    screened.add_argument("--source", action="append", type=Path, required=True)
    screened.add_argument("--alternative", default="")
    screened.add_argument("--assumption", default="")
    screened.add_argument("--structure", default="")
    located = commands.add_parser("path")
    located.add_argument("--kind", required=True)
    located.add_argument("--topic", required=True)
    located.add_argument("--date", default=date.today().isoformat())
    located.add_argument("--project", type=Path, default=Path.cwd())
    checked = commands.add_parser("check")
    checked.add_argument("files", nargs="*", type=Path)
    commands.add_parser("misses")
    mode = commands.add_parser("mode")
    mode.add_argument("value", nargs="?", choices=("normal", "bypass"))
    args = parser.parse_args(argv)
    if args.command == "screen":
        result = screen([path.read_text(encoding="utf-8") for path in args.source], args.alternative, args.assumption, args.structure)
        return (0 if result["pass"] else 1), result
    if args.command == "mode":
        return 0, {"mode": config(args.value)["mode"]}
    if args.command == "path":
        return 0, target(args.kind, args.topic, args.date, args.project)
    try:
        vault = pc.resolve_vault()
    except pc.ContextError as error:
        raise JournalError(f"Vault 미등록: {error}") from error
    if args.command == "misses":
        return 0, {"rows": misses(vault)}
    files = args.files or [*record_files(vault), *([vault / PRINCIPLES] if (vault / PRINCIPLES).is_file() else [])]
    problems = []
    for path in files:
        problems += check_principles(path) if path.name == PRINCIPLES else check_record(path)
    return (1 if problems else 0), {"problems": problems}


# cost: time O(f·n), heap O(n), stack O(d), io O(f)
# vars: f = 검사 파일 수, n = 파일 하나 글자 수, d = 폴더 깊이
# basis: estimate
def main(argv: list[str] | None = None) -> int:
    try:
        code, result = run(sys.argv[1:] if argv is None else argv)
    except JournalError as error:
        code, result = 1, {"error": str(error)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
