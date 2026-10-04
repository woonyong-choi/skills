"""git-issue 종류 절의 제목 길이와 종류별 끝말을 게시 전에 검사한다."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ENDINGS = {
    "design": ("결정",),
    "build": ("추가", "구현", "변경"),
    "bug": ("수정",),
    "experiment": ("측정",),
    "docs": ("문서 갱신",),
}


# cost: time O(n), heap O(n), stack O(1), io 1 + 위반 수
# vars: n = 입력 제목 길이
# basis: estimate
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", required=True, choices=_ENDINGS)
    parser.add_argument(
        "file", nargs="?", default="-", help="UTF-8 title file or - for stdin"
    )
    args = parser.parse_args(argv)
    try:
        title = (
            sys.stdin.read()
            if args.file == "-"
            else Path(args.file).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError) as error:
        print(f"issue title check failed: {error}", file=sys.stderr)
        return 2
    findings = _check(title.removesuffix("\n").removesuffix("\r"), args.kind)
    for finding in findings:
        print(f"1: {finding}")
    return 1 if findings else 0


def _check(title: str, kind: str) -> list[str]:
    if not title.strip() or len(title.splitlines()) != 1:
        return ["title must be one non-empty line"]
    findings = []
    if len(title) > 20:
        findings.append(f"title exceeds 20 characters: {len(title)}")
    endings = _ENDINGS[kind]
    if not any(
        title.endswith(" " + ending) and title[: -len(ending) - 1].strip()
        for ending in endings
    ):
        findings.append(
            f"{kind} title requires a target and ending: {' / '.join(endings)}"
        )
    return findings


if __name__ == "__main__":
    sys.exit(main())
