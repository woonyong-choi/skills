"""현재 판단에 필요한 소유 규칙을 실행 순서대로 한 번씩 출력한다.

인자: topics는 분류 이름, --pending은 기존 훅 세션 파일, --help는 사용법.
출력: stdout 원문, stderr 진단. 성공 0, 읽기 실패 1, 입력 오류 2.
실행 조건: Python 3.9 이상·표준 라이브러리. 원본·평탄한 설치 구조 지원.
"""

from __future__ import annotations

__all__ = [
    "main",
    "select_for_tool",
    "pending_rules",
    "collect_tool_output",
    "is_rule_query",
    "select_query",
]

import argparse
import contextlib
import hashlib
import io
import json
import logging
from pathlib import Path
import re
import shlex
from types import ModuleType
from typing import Final

RULES: Final = {
    "requirements": ("repo-docs-design", "references/requirements.md", ()),
    "choice": (
        "repo-docs-design",
        "SKILL.md",
        ("", "적용", "요구 확인", "선택", "설명과 조사", "구조 경계"),
    ),
    "infrastructure": ("repo-docs-design", "references/infrastructure.md", ()),
    "implement": ("code-style", "SKILL.md", ("", "조건별 읽기", "원칙", "구현")),
    "failure": ("code-style", "SKILL.md", ("실패 처리",)),
    "data-and-concurrency": ("code-style", "references/data-and-concurrency.md", ()),
    "resources": ("code-style", "references/resources.md", ()),
    "operations": ("code-style", "references/operations.md", ()),
    "interfaces": ("code-style", "references/interfaces.md", ()),
    "review": ("code-style", "SKILL.md", ("검증",)),
}
TOPICS: Final = {
    "product": tuple(rule for rule in RULES if rule not in ("implement", "failure")),
    "implement": ("implement",),
    "failure": ("failure",),
    "spec": ("requirements",),
    "choice": ("choice", "requirements"),
    "data": ("data-and-concurrency",),
    "resources": ("requirements", "resources"),
    "interface": ("interfaces",),
    "external": ("operations", "interfaces"),
    "infrastructure": ("choice", "requirements", "infrastructure", "operations"),
    "operations": ("operations",),
    "review": ("review",),
}
logger = logging.getLogger(__name__)


