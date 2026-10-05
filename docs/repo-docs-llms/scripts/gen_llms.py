"""README.md와 docs/README.md로 llms.txt(--full이면 llms-full.txt도) 생성.

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
ROW = re.compile(r"\| \[(.+?)\]\((.+?)\) \| (.+?) \|$")
LANGUAGE_LINE = re.compile(r"^(English|\[English\])[^\n]*\|")


# cost: time O(n), heap O(n), stack O(1), io 2
# vars: n = 원격 URL과 HEAD 응답 길이
# basis: estimate
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
        output = subprocess.run(["git", "ls-remote", "--symref", remote, "HEAD"], capture_output=True, text=True, check=True).stdout
        heads = [line.split()[1].removeprefix("refs/heads/") for line in output.splitlines() if line.startswith("ref: refs/heads/") and line.split()[-1] == "HEAD"]
        if len(heads) != 1:
            raise SystemExit("cannot determine default branch; use --branch")
        branch = heads[0]
    return f"https://raw.githubusercontent.com/{match.group(1)}/{urllib.parse.quote(branch, safe='/')}/"


# cost: time O(c), heap O(r), stack O(1), io 1
# vars: c = docs/README.md 글자 수, r = 문서 표 행 수
# basis: estimate
def read_rows() -> list[tuple[str, str, str]]:
    rows = []
    in_fence = False
    for line in open("docs/README.md", encoding="utf-8"):
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        match = None if in_fence else ROW.match(line.rstrip("\n"))
        if match:
            rows.append(match.groups())
    return rows



# cost: time O(n * d), heap O(n), stack O(1)
# vars: n = 경로 길이, d = 중첩 URL 이스케이프 깊이
# basis: estimate
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

# cost: time O(p), heap O(p), stack O(1), io 2
# vars: p = 경로 길이
# basis: estimate
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


# cost: time O(t), heap O(t), stack O(1), io O(n)
# vars: t = README와 표 문서 글자 수 합, n = 표 행 수
# basis: estimate
def main(full: bool, remote: str = "origin", branch: str | None = None, raw_url: str | None = None, private_dirs: tuple[str, ...] = (".local", "archive")) -> int:
    raw = raw_base_url(remote, branch, raw_url)
    rows = read_rows()
    root = Path.cwd().resolve()
    inputs = ["README.md", "docs/README.md"] + ["docs/" + target for _, target, _ in rows]
    if Path("CHANGELOG.md").exists() or Path("CHANGELOG.md").is_symlink():
        inputs.append("CHANGELOG.md")
    for relative in inputs:
        if not is_public(root, relative, private_dirs):
            raise SystemExit("공개 문서 경로 아님: " + relative)
    readme = open("README.md", encoding="utf-8").read()
    blocks = [block.strip() for block in re.split(r"\n\s*\n", readme) if block.strip()]
    heading = re.search(r"<h1[^>]*>(.*?)</h1>|^# (.+)$", readme, re.MULTILINE)
    name = (heading.group(1) or heading.group(2)).strip()
    texts = []
    for block in blocks:
        if re.match(r"<h1|# ", block):
            continue
        lines = [re.sub(r"<[^>]+>", "", line).strip() for line in block.splitlines()]
        lines = [line for line in lines if line and not LANGUAGE_LINE.match(line) and " · " not in line]
        if lines:
            texts.append(" ".join(lines))
    tagline, intro = texts[0], texts[1]
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
