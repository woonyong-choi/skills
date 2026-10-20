"""README.en.md(없으면 README.md)와 docs/README.md 목록으로 llms.txt(--full이면 llms-full.txt도) 생성.

사용: python3 gen_llms.py [--full] (저장소 루트에서 실행)

인자: --full, --remote(기본 origin), --branch(기본 원격 HEAD 조회), --raw-base-url, --private-dir 반복(기본 .local 대체), 저장소 루트에서 실행
실행 조건: Python 3.9 이상, 표준 라이브러리, Git. URL 자동 구성은 github.com 원격만 지원
출력: llms.txt, --full이면 llms-full.txt, stdout 없음, stderr 실패 이유, 종료 0 성공·1 실행 실패·2 인자 오류
"""

from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

OPTIONAL_PREFIXES = ("docs/experiments/", "docs/decisions/")
# 머리 뒤 소개 문단이 없는 README 틀(repo-docs-readme)의 소개 절
INTRO_SECTIONS = ("Why", "해결하는 문제", "Problem and constraints", "문제와 제약")
IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
ITEM = re.compile(r"^(?: {2}){0,2}- \[(.+?)\]\((.+?)\)(?:: (\S.*))?$")
KEYWORD = re.compile(r"^(?: {2}){0,2}- [^\[\]:\s][^\[\]:]*$")
LIST_LINE = re.compile(r"^ *[-*+] ")
FENCE_LINE = re.compile(r"^[ \t]*(`{3,}|~{3,})")
LANGUAGE_LINE = re.compile(r"\|.*README[\w.-]*\.md|README[\w.-]*\.md.*\|")
FENCE = re.compile(
    r"^[ \t]*(`{3,}|~{3,}).*?^[ \t]*\1[ \t]*$\n?", re.MULTILINE | re.DOTALL
)
LINK = re.compile(
    r"\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)|!?\[[^\]]*\]\([^)]*\)|<a\b[^>]*>.*?</a>",
    re.IGNORECASE,
)


