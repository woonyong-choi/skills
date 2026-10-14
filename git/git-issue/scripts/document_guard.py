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
DOCUMENT_LITERAL = re.compile(r"\.(?:md|mdx|rst|adoc|txt|docx|pdf)(?=$|[^\w])", re.IGNORECASE)


def deny(reason: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "Work Continuity: " + reason}}


def document_paths(payload: dict) -> list[Path]:
    name = payload.get("tool_name", "")
    value = payload.get("tool_input", {})
    if not isinstance(value, dict):
        value = {"command": value} if isinstance(value, str) else {}
    if name == "apply_patch":
        paths = PATCH_PATH.findall(value.get("command", value.get("patch", "")))
    elif name in {"Write", "Edit", "MultiEdit"}:
        paths = [value.get("file_path", "")]
    else:
        return []
    cwd = Path(value.get("workdir") or payload.get("cwd") or Path.cwd())
    return [(cwd / path).resolve() for path in paths if path and Path(path).suffix.lower() in DOCUMENT_SUFFIXES]


# cost: time O(n), heap O(n), stack O(1), io O(p)
# vars: n = tool input and index bytes, p = registered projects
# basis: estimate
def check_tool(payload: dict, project_path: Path | None = None) -> dict:
    name = payload.get("tool_name", "")
    value = payload.get("tool_input", {})
    if name in {"Bash", "exec_command"} and isinstance(value, dict):
        command = value.get("command", value.get("cmd", ""))
        try:
            lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>()")
            lexer.whitespace_split = True
            tokens = list(lexer)
        except ValueError:
            return deny("cannot inspect malformed shell command; use a structured file tool")
        redirected_document = any(
            token in {">", ">>"} and DOCUMENT_LITERAL.search(tokens[index + 1])
            for index, token in enumerate(tokens[:-1])
        )
        file_command = any(Path(token).name in SHELL_FILE_COMMANDS for token in tokens)
        inline_document_write = any(
            SHELL_WRITER.search(line) and DOCUMENT_LITERAL.search(line)
            for line in command.splitlines()
        )
        if redirected_document or inline_document_write or (file_command and DOCUMENT_LITERAL.search(command)):
            return deny("document writes through shell commands require a structured Write/Edit/apply_patch call; do not retry through another shell command")
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
        return deny(str(error) + "; register the correct project or use its Vault document area; do not bypass this check")
