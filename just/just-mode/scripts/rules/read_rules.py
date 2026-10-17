"""편집할 코드 파일에 맞는 규칙 원문(원칙 파일, code-style 절, 언어별 스킬)을 골라 출력한다.

사용:
  python3 read_rules.py <파일...>            편집할 파일의 종류·내용으로 고른 규칙 원문
  python3 read_rules.py --ids <ID...>        지정한 규칙 원문
  python3 read_rules.py --pending <상태 파일>  훅 상태에서 아직 전달되지 않은 원문(12000바이트 단위)
  python3 read_rules.py --check              대응표의 sha256과 현재 원문 대조
인자: 대응표는 같은 폴더의 rule-map.json. 파일 경로는 현재 폴더 기준
출력: stdout 원문, stderr 진단. 성공 0, --check 불일치 1, 입력·읽기 오류 2(부분 출력 없음)
실행 조건: Python 3.9 이상·표준 라이브러리. 원본 저장소(분류 폴더)와 평탄한 설치 구조 지원
"""

from __future__ import annotations

__all__ = ["collect_tool_output", "edit_targets", "main", "pending_rules", "select_for_tool", "select_query"]

import argparse
import hashlib
import json
import re
import shlex
import sys
from pathlib import Path
from typing import Callable

MAP = Path(__file__).resolve().with_name("rule-map.json")
CATEGORIES = ("just", "code", "docs", "git", "design", "tools")
BATCH_BYTES = 12000
DONE = "필수 원문 전달 완료. 같은 원문 재조회 없이 적용."
MORE = "\n\n미전달 원문이 남아 있습니다. 같은 --pending 명령으로 이어서 조회하세요.\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="*", metavar="file")
    parser.add_argument("--ids", nargs="+")
    parser.add_argument("--pending", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if sum(map(bool, (args.files, args.ids, args.pending, args.check))) != 1:
        parser.error("give files, --ids, --pending or --check (exactly one)")
    try:
        catalog = read_catalog()
        if args.check:
            return check(catalog)
        if args.pending:
            text = pending_text(json.loads(args.pending.read_text(encoding="utf-8")))
        else:
            ids = args.ids or select_files([Path(name) for name in args.files], Path.cwd(), "")
            if not ids:
                raise ValueError("no rules for these files; give code files or --ids")
            text = render(catalog, ids)
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        print(f"read_rules: {error}", file=sys.stderr)
        return 2
    print(text, end="" if text.endswith("\n") else "\n")
    return 0


def read_catalog() -> dict:
    """대응표를 읽고 형식을 확인한다. 규칙 이름과 선택 조건이 가리키는 규칙이 모두 있어야 한다."""
    catalog = json.loads(MAP.read_text(encoding="utf-8"))
    rules = catalog.get("rules") if isinstance(catalog, dict) else None
    selects = catalog.get("select") if isinstance(catalog, dict) else None
    is_shaped = isinstance(rules, dict) and isinstance(selects, list)
    if not is_shaped:
        raise ValueError(f"invalid rule map: {MAP}")
    broken = [name for name, rule in rules.items() if not isinstance(rule, dict) or not all(isinstance(rule.get(key), str) for key in ("skill", "path", "sha256"))]
    broken += [repr(row) for row in selects if not isinstance(row, dict) or not isinstance(row.get("rules"), list) or set(row["rules"]) - rules.keys()]
    if broken:
        raise ValueError(f"invalid rules or select rows in {MAP}: {', '.join(broken)}")
    return catalog


def skill_folder(name: str) -> Path:
    """설치본(스킬 폴더 나란히) 또는 원본 저장소(분류 폴더 아래)에서 스킬 폴더 하나를 찾는다."""
    root = Path(__file__).resolve().parents[3]
    candidates = [root / name, *(root.parent / category / name for category in CATEGORIES)]
    found = list(dict.fromkeys(path.resolve() for path in candidates if (path / "SKILL.md").is_file()))
    if len(found) != 1:
        raise ValueError(f"skill missing or ambiguous: {name}")
    return found[0]


def rule_text(rule: dict) -> str:
    """규칙 원문. 머리말(frontmatter)을 빼고, `sections`가 있으면 그 절만, `drop`이 있으면 그 절을 뺀다."""
    source = skill_folder(rule["skill"]) / rule["path"]
    text = source.read_text(encoding="utf-8")
    if text.startswith("---\n"):
        text = text.split("\n---\n", 1)[1].lstrip("\n")
    blocks = re.split(r"(?=^## )", text, flags=re.MULTILINE)
    named = {"" if not block.startswith("## ") else block[3:].split("\n", 1)[0]: block for block in blocks}
    wanted = rule.get("sections")
    dropped = rule.get("drop", [])
    missing = (set(wanted or []) | set(dropped)) - named.keys()
    if missing:
        raise ValueError(f"rule section missing in {source}: {', '.join(sorted(missing))}")
    picked = [named[title] for title in wanted] if wanted else [block for title, block in named.items() if title not in dropped]
    return "".join(picked).rstrip("\n") + "\n"


def rule_body(catalog: dict, name: str) -> str:
    rule = catalog["rules"][name]
    text = rule_text(rule)
    if hashlib.sha256(text.encode()).hexdigest() != rule["sha256"]:
        raise ValueError(f"rule changed; review the selection in {MAP} and update sha256: {name} ({rule['skill']}/{rule['path']})")
    return text


def ordered(catalog: dict, ids: list[str]) -> list[str]:
    unknown = set(ids) - catalog["rules"].keys()
    if unknown:
        raise ValueError("unknown rule IDs: " + ", ".join(sorted(unknown)))
    return [name for name in catalog["rules"] if name in ids]


def render(catalog: dict, ids: list[str]) -> str:
    blocks = []
    for name in ordered(catalog, ids):
        rule = catalog["rules"][name]
        blocks.append(f"<!-- {name} | {rule['skill']}/{rule['path']} -->\n{rule_body(catalog, name)}")
    return "\n".join(blocks)


def check(catalog: dict) -> int:
    failures = 0
    for name, rule in catalog["rules"].items():
        digest = hashlib.sha256(rule_text(rule).encode()).hexdigest()
        if digest != rule["sha256"]:
            failures += 1
            print(f"{name}: {rule['skill']}/{rule['path']} sha256 {digest}", file=sys.stderr)
    print(f"rules {len(catalog['rules'])}, changed {failures}")
    return 1 if failures else 0


def select_files(paths: list[Path], working: Path, edited: str) -> list[str]:
    """편집할 파일의 확장자·경로와 내용으로 대응표의 선택 조건을 맞춰 규칙 이름을 고른다. 내용은 편집 입력이 있으면 그것만, 없으면 기존 파일을 본다."""
    catalog = read_catalog()
    selected: list[str] = []
    for path in paths:
        source = path if path.is_absolute() else working / path
        if not any(source.suffix in row.get("suffixes", ()) for row in catalog["select"]):
            continue
        text = edited
        if not edited and source.is_file():
            text = source.read_text(encoding="utf-8", errors="replace")
        for row in catalog["select"]:
            if row.get("suffixes") and source.suffix not in row["suffixes"]:
                continue
            if row.get("path") and not re.search(row["path"], source.as_posix()):
                continue
            if row.get("content") and not re.search(row["content"], text):
                continue
            selected += row["rules"]
    return list(dict.fromkeys(selected))


def edit_targets(payload: dict) -> list[Path]:
    """편집 도구 입력에 명시된 파일의 절대 경로."""
    value = payload.get("tool_input", {})
    working = Path(value.get("workdir") or payload.get("cwd") or ".") if isinstance(value, dict) else Path(".")
    if payload.get("tool_name") in {"Write", "Edit", "MultiEdit"} and isinstance(value, dict):
        names = [str(value.get("file_path") or "")]
    else:
        command = "\n".join(str(value.get(key) or "") for key in ("command", "cmd", "patch")) if isinstance(value, dict) else str(value)
        names = re.findall(r"^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$", command, re.MULTILINE)
    return [(working / name).resolve() for name in dict.fromkeys(names) if name]


def select_for_tool(payload: dict, scope: dict, in_git: Callable[[Path], bool]) -> None:
    """편집 도구 입력에 명시된 코드 파일 가운데 git 작업본 안의 것(`in_git`)으로 규칙을 골라 scope["ids"]에 더한다. 내용 조건은 편집 입력에만 맞춘다."""
    value = payload.get("tool_input", {})
    edited = {key: item for key, item in value.items() if key not in {"file_path", "workdir"}} if isinstance(value, dict) else value
    inside = [source for source in edit_targets(payload) if in_git(source)]
    ids = select_files(inside, Path("/"), _joined_strings(edited))
    scope["ids"] = list(dict.fromkeys([*scope.get("ids", []), *ids]))


def select_query(payload: dict, scope: dict) -> bool:
    """단일 셸 명령으로 이 조회기를 파일·ID 인자로 부르면 그 규칙을 scope에 더하고 참을 돌려준다(훅이 --pending 조회로 바꾼다)."""
    args = _query_args(payload)
    if not args:
        return False
    is_ids = args[0] == "--ids" or args[0].startswith("--ids=")
    if args[0].startswith("-") and not is_ids:
        return False
    try:
        catalog = read_catalog()
        if is_ids:
            ids = ([args[0].split("=", 1)[1]] if "=" in args[0] else []) + args[1:]
            if not ids or any(name.startswith("-") for name in ids):
                return False
            ordered(catalog, ids)
        else:
            if any(name.startswith("-") for name in args):
                return False
            value = payload.get("tool_input", {})
            working = Path(value.get("workdir") or payload.get("cwd") or ".") if isinstance(value, dict) else Path(".")
            ids = select_files([Path(name) for name in args], working, "")
            if not ids:
                return False
    except (OSError, ValueError):
        return False  # 잘못된 입력의 진단·종료 코드는 원래 명령이 돌려준다.
    scope["ids"] = list(dict.fromkeys([*scope.get("ids", []), *ids]))
    return True


def pending_rules(state: dict) -> list[tuple[str, str, str]]:
    """훅 상태의 선택 규칙을 `#`·`##` 절 단위로 나눠 아직 전달되지 않은 (sha256, 출처, 본문) 목록을 돌려준다."""
    if not isinstance(state, dict):
        raise TypeError("rule state must be an object")
    scope = state.get("rule_scope", {})
    ids = scope.get("ids", []) if isinstance(scope, dict) else None
    seen = state.get("rule_seen", [])
    for label, values in (("rule scope ids", ids), ("rule seen", seen)):
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise TypeError(f"{label} must be a string list")
    if not ids:
        return []
    catalog = read_catalog()
    output = []
    hashes = set(seen)
    for name in ordered(catalog, ids):
        rule = catalog["rules"][name]
        label = f"{name} | {rule['skill']}/{rule['path']}"
        for part in re.split(r"(?=^##? )", rule_body(catalog, name), flags=re.MULTILINE):
            body = part.strip()
            digest = hashlib.sha256(body.encode()).hexdigest()
            if body and digest not in hashes:
                output.append((digest, label, body))
                hashes.add(digest)
    return output


def pending_text(state: dict) -> str:
    rows = pending_rules(state)
    selected: list[str] = []
    size = 0
    for _, label, body in rows:
        block = f"<!-- {label} -->\n{body}"
        if selected and size + len(block.encode()) > BATCH_BYTES:
            break
        selected.append(block)
        size += len(block.encode())
    text = "\n\n".join(selected) or DONE
    return text + MORE if len(selected) < len(rows) else text + "\n"


def collect_tool_output(payload: dict) -> str:
    return _joined_strings(payload.get("tool_response", ""))


def _joined_strings(item: object) -> str:
    """JSON 값 안의 모든 문자열을 줄바꿈으로 이은 글. 이스케이프 없이 원문 그대로라 낱말 경계 조건이 맞는다."""
    def strings(value: object) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            return [text for child in value.values() for text in strings(child)]
        if isinstance(value, list):
            return [text for child in value for text in strings(child)]
        return []

    return "\n".join(strings(item))


def _query_args(payload: dict) -> list[str] | None:
    value = payload.get("tool_input", {})
    command = str(value.get("command", value.get("cmd", "")) if isinstance(value, dict) else value)
    # 조회 예외는 확장·치환·연속 실행 없는 단일 명령에만 적용한다.
    if any(character in command for character in "\n\r$`"):
        return None
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>()")
        lexer.whitespace_split = True
        args = list(lexer)
    except ValueError:
        return None
    if not args or not re.fullmatch(r"python(?:3(?:\.\d+)?)?", Path(args[0]).name):
        return None
    if any(token and set(token) <= set(";&|<>()") for token in args):
        return None
    index = 2 if len(args) > 1 and args[1] == "-B" else 1
    if len(args) <= index:
        return None
    working = Path(value.get("workdir") or payload.get("cwd") or ".") if isinstance(value, dict) else Path(".")
    if (working / args[index]).resolve() != Path(__file__).resolve():
        return None
    return args[index + 1 :]


if __name__ == "__main__":
    raise SystemExit(main())