def raw_base_url(
    remote: str = "origin", branch: str | None = None, raw_url: str | None = None
) -> str:
    if raw_url:
        parsed = urllib.parse.urlsplit(raw_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.query
            or parsed.fragment
        ):
            raise SystemExit("invalid raw base URL")
        return raw_url.rstrip("/") + "/"
    url = subprocess.run(
        ["git", "remote", "get-url", remote], capture_output=True, text=True, check=True
    ).stdout.strip()
    match = re.fullmatch(
        r"(?:https?://github\.com/|git@github\.com:|ssh://git@github\.com/)([^/]+/[^/]+?)(?:\.git)?/?",
        url,
    )
    if not match:
        raise SystemExit(
            f"{remote}이 GitHub 저장소가 아님: {url}; --raw-base-url 지정 필요"
        )
    if branch is None:
        result = subprocess.run(
            ["git", "ls-remote", "--symref", remote, "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise SystemExit(
                f"cannot query {remote} HEAD: {result.stderr.strip()}; use --branch"
            )
        heads = [
            line.split()[1].removeprefix("refs/heads/")
            for line in result.stdout.splitlines()
            if line.startswith("ref: refs/heads/") and line.split()[-1] == "HEAD"
        ]
        if len(heads) != 1:
            raise SystemExit("cannot determine default branch; use --branch")
        branch = heads[0]
    return f"https://raw.githubusercontent.com/{match.group(1)}/{urllib.parse.quote(branch, safe='/')}/"


# 링크·태그·구분 기호를 지워 남는 글자가 없으면 이동 줄
def link_only(line: str) -> bool:
    if not LINK.search(line):
        return False
    rest = re.sub(r"<[^>]+>", "", LINK.sub("", line))
    return not re.sub(r"[\s·|/•–-]", "", rest)


def section_intro(blocks: list[str]) -> list[str]:
    """소개 절(INTRO_SECTIONS) 바로 아래 첫 문단. 없으면 빈 목록"""
    for index, block in enumerate(blocks[:-1]):
        if block.startswith("## ") and block[3:].strip() in INTRO_SECTIONS:
            for following in blocks[index + 1 :]:
                if following.startswith("#"):
                    break
                text = _paragraph_text(following)
                if text:
                    return [text]
            return []
    return []


def _paragraph_text(block: str) -> str:
    block = IMAGE.sub("", block).strip()
    block = re.sub(
        r"<h1[^>]*>.*?</h1>|^#{1,6} [^\n]*$",
        "",
        block,
        flags=re.MULTILINE | re.DOTALL,
    ).strip()
    if re.match(r">\s*\[!", block):
        return ""
    block = re.sub(r"^>[ \t]?", "", block, flags=re.MULTILINE)
    if re.match(r"(?:[-*+] |\d+[.)] |<(?:ul|ol)\b)", block, re.IGNORECASE):
        return ""
    lines = [
        line.strip()
        for line in block.splitlines()
        if not LANGUAGE_LINE.search(line) and not link_only(line)
    ]
    lines = [re.sub(r"<[^>]+>", "", line).strip() for line in lines]
    lines = [
        line
        for line in lines
        if line
        and not re.fullmatch(r"(?:-[ \t]*){2,}|(?:\*[ \t]*){2,}|(?:_[ \t]*){2,}", line)
    ]
    return " ".join(lines)


def read_rows() -> list[tuple[str, str, str]]:
    """목록 줄을 위에서부터 순서대로. 코드 블록 안 제외, 형식이 틀린 목록 줄과 표만 있는 옛 형식은 종료"""
    rows = []
    fence = ""
    table = False
    for number, line in enumerate(
        Path("docs/README.md").read_text(encoding="utf-8").splitlines(), 1
    ):
        text = line.rstrip("\n")
        marker = FENCE_LINE.match(text)
        if marker and (not fence or marker.group(1).startswith(fence)):
            fence = "" if fence else marker.group(1)
            continue
        if fence:
            continue
        if text.lstrip().startswith("|"):
            table = True
        elif LIST_LINE.match(text):
            match = ITEM.match(text)
            if match:
                title, target, summary = match.groups()
                if target.startswith("/") or re.search(r"[:?#\\]", target):
                    raise SystemExit("공개 문서 경로 아님: " + target)
                rows.append((title, target, summary or ""))
            elif not KEYWORD.fullmatch(text):
                raise SystemExit(
                    f"docs/README.md {number}번째 줄 목록 형식 아님(`- 키워드` 또는 `- [키워드](경로)`): {text.strip()}"
                )
    if table and not rows:
        raise SystemExit("docs/README.md가 목록 형식이 아님")
    return rows


# URL 파싱과 디코딩은 메모리에서만 수행
def _private_path(value: str, private_dirs: tuple[str, ...] = (".local",)) -> bool:
    decoded = html.unescape(value)
    while True:
        unquoted = urllib.parse.unquote(decoded)
        if unquoted == decoded:
            break
        decoded = unquoted
    path = urllib.parse.urlsplit(decoded.replace("\\", "/")).path
    parts = [part.casefold() for part in path.split("/") if part not in ("", ".")]
    return bool({name.casefold() for name in private_dirs}.intersection(parts))


def is_public(
    root: Path, relative: str, private_dirs: tuple[str, ...] = (".local",)
) -> bool:
    if _private_path(relative, private_dirs):
        return False
    real = (root / relative).resolve()
    if (
        Path(relative).is_absolute()
        or real.suffix != ".md"
        or not real.is_relative_to(root)
    ):
        return False
    real_relative = real.relative_to(root).as_posix()
    if _private_path(real_relative, private_dirs) or not real.is_file():
        return False
    return all(
        subprocess.run(
            ["git", "check-ignore", "-q", "--", path], check=False
        ).returncode
        == 1
        for path in (relative, real_relative)
    )


def main(
    full: bool,
    remote: str = "origin",
    branch: str | None = None,
    raw_url: str | None = None,
    private_dirs: tuple[str, ...] = (".local",),
) -> int:
    raw = raw_base_url(remote, branch, raw_url)
    rows = read_rows()
    root = Path.cwd().resolve()
    source = (
        "README.en.md"
        if Path("README.en.md").exists() or Path("README.en.md").is_symlink()
        else "README.md"
    )
    inputs = list(dict.fromkeys(["README.md", source, "docs/README.md"])) + [
        "docs/" + target for _, target, _ in rows
    ]
    if Path("CHANGELOG.md").exists() or Path("CHANGELOG.md").is_symlink():
        inputs.append("CHANGELOG.md")
    for relative in inputs:
        if not is_public(root, relative, private_dirs):
            raise SystemExit("공개 문서 경로 아님: " + relative)
    rows = [
        (
            title,
            (root / "docs" / target).resolve().relative_to(root).as_posix(),
            summary,
        )
        for title, target, summary in rows
    ]
    readme = FENCE.sub("", Path(source).read_text(encoding="utf-8"))
    readme = re.sub(r"^(#{2,6} [^\n]*)\n", r"\n\n\1\n\n", readme, flags=re.MULTILINE)
    blocks = [block.strip() for block in re.split(r"\n\s*\n", readme) if block.strip()]
    heading = re.search(
        r"<h1[^>]*>(.*?)</h1>|^# ([^\n]+)$", readme, re.MULTILINE | re.DOTALL
    )
    texts: list[str] = []
    for block_index, block in enumerate(blocks):
        if block.startswith("## "):
            if len(texts) == 1:
                texts.extend(section_intro(blocks[block_index:]))
            break
        text = _paragraph_text(block)
        if text:
            texts.append(text)
    if not heading or len(texts) < 2:
        raise SystemExit(
            f"{source} needs a title, a tagline paragraph and an intro paragraph"
        )
    tagline, intro = texts[0], texts[1]
    name = (
        html.unescape(
            " ".join(
                re.sub(r"<[^>]+>", " ", heading.group(1) or heading.group(2)).split()
            )
        )
        if heading
        else ""
    )
    if not name:
        raise SystemExit(
            f"{source} needs a title, a tagline paragraph and an intro paragraph"
        )
    main_rows = [row for row in rows if not row[1].startswith(OPTIONAL_PREFIXES)]
    optional_rows = [row for row in rows if row[1].startswith(OPTIONAL_PREFIXES)]
    index = [f"# {name}", "", f"> {tagline}", "", intro, "", "## Docs", ""]
    index += [
        f"- [{title}]({raw}{target})" + (f": {summary}" if summary else "")
        for title, target, summary in main_rows
    ]
    extra = [
        f"- [{title}]({raw}{target})" + (f": {summary}" if summary else "")
        for title, target, summary in optional_rows
    ]
    try:
        changelog_title = (
            Path("CHANGELOG.md")
            .read_text(encoding="utf-8")
            .partition("\n")[0]
            .lstrip("# ")
            .strip()
        )
        extra.append(f"- [{changelog_title}]({raw}CHANGELOG.md)")
    except FileNotFoundError:
        pass
    if extra:
        index += ["", "## Optional", ""] + extra
    parts = ["README.md"] + [target for _, target, _ in rows]
    full_text = [
        f"<!-- {part} -->\n\n" + Path(part).read_text(encoding="utf-8").strip() + "\n"
        for part in parts
    ]
    Path("llms.txt").write_text("\n".join(index) + "\n", encoding="utf-8")
    if full:
        Path("llms-full.txt").write_text("\n".join(full_text), encoding="utf-8")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--remote", default="origin")
    parser.add_argument(
        "--branch", help="default: remote HEAD; main only when explicitly selected"
    )
    parser.add_argument("--raw-base-url", help="raw document root URL for other hosts")
    parser.add_argument(
        "--private-dir",
        action="append",
        help="private directory name; repeated options replace the .local default",
    )
    args = parser.parse_args()
    if args.private_dir and any(
        not name or "/" in name or "\\" in name or name in {".", ".."}
        for name in args.private_dir
    ):
        parser.error("--private-dir requires one directory name")
    try:
        sys.exit(
            main(
                args.full,
                args.remote,
                args.branch,
                args.raw_base_url,
                tuple(args.private_dir) if args.private_dir else (".local",),
            )
        )
    except (OSError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
