"""README.md와 docs/README.md로 llms.txt(--full이면 llms-full.txt도) 생성.

사용: python3 gen_llms.py [--full] (저장소 루트에서 실행)
"""
import re
import subprocess
import sys
from pathlib import Path

OPTIONAL_PREFIXES = ("experiments/", "decisions/")
ROW = re.compile(r"\| \[(.+?)\]\((.+?)\) \| (.+?) \|$")
LANGUAGE_LINE = re.compile(r"^(English|\[English\])[^\n]*\|")


# cost: time O(1), heap O(1), stack O(1), io 1
# basis: estimate
def raw_base_url() -> str:
    remote = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True, check=True).stdout.strip()
    match = re.search(r"github\.com[:/](.+?)(\.git)?$", remote)
    if not match:
        raise SystemExit("origin이 GitHub 저장소가 아님: " + remote)
    return f"https://raw.githubusercontent.com/{match.group(1)}/main/"


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


# cost: time O(p), heap O(p), stack O(1), io 2
# vars: p = 경로 길이
# basis: estimate
def is_public(root: Path, relative: str) -> bool:
    real = (root / relative).resolve()
    if Path(relative).is_absolute() or ".." in Path(relative).parts or real.suffix != ".md" or not real.is_relative_to(root):
        return False
    real_relative = real.relative_to(root).as_posix()
    return all(subprocess.run(["git", "check-ignore", "-q", "--", path]).returncode == 1 for path in (relative, real_relative))


# cost: time O(t), heap O(t), stack O(1), io 1 + n
# vars: t = README와 표 문서 글자 수 합, n = 표 행 수
# basis: estimate
def main(full: bool) -> int:
    raw = raw_base_url()
    rows = read_rows()
    root = Path.cwd().resolve()
    for relative in ["README.md", "docs/README.md"] + ["docs/" + target for _, target, _ in rows]:
        if not is_public(root, relative):
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
    sys.exit(main("--full" in sys.argv[1:]))
