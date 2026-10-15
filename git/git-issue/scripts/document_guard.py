"""지원 파일 도구의 문서 쓰기를 등록된 프로젝트 경로와 대조한다."""

from __future__ import annotations

from pathlib import Path
import re
import shlex

import project_context


DOCUMENT_SUFFIXES = {".md", ".mdx", ".rst", ".adoc", ".txt", ".docx", ".pdf"}
PATCH_PATH = re.compile(r"^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$", re.MULTILINE)
SHELL_WRITER = re.compile(r"\.write_(?:text|bytes)\s*\(|\bwriteFile(?:Sync)?\s*\(|\bopen\([^\n]*[,=]\s*['\"][wax]")
SHELL_FILE_COMMANDS = {"tee", "cp", "mv", "install", "touch"}
SHELL_INTERPRETERS = {"sh", "bash", "zsh", "dash"}
DOCUMENT_LITERAL = re.compile(r"\.(?:md|mdx|rst|adoc|txt|docx|pdf)(?=$|[^\w])", re.IGNORECASE)
HEREDOC = re.compile(r"""'[^']*'|"(?:\\.|[^"\\])*"|\\.|(?P<comment>(?<!\S)\#.*)|(?<!<)<<(?P<tabs>-?)(?!<)[ \t]*(?P<delimiter>'[^']+'|"(?:\\.|[^"\\])+"|\\?[A-Za-z_][\w.-]*)""")


def deny(reason: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "Work Continuity: " + reason}}


def document_paths(payload: dict) -> list[Path]:
    name = payload.get("tool_name", "")
    value = payload.get("tool_input", {})
    if not isinstance(value, dict):
        value = {"command": value} if isinstance(value, str) else {}
    if name == "apply_patch":
        paths = PATCH_PATH.findall("\n".join(str(value.get(key) or "") for key in ("command", "patch")))
    elif name in {"Write", "Edit", "MultiEdit"}:
        paths = [value.get("file_path", "")]
    else:
        return []
    cwd = Path(value.get("workdir") or payload.get("cwd") or Path.cwd())
    return [(cwd / path).resolve() for path in paths if path and Path(path).suffix.lower() in DOCUMENT_SUFFIXES]


# cost: time O(n²), heap O(n), stack O(1), io O(p)
# vars: n = tool input and index bytes, p = registered projects
# basis: estimate
def check_tool(payload: dict, project_path: Path | None = None) -> dict:
    name = payload.get("tool_name", "")
    value = payload.get("tool_input", {})
    if name in {"Bash", "exec_command"} and isinstance(value, dict):
        commands = [str(value.get("command", value.get("cmd")) or "")]
        try:
            while commands:
                command = commands.pop()
                lexer = shlex.shlex(shell_syntax(command), posix=True, punctuation_chars=";&|<>(){}\n")
                lexer.whitespace_split = True
                lexer.whitespace = " \t\r"
                lexer.commenters = ""
                tokens = list(lexer)
                commands.extend(
                    tokens[index + 2] for index, token in enumerate(tokens[:-2])
                    if Path(token).name in SHELL_INTERPRETERS and re.fullmatch(r"-[a-z]*c[a-z]*", tokens[index + 1])
                )
                redirected_document = any(
                    token in {">", ">>"} and DOCUMENT_LITERAL.search(tokens[index + 1])
                    for index, token in enumerate(tokens[:-1])
                )
                inline_document_write = any(
                    SHELL_WRITER.search(line) and DOCUMENT_LITERAL.search(line)
                    for line in command.splitlines()
                )
                if redirected_document or inline_document_write or writes_document(tokens):
                    return deny("document writes through shell commands require a structured Write/Edit/apply_patch call; do not retry through another shell command")
        except ValueError:
            return deny("cannot inspect malformed shell command; use a structured file tool")
        return {}
    paths = document_paths(payload)
    if not paths:
        return {}
    try:
        project = project_context.check_project(project_path or Path(payload["cwd"]))
        for path in paths:
            project_context.check_write(project, path)
        return {}
    except (project_context.ContextError, OSError, ValueError, IndexError, KeyError) as error:
        hint = "" if str(error).startswith("vault unregistered") else "; register the correct project or use its Vault document area"
        return deny(str(error) + hint + "; do not bypass this check")


def writes_document(tokens: list[str]) -> bool:
    start = 0
    for index, token in enumerate([*tokens, ";"]):
        if token and set(token) <= set(";&|(){}\n"):
            part = tokens[start:index]
            if part and is_document_command(part):
                return True
            start = index + 1
    return False


def is_document_command(part: list[str]) -> bool:
    names = [Path(arg).name for arg in part]
    has_document = any(DOCUMENT_LITERAL.search(arg) for arg in part)
    file_command = any(
        name in SHELL_FILE_COMMANDS and not (
            name == "install" and index > 0 and re.fullmatch(r"pip(?:\d+(?:\.\d+)?)?", names[index - 1])
        ) for index, name in enumerate(names)
    )
    dd_output = "dd" in names and any(arg.startswith("of=") and DOCUMENT_LITERAL.search(arg[3:]) for arg in part)
    in_place = bool({"sed", "perl"}.intersection(names)) and any(
        arg.startswith("--in-place") or re.match(r"^-[npEw]*i", arg)
        for arg in part
    )
    return dd_output or (has_document and (file_command or in_place))


def shell_syntax(command: str) -> str:
    """heredoc 본문은 셸 인자가 아니므로 따옴표 파싱에서 제외한다."""
    lines = []
    delimiters: list[tuple[str, bool]] = []
    shell_body = False
    for line in command.replace("\\\n", "").splitlines():
        if delimiters:
            delimiter, strip_tabs = delimiters[0]
            if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                delimiters.pop(0)
            elif shell_body:
                lines.append(line)
            continue
        for match in HEREDOC.finditer(line):
            if match["comment"] is not None:
                line = line[:match.start()]
                break
            if match["delimiter"] is not None:
                delimiters.append((shlex.split(match["delimiter"])[0], bool(match["tabs"])))
                words = shlex.split(line[:match.start()])
                shell_body = any(Path(word).name in SHELL_INTERPRETERS for word in words)
        lines.append(line)
    if delimiters:
        raise ValueError("unterminated heredoc")
    return "\n".join(lines)
