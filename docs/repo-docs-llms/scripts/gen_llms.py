"""README.en.md(없으면 README.md)와 docs/README.md 목록으로 llms.txt(--full이면 llms-full.txt도) 생성.

사용: python3 gen_llms.py [--full] (저장소 루트에서 실행)

인자: --full, --remote(기본 origin), --branch(기본 원격 HEAD 조회), --raw-base-url, --private-dir 반복(기본 .local·archive 대체), 저장소 루트에서 실행
실행 조건: Python 3.9 이상, 표준 라이브러리, Git. URL 자동 구성은 github.com 원격만 지원
출력: llms.txt, --full이면 llms-full.txt, stdout 없음, stderr 실패 이유, 종료 0 성공·1 실행 실패·2 인자 오류
"""
from __future__ import annotations

import argparse
import re
import html
import urllib.parse
import subprocess
import sys
from pathlib import Path

OPTIONAL_PREFIXES = ("experiments/", "decisions/")
# 머리 뒤 소개 문단이 없는 README 틀(repo-docs-readme)의 소개 절
INTRO_SECTIONS = ("Why", "해결하는 문제", "Problem and constraints", "문제와 제약")
IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
# 분류(## 절) 아래 문서 줄: 들여쓰기 0~2단계, `- [제목](경로): 답하는 것`
ITEM = re.compile(r"^(?: {2}){0,2}- \[(.+?)\]\((.+?)\): (\S.*)$")
LIST_LINE = re.compile(r"^ *[-*+] ")
FENCE_LINE = re.compile(r"^[ \t]*(`{3,}|~{3,})")
LANGUAGE_LINE = re.compile(r"\|.*README[\w.-]*\.md|README[\w.-]*\.md.*\|")
FENCE = re.compile(r"^[ \t]*(`{3,}|~{3,}).*?^[ \t]*\1[ \t]*$\n?", re.MULTILINE | re.DOTALL)
LINK = re.compile(r"\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)|!?\[[^\]]*\]\([^)]*\)|<a\b[^>]*>.*?</a>", re.IGNORECASE)


