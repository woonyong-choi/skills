"""GitHub에 게시할 글의 저장소 링크와 비공개 경로를 검사한다.
인자: --repo 저장소, --remote 원격(기본 origin), --fix 선택, UTF-8 파일 또는 생략·-로 stdin
출력: stdout 위반 또는 수정 본문, stderr 수정 후 위반·입력 오류, 종료 0 통과·1 위반·2 입력 오류
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

_LINK = re.compile(
    r'!?\[[^\]\n]*\]\(\s*(?P<link><[^>\n]+>|(?:[^\s()]|\([^()\n]*\))+)(?:\s+["\'][^\n]*?["\'])?\s*\)'
    r"|^ {0,3}\[[^\]\n]+\]:\s*(?P<reference><[^>\n]+>|\S+)"
    r'|\b(?:href|src)=["\'](?P<html>[^"\']+)["\']',
    re.MULTILINE,
)
_CODE = re.compile(r"(?<!`)(?P<ticks>`{1,2})(?!`)(?P<path>[^`\n]+)(?P=ticks)(?!`)")
_REGEXP_CONTEXT = re.compile(r"(?:정규식|\bregexp\b)[ \t:]*$", re.IGNORECASE)
_HTTP_REQUEST = re.compile(
    r"(?:GET|HEAD|POST|PUT|DELETE|OPTIONS|TRACE|PATCH) (?P<path>/(?!/)\S*)"
)
_URL = re.compile(r'https?://[^\s<>`"\'\])]+')
_CLOSING_TAG = re.compile(r"</[A-Za-z][\w:-]*\s*>")
_LOCAL = re.compile(
    r"(?<![^\s(\[{'\"`<])(?:"
    r"file://[^\s<>`]+|(?:~|\$HOME|\$\{HOME\})[/\\][^\s<>`]*"
    r"|[A-Za-z]:[\\/][^\s<>`]+|\\\\[^\s<>`]+|/[^\s<>`]+"
    r"|(?:[^\s/<>`\"'()\[\]{}]+/)*\.local(?:/[^\s<>`]*)?(?![\w.-])"
    r"|(?:[^\s/\\<>`\"'()\[\]{}]+[/\\])*[^\s/\\<>`\"'()\[\]{}]+\.wt"
    r"(?=[/\\\s<>`\"'()\[\]{}]|$)(?:[/\\][^\s<>`]*)?"
    r"|(?:\.\./)+[^\s<>`]+)",
)
_LINES = re.compile(r"(?::|#L)(\d+)(?:-(?:L)?(\d+))?$")


@dataclass(frozen=True)
class _Repository:
    name: str
    visibility: str
    branch: str


@dataclass(frozen=True)
class _Finding:
    start: int
    end: int
    reason: str
    replacement: str | None = None


class _Context:
    def __init__(self, root: Path, remote_name: str = "origin") -> None:
        self.root = Path(_run(["git", "-C", str(root), "rev-parse", "--show-toplevel"]))
        remote = self.git("remote", "get-url", remote_name)
        match = re.fullmatch(
            r"(?:https?://github\.com/|git@github\.com:|ssh://git@github\.com/)"
            r"([^/]+/[^/]+?)(?:\.git)?/?",
            remote,
        )
        if match is None:
            raise ValueError(f"{remote_name} must be a github.com repository")
        self.repositories: dict[str, _Repository] = {}
        self.target = self.lookup(match[1])
        self.sha = self.git("rev-parse", "--revs-only", "HEAD")
        self.files = (
            set(self.git("ls-tree", "-r", "--name-only", "-z", "HEAD").split("\0"))
            if self.sha
            else set()
        )

    def git(self, *args: str) -> str:
        return _run(["git", "-C", str(self.root), *args])

    def lookup(self, name: str) -> _Repository:
        key = name.removesuffix(".git").lower()
        if key not in self.repositories:
            data = json.loads(
                _run(
                    [
                        "gh",
                        "repo",
                        "view",
                        key,
                        "--json",
                        "visibility,defaultBranchRef,nameWithOwner",
                    ]
                )
            )
            visibility = data["visibility"]
            if visibility not in {"PUBLIC", "PRIVATE", "INTERNAL"}:
                raise ValueError("unknown repository visibility")
            repository = _Repository(
                data["nameWithOwner"],
                visibility,
                (data["defaultBranchRef"] or {}).get("name", ""),
            )
            self.repositories[key] = repository
            self.repositories[repository.name.lower()] = repository
        return self.repositories[key]


def _run(command: list[str]) -> str:
    result = subprocess.run(
        command, capture_output=True, text=True, timeout=30, check=True
    )
    return result.stdout.rstrip("\n")


def _is_local(value: str) -> bool:
    value = unquote(value)
    return (
        value.startswith(("/", "~", "$HOME", "${HOME}", "file:", "\\\\"))
        or re.match(r"^[A-Za-z]:[\\/]", value) is not None
        or ".local" in value.replace("\\", "/").split("/")
        or any(
            part.endswith(".wt") and part != ".wt"
            for part in value.replace("\\", "/").split("/")
        )
    )


def _check_url(value: str, context: _Context) -> str | None:
    parsed = urlsplit(value)
    if ".local" in unquote(parsed.path).split("/"):
        return "private path: do not publish; summarize without its location"
    if parsed.hostname not in {
        "github.com",
        "www.github.com",
        "raw.githubusercontent.com",
    }:
        return None
    parts = unquote(parsed.path).strip("/").split("/")
    if len(parts) < 2:
        return None
    if parsed.hostname in {"github.com", "www.github.com"}:
        if len(parts) >= 3 and tuple(parts[:2]) in {
            ("user-attachments", "assets"),
            ("user-attachments", "files"),
        }:
            return None
        if (
            len(parts) == 2
            and parts[0] == "advisories"
            and re.fullmatch(r"GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}", parts[1])
        ):
            return None
    repository = context.lookup("/".join(parts[:2]))
    if (
        repository.visibility != "PUBLIC"
        and repository.name.lower() != context.target.name.lower()
    ):
        return "private repository: do not publish; summarize without its address"
    if (
        len(parts) >= 4
        and parts[2] == "blob"
        and re.match(r"L\d", parsed.fragment)
        and re.fullmatch(r"[0-9a-fA-F]{40}", parts[3]) is None
    ):
        return "code lines require a full commit SHA"
    return None


def _check_path(
    value: str, context: _Context, *, is_link: bool
) -> tuple[str | None, str | None]:
    value = unquote(value)
    if _is_local(value):
        return "private path: do not publish; summarize without its location", None
    suffix = _LINES.search(value)
    path = value[: suffix.start()] if suffix else value.split("#", 1)[0]
    fragment = ""
    if suffix:
        fragment = f"#L{suffix[1]}" + (f"-L{suffix[2]}" if suffix[2] else "")
    elif "#" in value:
        fragment = "#" + value.split("#", 1)[1]
    resolved = (context.root / path).resolve()
    if not resolved.is_relative_to(context.root):
        return (
            "path outside repository: do not publish; summarize without its location",
            None,
        )
    relative = resolved.relative_to(context.root).as_posix()
    if relative not in context.files:
        if resolved.is_file():
            return (
                "unpublished file: do not publish; summarize without its location",
                None,
            )
        return (
            ("relative link has no published file", None) if is_link else (None, None)
        )
    ref = context.sha if suffix else context.target.branch
    if not ref:
        raise ValueError("default branch is unavailable")
    url = f"https://github.com/{context.target.name}/blob/{quote(ref, safe='/')}/{quote(relative)}{fragment}"
    return (
        (
            "relative repository link: replace with a public web link"
            if is_link
            else "repository path in code text: replace with a public web link"
        ),
        url,
    )


def _check_target(
    value: str, context: _Context, *, is_link: bool
) -> tuple[str | None, str | None]:
    if value.startswith(("https://", "http://")):
        return _check_url(value, context), None
    if value.startswith(("#", "mailto:")):
        return None, None
    return _check_path(value, context, is_link=is_link)


def _scan(text: str, context: _Context) -> list[_Finding]:
    findings: list[_Finding] = []
    code_matches = list(_CODE.finditer(text))
    code_spans = [match.span() for match in code_matches]
    covered: list[tuple[int, int]] = []
    ignored_local_spans = [
        match.span()
        for pattern in (_URL, _CLOSING_TAG)
        for match in pattern.finditer(text)
    ]
    for match in code_matches:
        if re.match(r"//[ \t]", match["path"].lstrip()):
            prefix_start = (
                match.start("path") + len(match["path"]) - len(match["path"].lstrip())
            )
            ignored_local_spans.append((prefix_start, prefix_start + 2))
    for pattern in (_LINK, _CODE, _URL):
        for match in pattern.finditer(text):
            if any(
                match.start() < end and start < match.end() for start, end in covered
            ):
                continue
            start, end = match.span()
            covered.append((start, end))
            value = match[0]
            is_link = pattern is _LINK and not any(
                code_start <= start and end <= code_end
                for code_start, code_end in code_spans
            )
            if pattern is _LINK:
                group = next(
                    name
                    for name, value in match.groupdict().items()
                    if value is not None
                )
                start, end = match.span(group)
                value = match[group].strip("<>")
            elif pattern is _CODE:
                value = match["path"].strip()
                if re.match(r"//[ \t]", value):
                    covered.pop()
                    continue
                line_start = text.rfind("\n", 0, start) + 1
                is_regexp = (
                    re.fullmatch(r"/[A-Za-z0-9_-]+/", value) is not None
                    and _REGEXP_CONTEXT.search(text[line_start:start]) is not None
                )
                request = _HTTP_REQUEST.fullmatch(value)
                is_http_request = request is not None and not _is_local(
                    urlsplit(request["path"]).path.removeprefix("/")
                )
                if re.fullmatch(r"/[\w-]+", value) or is_http_request or is_regexp:
                    ignored_local_spans.append((start, end))
                    continue
            reason, replacement = _check_target(value, context, is_link=is_link)
            if pattern is _CODE and replacement:
                replacement = f"[{value}]({replacement})"
            if reason:
                findings.append(_Finding(start, end, reason, replacement))
            elif pattern is _CODE and not value.startswith(("https://", "http://")):
                covered.pop()
    for match in _LOCAL.finditer(text):
        if any(start <= match.start() < end for start, end in ignored_local_spans):
            continue
        if any(finding.start <= match.start() < finding.end for finding in findings):
            continue
        findings.append(
            _Finding(
                match.start(),
                match.end(),
                "private path: do not publish; summarize without its location",
            )
        )
    return sorted(findings, key=lambda finding: finding.start)


def _fix(text: str, findings: list[_Finding]) -> str:
    for finding in reversed(findings):
        if finding.replacement is not None:
            text = text[: finding.start] + finding.replacement + text[finding.end :]
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "file", nargs="?", default="-", help="UTF-8 body file or - for stdin"
    )
    parser.add_argument(
        "--repo", type=Path, default=Path.cwd(), help="posting repository root"
    )
    parser.add_argument(
        "--fix", action="store_true", help="write revised body to stdout"
    )
    parser.add_argument("--remote", default="origin", help="GitHub remote name")
    args = parser.parse_args(argv)
    try:
        text = (
            sys.stdin.read()
            if args.file == "-"
            else Path(args.file).read_text(encoding="utf-8")
        )
        context = _Context(args.repo, args.remote)
        findings = _scan(text, context)
        if args.fix:
            text = _fix(text, findings)
            findings = _scan(text, context)
            sys.stdout.write(text)
        for finding in findings:
            line = text.count("\n", 0, finding.start) + 1
            print(
                f"{line}: {finding.reason}", file=sys.stderr if args.fix else sys.stdout
            )
        return 1 if findings else 0
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
    ) as error:
        print(f"public links check failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