# cost: time O(n+b), heap O(n+b), stack O(1), io k file reads and stdout
# vars: n = 분류 수, b = 조회 문서 길이, k = 선택 파일 수
# basis: estimate
def main() -> int:
    logging.basicConfig(level=logging.ERROR, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topics", nargs="*", metavar="topic")
    parser.add_argument(
        "--pending", type=Path, help="print undelivered rules from hook session state"
    )
    args = parser.parse_args()
    if bool(args.topics) == bool(args.pending):
        parser.error("provide topics or --pending")
    if any(topic not in TOPICS for topic in args.topics):
        parser.error("unknown topic; choose from " + ", ".join(TOPICS))
    try:
        if args.pending:
            state = json.loads(args.pending.read_text(encoding="utf-8"))
            rows = pending_rules(state)
            selected: list[str] = []
            size = 0
            for row in rows:
                block = f"<!-- {row[1]} -->\n{row[2]}"
                if selected and size + len(block.encode()) > 12000:
                    break
                selected.append(block)
                size += len(block.encode())
            text = (
                "\n\n".join(selected)
                or "필수 원문 전달 완료. 같은 원문 재조회 없이 적용."
            )
            if len(selected) < len(rows):
                text += "\n\n미전달 원문이 남아 있습니다. 같은 --pending 명령으로 이어서 조회하세요.\n"
        else:
            text = _read_rules(args.topics)
    except (OSError, UnicodeError, ValueError) as error:
        logger.error("failed to read required rules: %s", error)
        return 1
    print(text, end="")
    return 0


# cost: time O(n+b), heap O(n+b), stack O(1), io O(f)
# vars: n = 도구 입력 길이, b = 대상 소스 바이트, f = 명시된 소스 파일 수
# basis: estimate
def select_for_tool(payload: dict, repo: Path, scope: dict) -> None:
    """명시된 소스·편집 내용으로 읽기 하한을 선택한다. 의미상 추가 조건은 실행자가 선택한다."""
    value = payload.get("tool_input", {})
    command = str(
        value.get("command", value.get("cmd", value.get("patch", "")))
        if isinstance(value, dict)
        else value
    )
    raw = command + "\n" + json.dumps(value, ensure_ascii=False)
    working = (
        Path(value.get("workdir") or payload.get("cwd") or repo)
        if isinstance(value, dict)
        else repo
    )
    tool = payload.get("tool_name", "")
    if tool == "apply_patch" and isinstance(value, dict):
        command = "\n".join(str(value.get(key) or "") for key in ("command", "patch"))
    is_edit = tool in {"Write", "Edit", "MultiEdit", "apply_patch"}
    names = re.findall(r"[\w./-]+\.(?:py|m?js|jsx|tsx?|rs|kts?|css)\b", command)
    try:
        names += [
            token
            for token in shlex.split(command)
            if re.search(r"\.(?:py|m?js|jsx|tsx?|rs|kts?|css)$", token)
        ]
    except ValueError:
        pass  # 불완전한 셸 입력은 명시된 경로만 사용한다.
    if tool in {"Read", "Write", "Edit", "MultiEdit"}:
        names = [value.get("file_path", "")]
    elif tool == "apply_patch":
        names = re.findall(
            r"^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$",
            command,
            re.M,
        )
    languages = {
        ".py": "python",
        ".js": "javascript",
        ".mjs": "javascript",
        ".jsx": "javascript",
        ".ts": "javascript",
        ".tsx": "javascript",
        ".rs": "rust",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".css": "css",
    }
    scope.setdefault("topics", [])
    scope.setdefault("ids", [])
    scope.setdefault("languages", [])
    texts = []
    for name in dict.fromkeys(names):
        source = (working / name).resolve()
        if not source.is_relative_to(repo.resolve()) or not (
            source.is_file() or is_edit
        ):
            continue
        language = languages.get(source.suffix)
        if language and language not in scope["languages"]:
            scope["languages"].append(language)
        if source.is_file():
            texts.append(source.read_text(encoding="utf-8"))
    if not scope["languages"]:
        return
    text = "\n".join(texts) + raw
    scope["topics"] = list(dict.fromkeys([*scope["topics"], "implement"]))
    for topic, pattern in {
        "data": r"\b(?:async|await|locked|Lock|RLock|Semaphore|transaction|Thread)\b",
        "operations": r"\b(?:permission|authorization|subprocess|exec_module|environ|Popen)\b",
    }.items():
        if re.search(pattern, text) and topic not in scope["topics"]:
            scope["topics"].append(topic)
    selected = ["CS-LANGUAGE"]
    conditions = {
        "CS-SIZE": r"\b(?:def|class|fn|fun|function|if|for|while)\b|=>",
        "CS-NAME": r"\b(?:def|class|fn|fun|function|const|let|var)\b|=>",
        "CS-ORDER": r"\b(?:def|class|fn|fun|function|const|let|var)\b|=>",
        "CS-VISIBILITY": r"\b(?:def|class|fn|fun|function|public|private|pub)\b|#|//|=>",
        "CS-CONDITION": r"\b(?:if|elif|else|match|switch|for|while)\b|\?",
        "CS-ERROR": r"\b(?:raise|try|except|throw|catch|Result|Error|open)\b|read_|write_|subprocess|fetch\(",
        "CS-COST": r"read_|write_|\bopen\(|subprocess|fetch\(|\.request\(|\.execute\(",
    }
    selected += [
        identity for identity, pattern in conditions.items() if re.search(pattern, text)
    ]
    selected.append("CS-TEST")
    scope["ids"] = list(dict.fromkeys([*scope["ids"], *selected]))


# cost: time O(b), heap O(b), stack O(1), io O(f)
# vars: b = 선택 원문 바이트, f = 선택 파일 수
# basis: estimate
def pending_rules(state: dict) -> list[tuple[str, str, str]]:
    if not isinstance(state, dict):
        raise ValueError("rule state must be an object")
    scope = state.get("rule_scope", {})
    if not isinstance(scope, dict):
        raise ValueError("rule scope must be an object")
    for name in ("topics", "ids", "languages"):
        values = scope.get(name, [])
        if not isinstance(values, list) or any(
            not isinstance(value, str) for value in values
        ):
            raise ValueError(f"rule scope {name} must be a string list")
    topics = scope.get("topics", [])
    if any(topic not in TOPICS for topic in topics):
        raise ValueError("unknown rule topic")
    texts = [_read_rules(topics)] if topics else []
    if scope.get("ids"):
        module = _code_reader()
        rules = module.select_rules(module.ROOT, scope["ids"])
        texts += [
            f"<!-- code-style/{row['source']} -->\n{row['text']}" for row in rules
        ]
        texts += module.read_dependencies(rules, scope.get("languages", []))
    seen = state.get("rule_seen", [])
    if not isinstance(seen, list) or any(not isinstance(value, str) for value in seen):
        raise ValueError("rule seen must be a string list")
    output = []
    hashes = set()
    for chunk in re.split(r"(?=^<!-- )", "\n".join(texts), flags=re.M):
        match = re.match(r"<!-- (.*?) -->\s*", chunk)
        label = match[1] if match else "required rule"
        content = chunk[match.end() :] if match else chunk
        for part in re.split(r"(?=^##? )", content, flags=re.M):
            body = part.strip()
            if not body:
                continue
            digest = hashlib.sha256(body.encode()).hexdigest()
            if digest not in seen and digest not in hashes:
                output.append((digest, label, body))
                hashes.add(digest)
    return output


def collect_tool_output(payload: dict) -> str:
    value = payload.get("tool_response", "")

    def strings(item: object) -> list[str]:
        if isinstance(item, str):
            return [item]
        if isinstance(item, dict):
            return [text for child in item.values() for text in strings(child)]
        if isinstance(item, list):
            return [text for child in item for text in strings(child)]
        return []

    return "\n".join(strings(value))


def is_rule_query(payload: dict) -> bool:
    return _query_args(payload) is not None


# cost: time O(b), heap O(b), stack O(1), io O(f)
# vars: b = 선택 원문 바이트, f = 선택 파일 수
# basis: estimate
def select_query(payload: dict, scope: dict) -> bool:
    query = _query_args(payload)
    if query is None:
        return False
    owner, args = query
    if owner == "developer-thinking":
        if not args or any(topic not in TOPICS for topic in args):
            return False
        scope["topics"] = list(dict.fromkeys([*scope.get("topics", []), *args]))
        return True
    try:
        module = _code_reader()
        with (
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            parsed = module.parse_arguments(args)
        if not parsed.text:
            return False
        identities = (["CS-LANGUAGE"] if parsed.language else []) + parsed.ids
        rules = module.select_rules(module.ROOT, identities)
        module.read_dependencies(rules, parsed.language or [])
    except (SystemExit, OSError, ValueError):
        return False  # 잘못된 입력의 진단·종료 코드는 원래 CLI가 반환한다.
    scope["ids"] = list(dict.fromkeys([*scope.get("ids", []), *identities]))
    scope["languages"] = list(
        dict.fromkeys([*scope.get("languages", []), *(parsed.language or [])])
    )
    return True


# cost: time O(b), heap O(b), stack O(1), io 1
# vars: b = 조회기 코드 바이트
# basis: estimate
def _code_reader() -> ModuleType:
    source = _owner_path("code-style") / "scripts/read_rules.py"
    module = ModuleType("code_rule_reader")
    module.__file__ = str(source)
    exec(
        compile(source.read_text(encoding="utf-8"), str(source), "exec"),
        module.__dict__,
    )
    return module


def _query_args(payload: dict) -> tuple[str, list[str]] | None:
    value = payload.get("tool_input", {})
    command = str(
        value.get("command", value.get("cmd", "")) if isinstance(value, dict) else value
    )
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
    if any(set(token) <= set(";&|<>()") for token in args if token):
        return None
    index = 2 if len(args) > 1 and args[1] == "-B" else 1
    if len(args) <= index:
        return None
    working = (
        Path(value.get("workdir") or payload.get("cwd") or ".")
        if isinstance(value, dict)
        else Path(".")
    )
    source = (working / args[index]).resolve()
    for owner in ("developer-thinking", "code-style"):
        if source == (_owner_path(owner) / "scripts/read_rules.py").resolve():
            return owner, args[index + 1 :]
    return None


def _owner_path(name: str) -> Path:
    skill = Path(__file__).resolve().parents[1]
    candidates = (
        skill.parent / name,
        skill.parents[1] / "code" / name,
        skill.parents[1] / "docs" / name,
    )
    matches = [path for path in candidates if (path / "SKILL.md").is_file()]
    unique = list(dict.fromkeys(path.resolve() for path in matches))
    if len(unique) != 1:
        raise ValueError(f"required owner missing or ambiguous: {name}")
    return unique[0]


def _select_sections(text: str, headings: tuple[str, ...]) -> str:
    if not headings:
        return text
    parts = text.split("\n## ")
    blocks = {
        "": parts[0],
        **{part.split("\n", 1)[0]: "## " + part for part in parts[1:]},
    }
    missing = set(headings) - blocks.keys()
    if missing:
        raise ValueError("required sections missing: " + ", ".join(sorted(missing)))
    return "\n".join(blocks[heading] for heading in headings)


# cost: time O(n+b), heap O(b), stack O(1), io k file reads
# vars: n = 분류 수, b = 조회 문서 길이, k = 선택 파일 수
# basis: estimate
def _read_rules(topics: list[str]) -> str:
    selected = {"review"}
    for topic in topics:
        selected.update(TOPICS[topic])
    output = []
    contents = {}
    for rule, (owner, path, headings) in RULES.items():
        if rule in selected:
            source = _owner_path(owner) / path
            if source not in contents:
                contents[source] = source.read_text(encoding="utf-8")
            output.append(
                f"<!-- {owner}/{path} -->\n"
                + _select_sections(contents[source], headings)
            )
    return "\n".join(output)


if __name__ == "__main__":
    raise SystemExit(main())