def raw_base_url(remote: str = "origin", branch: str | None = None, raw_url: str | None = None) -> str:
    if raw_url:
        parsed = urllib.parse.urlsplit(raw_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.query or parsed.fragment:
            raise SystemExit("invalid raw base URL")
        return raw_url.rstrip("/") + "/"
    url = subprocess.run(["git", "remote", "get-url", remote], capture_output=True, text=True, check=True).stdout.strip()
    match = re.fullmatch(r"(?:https?://github\.com/|git@github\.com:|ssh://git@github\.com/)([^/]+/[^/]+?)(?:\.git)?/?", url)
    if not match:
        raise SystemExit(f"{remote}이 GitHub 저장소가 아님: {url}; --raw-base-url 지정 필요")
    if branch is None:
        result = subprocess.run(["git", "ls-remote", "--symref", remote, "HEAD"], capture_output=True, text=True)
        if result.returncode != 0:
            raise SystemExit(f"cannot query {remote} HEAD: {result.stderr.strip()}; use --branch")
        heads = [line.split()[1].removeprefix("refs/heads/") for line in result.stdout.splitlines() if line.startswith("ref: refs/heads/") and line.split()[-1] == "HEAD"]
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
            following = blocks[index + 1]
            return [] if following.startswith("#") else [" ".join(line.strip() for line in following.splitlines())]
    return []


def read_rows() -> list[tuple[str, str, str]]:
    """목록 줄을 위에서부터 순서대로. 코드 블록 안 제외, 형식이 틀린 목록 줄과 표만 있는 옛 형식은 종료"""
    rows = []
    fence = ""
    table = False
    for number, line in enumerate(open("docs/README.md", encoding="utf-8"), 1):
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
            if not match:
                raise SystemExit(f"docs/README.md {number}번째 줄 목록 형식 아님(`- [제목](경로): 답하는 것`): {text.strip()}")
            rows.append(match.groups())
    if table and not rows:
        raise SystemExit("docs/README.md가 목록 형식이 아님")
    return rows



# URL 파싱과 디코딩은 메모리에서만 수행
def _private_path(value: str, private_dirs: tuple[str, ...] = (".local", "archive")) -> bool:
    decoded = html.unescape(value)
    while True:
        unquoted = urllib.parse.unquote(decoded)
        if unquoted == decoded:
            break
        decoded = unquoted
    path = urllib.parse.urlsplit(decoded.replace("\\", "/")).path
    parts = [part.casefold() for part in path.split("/") if part not in ("", ".")]
    return bool({name.casefold() for name in private_dirs}.intersection(parts))

def is_public(root: Path, relative: str, private_dirs: tuple[str, ...] = (".local", "archive")) -> bool:
    if _private_path(relative, private_dirs):
        return False
    real = (root / relative).resolve()
    if Path(relative).is_absolute() or ".." in Path(relative).parts or real.suffix != ".md" or not real.is_relative_to(root):
        return False
    real_relative = real.relative_to(root).as_posix()
    if _private_path(real_relative, private_dirs) or not real.is_file():
        return False
    return all(subprocess.run(["git", "check-ignore", "-q", "--", path]).returncode == 1 for path in (relative, real_relative))


def main(full: bool, remote: str = "origin", branch: str | None = None, raw_url: str | None = None, private_dirs: tuple[str, ...] = (".local", "archive")) -> int:
    raw = raw_base_url(remote, branch, raw_url)
    rows = read_rows()
    root = Path.cwd().resolve()
    source = "README.en.md" if Path("README.en.md").exists() or Path("README.en.md").is_symlink() else "README.md"
    inputs = list(dict.fromkeys(["README.md", source, "docs/README.md"])) + ["docs/" + target for _, target, _ in rows]
    if Path("CHANGELOG.md").exists() or Path("CHANGELOG.md").is_symlink():
        inputs.append("CHANGELOG.md")
    for relative in inputs:
        if not is_public(root, relative, private_dirs):
            raise SystemExit("공개 문서 경로 아님: " + relative)
    readme = FENCE.sub("", open(source, encoding="utf-8").read())
    blocks = [block.strip() for block in re.split(r"\n\s*\n", readme) if block.strip()]
    heading = re.search(r"<h1[^>]*>(.*?)</h1>|^# ([^\n]+)$", readme, re.MULTILINE | re.DOTALL)
    texts = []
    for index, block in enumerate(blocks):
        if block.startswith("## "):
            if len(texts) == 1:
                texts.extend(section_intro(blocks[index:]))
            break
        block = IMAGE.sub("", block).strip()
        # 제목 줄만 지우고 같은 블록의 한 줄 소개는 유지
        block = re.sub(r"<h1[^>]*>.*?</h1>|^#{1,6} [^\n]*$", "", block, flags=re.MULTILINE | re.DOTALL).strip()
        if block.startswith(">"):
            if re.match(r">\s*\[!", block):
                continue
            block = re.sub(r"^>[ \t]?", "", block, flags=re.MULTILINE)
        lines = [line.strip() for line in block.splitlines() if not LANGUAGE_LINE.search(line) and not link_only(line)]
        lines = [re.sub(r"<[^>]+>", "", line).strip() for line in lines]
        lines = [line for line in lines if line]
        if lines:
            texts.append(" ".join(lines))
    if not heading or len(texts) < 2:
        raise SystemExit(f"{source} needs a title, a tagline paragraph and an intro paragraph")
    tagline, intro = texts[0], texts[1]
    name = html.unescape(" ".join(re.sub(r"<[^>]+>", " ", heading.group(1) or heading.group(2)).split())) if heading else ""
    if not name:
        raise SystemExit(f"{source} needs a title, a tagline paragraph and an intro paragraph")
    main_rows = [row for row in rows if not row[1].startswith(OPTIONAL_PREFIXES)]
    optional_rows = [row for row in rows if row[1].startswith(OPTIONAL_PREFIXES)]
    index = [f"# {name}", "", f"> {tagline}", "", intro, "", "## Docs", ""]
    index += [f"- [{title}]({raw}docs/{target}): {summary}" for title, target, summary in main_rows]
    extra = [f"- [{title}]({raw}docs/{target}): {summary}" for title, target, summary in optional_rows]
    try:
        changelog_title = open("CHANGELOG.md", encoding="utf-8").readline().lstrip("# ").strip()
        extra.append(f"- [{changelog_title}]({raw}CHANGELOG.md)")
    except FileNotFoundError:
        pass
    if extra:
        index += ["", "## Optional", ""] + extra
    parts = ["README.md"] + ["docs/" + target for _, target, _ in rows]
    full_text = [f"<!-- {part} -->\n\n" + open(part, encoding="utf-8").read().strip() + "\n" for part in parts]
    open("llms.txt", "w", encoding="utf-8").write("\n".join(index) + "\n")
    if full:
        open("llms-full.txt", "w", encoding="utf-8").write("\n".join(full_text))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", help="default: remote HEAD; main only when explicitly selected")
    parser.add_argument("--raw-base-url", help="raw document root URL for other hosts")
    parser.add_argument("--private-dir", action="append", help="private directory name; repeated options replace .local and archive defaults")
    args = parser.parse_args()
    if args.private_dir and any(not name or "/" in name or "\\" in name or name in {".", ".."} for name in args.private_dir):
        parser.error("--private-dir requires one directory name")
    try:
        sys.exit(main(args.full, args.remote, args.branch, args.raw_base_url, tuple(args.private_dir) if args.private_dir else (".local", "archive")))
    except (OSError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
