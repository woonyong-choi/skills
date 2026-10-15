"""지원 파일 도구의 문서 쓰기를 등록된 프로젝트 경로와 대조한다."""

from __future__ import annotations

from pathlib import Path
import re
import shlex

import project_context


DOCUMENT_SUFFIXES = {".md", ".mdx", ".rst", ".adoc", ".txt", ".docx", ".pdf"}
PATCH_PATH = re.compile(r"^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$", re.MULTILINE)
SHELL_WRITER = re.compile(r"\.write_(?:text|bytes)\s*\(|\bwriteFile(?:Sync)?\s*\(|\bopen\([^\n]*[,=]\s*\\?['\"][wax]")
SHELL_FILE_COMMANDS = {"tee", "cp", "mv", "install", "touch"}
COPY_COMMANDS = {"cp", "mv", "install"}
# 값을 따로 받는 옵션: 값을 명령 이름·피연산자로 오인하지 않도록 건너뜀.
OPTION_VALUES = {
    "sudo": {"-u", "-g", "-h", "-p", "-C", "-D", "-r", "-t", "-U", "-T", "--user", "--group", "--host", "--prompt", "--chdir"},
    "env": {"-u", "-C", "--unset", "--chdir"},
    "git": {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"},
    "xargs": {"-I", "-n", "-L", "-P", "-d", "-E", "-s", "-a"},
    "time": {"-f", "-o"},
}
COPY_OPTION_VALUES = {"-m", "-o", "-g", "-S", "--mode", "--owner", "--group", "--suffix"}
# .txt 설정·빌드 파일: 문서 아님. llms.txt·llms-full.txt는 문서 유지.
NON_DOCUMENT_NAME = re.compile(r"(?:requirements|constraints)(?:[-_.][\w.-]*)?\.txt|CMakeLists\.txt", re.IGNORECASE)
REDIRECT = re.compile(r"(?:>>?|>\||<>|>&)$")
SHELL_INTERPRETERS = {"sh", "bash", "zsh", "dash"}
COMMAND_PREFIXES = {"sudo", "env", "xargs", "command", "time", "git", "if", "then", "else", "elif", "do", "while", "until", "!"}
# 마지막 확장자만 문서 판정: 뒤가 끝·공백·따옴표·셸 구분·경로 구분일 때. `a.txt-bak`·`notes.md.orig` 제외
DOCUMENT_LITERAL = re.compile(r"\.(?:md|mdx|rst|adoc|txt|docx|pdf)(?=$|[\s'\"`;&|<>(){}\[\],=:\\/])", re.IGNORECASE)
SHELL_PUNCTUATION = ";&|<>(){}\n"
# 따옴표·역슬래시로 인용한 구분 문자: 연산자 판정 제외용 사용자 영역 문자로 치환 후 복원.
QUOTED_PUNCTUATION = {ord(char): 0xE000 + offset for offset, char in enumerate(SHELL_PUNCTUATION)}
UNQUOTED_PUNCTUATION = {value: key for key, value in QUOTED_PUNCTUATION.items()}
FIND_EXEC = {"-exec", "-execdir", "-ok", "-okdir"}
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
    return [(cwd / path).resolve() for path in paths if path and is_document_name(Path(path).name)]


def is_document_name(name: str) -> bool:
    return Path(name).suffix.lower() in DOCUMENT_SUFFIXES and not NON_DOCUMENT_NAME.fullmatch(name)


def mentions_document(text: str) -> bool:
    """문서 확장자로 끝나는 단어 존재 여부. 설정용 .txt 이름 제외."""
    for match in DOCUMENT_LITERAL.finditer(text):
        name = re.split(r"[\s/\\'\"=(),;:<>|&]", text[:match.end()])[-1]
        if not NON_DOCUMENT_NAME.fullmatch(name):
            return True
    return False


# cost: time O(n²), heap O(n), stack O(1), io O(p)
# vars: n = tool input and index bytes, p = registered projects
# basis: estimate
def check_tool(payload: dict, project_path: Path | None = None) -> dict:
    name = payload.get("tool_name", "")
    value = payload.get("tool_input", {})
    if name in {"Bash", "exec_command"} and isinstance(value, dict):
        source = str(value.get("command", value.get("cmd")) or "")
        commands = [source]
        cwd = Path(value.get("workdir") or payload.get("cwd") or Path.cwd())
        try:
            while commands:
                command = commands.pop()
                tokens, operators = shell_tokens(command)
                commands.extend(nested_commands(tokens))
                redirected_document = any(
                    index in operators and REDIRECT.search(token) and mentions_document(tokens[index + 1])
                    for index, token in enumerate(tokens[:-1])
                )
                inline_document_write = any(
                    SHELL_WRITER.search(line) and mentions_document(line)
                    for line in command.splitlines()
                )
                if redirected_document or inline_document_write or writes_document(tokens, operators, cwd):
                    return deny("document writes through shell commands require a structured Write/Edit/apply_patch call; redirect command output to a .log file; do not retry through another shell command")
            patched = shell_patch(payload)
        except ValueError:
            return deny("cannot inspect malformed shell command; use a structured file tool")
        if patched is None:
            return {}
        if "*** Begin Patch" not in source:
            return deny("cannot inspect apply_patch input; pass the patch inline")
        payload = patched
    paths = document_paths(payload)
    if not paths:
        return {}
    project = None
    try:
        # 지원 문서는 프로젝트가 아니라 등록 Vault의 career 영역에 둔다(career 스킬).
        career = project_context.resolve_vault() / "career"
        if all(path.is_relative_to(career) for path in paths):
            return {}
        project = project_context.check_project(project_path or Path(payload["cwd"]))
        for path in paths:
            project_context.check_write(project, path)
        return {}
    except (project_context.ContextError, OSError, ValueError, IndexError, KeyError) as error:
        message = str(error)
        if message.startswith("vault unregistered"):
            hint = ""
        elif message.startswith("document path is outside") and (owner := owning_project(paths, project)):
            hint = f"; the path belongs to registered project {owner}; start the session with that project's working directory as cwd and retry"
        elif message.startswith("document path is outside") and project:
            area = Path(project["area"])
            hint = f"; write inside {area / 'docs'} (documents) or {area / 'agent'} (agent context); a project-root document needs explicit user approval recorded in approved_documents of {project['index']}"
        elif message.startswith("document path is outside"):
            hint = "; write inside the project's Vault area or an approved path"
        else:
            hint = setup_hint(message, project_path or payload.get("cwd") or Path.cwd())
        return deny(message + hint + "; do not bypass this check")


def owning_project(paths: list[Path], current: dict | None) -> str | None:
    """대상 경로가 다른 등록 프로젝트의 Vault 영역·작업 경로에 있으면 그 프로젝트 작업 경로."""
    try:
        vault = project_context.resolve_vault()
        indexes = list((vault / "worktree").glob("*/agent/index.md"))
    except (project_context.ContextError, OSError):
        return None
    for index in indexes:
        if current and Path(current["index"]) == index:
            continue
        try:
            registration = project_context.read_registration(index)
        except (project_context.ContextError, OSError, ValueError):
            continue
        roots = [index.parent.parent, *(Path(p) for p in registration.get("paths", []))]
        if all(any(path.is_relative_to(root.resolve()) for root in roots) for path in paths):
            return next(iter(registration.get("paths", [])), str(index.parent.parent))
    return None


def setup_hint(message: str, project_path: Path | str) -> str:
    """프로젝트 맥락 오류의 등록 안내. Vault 미등록 오류는 자체 절차 포함이라 빈 값."""
    if message.startswith("vault unregistered"):
        return ""
    project = shlex.quote(str(project_path))
    return f"; ask the user first (registration writes AGENTS.md/CLAUDE.md into the repo), then run python3 {Path(project_context.__file__).resolve()} --project {project} --register-project"


# cost: time O(n), heap O(n), stack O(1), io O(1)
# vars: n = command bytes
# basis: estimate
def shell_tokens(command: str) -> tuple[list[str], set[int]]:
    """셸 단어와 인용하지 않은 연산자 위치. 단독 `{}`는 find·xargs 인자."""
    lexer = shlex.shlex(mark_quoted(shell_syntax(command)), posix=True, punctuation_chars=SHELL_PUNCTUATION)
    lexer.whitespace_split = True
    lexer.whitespace = " \t\r"
    lexer.commenters = ""
    tokens = list(lexer)
    operators = {index for index, token in enumerate(tokens) if token[:1] in set(SHELL_PUNCTUATION) and token != "{}"}
    return [token.translate(UNQUOTED_PUNCTUATION) for token in tokens], operators


# cost: time O(n), heap O(n), stack O(1), io O(1)
# vars: n = command bytes
# basis: estimate
def mark_quoted(command: str) -> str:
    """작은따옴표·큰따옴표·역슬래시로 인용한 구분 문자를 치환. 따옴표는 shlex 처리용으로 유지."""
    marked = []
    quote = ""
    index = 0
    while index < len(command):
        char = command[index]
        if char == "\\" and quote != "'" and index + 1 < len(command):
            following = command[index + 1]
            if following in SHELL_PUNCTUATION and not quote:
                marked.append(following.translate(QUOTED_PUNCTUATION))
            else:
                marked.append(char + following.translate(QUOTED_PUNCTUATION if quote else {}))
            index += 2
            continue
        if quote:
            if char == quote:
                quote = ""
            else:
                char = char.translate(QUOTED_PUNCTUATION)
        elif char in "'\"":
            quote = char
        marked.append(char)
        index += 1
    return "".join(marked)


def writes_document(tokens: list[str], operators: set[int], cwd: Path) -> bool:
    start = 0
    for index, token in enumerate([*tokens, ";"]):
        if index == len(tokens) or (index in operators and not set(token) & set("<>")):
            part = tokens[start:index]
            if part and is_document_command(part, cwd):
                return True
            start = index + 1
    return False


def nested_commands(tokens: list[str]) -> list[str]:
    """`sh -c`·`bash -lc` 등 셸 인터프리터에 넘긴 명령 문자열."""
    return [
        tokens[index + 2] for index, token in enumerate(tokens[:-2])
        if Path(token).name in SHELL_INTERPRETERS and re.fullmatch(r"-[a-z]*c[a-z]*", tokens[index + 1])
    ]


# cost: time O(n), heap O(n), stack O(1), io O(1)
# vars: n = command bytes
# basis: estimate
def shell_patch(payload: dict) -> dict | None:
    """셸 apply_patch·applypatch 호출(heredoc 포함)을 같은 입력의 구조화 apply_patch payload로 변환. 호출이 없으면 None, 잘못된 셸은 ValueError.

    문서 경로 검사와 필수 원문 확인(continuity_hook)이 공유하는 판정 정본.
    """
    value = payload.get("tool_input")
    if payload.get("tool_name") not in {"Bash", "exec_command"} or not isinstance(value, dict):
        return None
    source = str(value.get("command", value.get("cmd")) or "")
    cwd = Path(value.get("workdir") or payload.get("cwd") or Path.cwd())
    commands = [source]
    while commands:
        tokens, operators = shell_tokens(commands.pop())
        commands.extend(nested_commands(tokens))
        directory = patch_workdir(tokens, operators, cwd)
        if directory is not None:
            return {**payload, "tool_name": "apply_patch", "tool_input": {"command": source, "workdir": str(directory)}}
    return None


def patch_workdir(tokens: list[str], operators: set[int], cwd: Path) -> Path | None:
    """apply_patch·applypatch 호출 시 패치 기준 폴더(앞선 단일 인자 `cd` 반영), 없으면 None."""
    start = 0
    for index, token in enumerate([*tokens, ";"]):
        if index == len(tokens) or (index in operators and not set(token) & set("<>")):
            part = tokens[start:index]
            names = [name for name, _ in command_names(part)]
            if names[-1:] in (["apply_patch"], ["applypatch"]):
                return cwd
            if part[:1] == ["cd"] and len(part) == 2:
                cwd = cwd / Path(part[1]).expanduser()
            start = index + 1
    return None


def command_names(part: list[str]) -> list[tuple[str, int]]:
    """명령 위치 단어와 위치: 할당과 COMMAND_PREFIXES·그 옵션(값 포함) 뒤 첫 단어(git은 하위 명령)."""
    names: list[tuple[str, int]] = []
    skip = False
    for index, arg in enumerate(part):
        if skip:
            skip = False
            continue
        if names and names[-1][0] not in COMMAND_PREFIXES:
            break
        if re.fullmatch(r"[A-Za-z_]\w*=.*", arg) and (not names or names[-1][0] == "env"):
            continue
        if names and arg.startswith("-"):
            skip = arg in OPTION_VALUES.get(names[-1][0], set())
            continue
        names.append((Path(arg).name, index))
    return names


def copy_destinations(args: list[str], cwd: Path) -> list[str]:
    """cp·mv·install이 쓰는 이름: -d는 전체 피연산자, 그 외 대상과 디렉터리 대상(-t, 끝 /, 기존 폴더)이면 원본 이름."""
    operands: list[str] = []
    targets: list[str] = []
    directories = False
    options = True
    skip = None
    for arg in args:
        if skip is not None:
            if skip:
                targets.append(arg)
            skip = None
        elif options and arg == "--":
            options = False
        elif options and arg.startswith("--"):
            if arg.startswith("--target-directory="):
                targets.append(arg.split("=", 1)[1])
            elif arg == "--target-directory":
                skip = True
            elif arg == "--directory":
                directories = True
            elif arg in COPY_OPTION_VALUES:
                skip = False
        elif options and arg.startswith("-") and arg != "-":
            flags = arg[1:]
            for position, flag in enumerate(flags):
                if flag == "d":
                    directories = True
                if flag == "t" or "-" + flag in COPY_OPTION_VALUES:
                    value = flags[position + 1:]
                    if flag == "t" and value:
                        targets.append(value)
                    elif not value:
                        skip = flag == "t"
                    break
        else:
            operands.append(arg)
    if directories:
        return operands + targets
    if not targets and operands:
        targets = [operands.pop()]
        if not (targets[0].endswith("/") or (cwd / targets[0]).expanduser().is_dir()):
            return targets
    return targets + [Path(source.rstrip("/")).name for source in operands]


def is_document_command(part: list[str], cwd: Path) -> bool:
    positions = command_names(part)
    names = [name for name, _ in positions]
    command, start = positions[-1] if positions else ("", 0)
    if command in COPY_COMMANDS:
        file_write = any(mentions_document(arg) for arg in copy_destinations(part[start + 1:], cwd))
    else:
        file_write = command in SHELL_FILE_COMMANDS and any(mentions_document(arg) for arg in part)
    dd_output = "dd" in names and any(arg.startswith("of=") and mentions_document(arg[3:]) for arg in part)
    in_place = bool({"sed", "perl"}.intersection(names)) and any(
        arg.startswith("--in-place") or re.match(r"^-[npEw]*i", arg)
        for arg in part
    ) and any(mentions_document(arg) for arg in part)
    return dd_output or file_write or in_place or any(
        is_document_command(part[index + 1:next((end for end in range(index + 1, len(part)) if part[end] in {";", "+"}), len(part))], cwd)
        for index, arg in enumerate(part) if command == "find" and arg in FIND_EXEC
    )


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
