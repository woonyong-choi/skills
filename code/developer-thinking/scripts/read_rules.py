"""현재 판단에 필요한 소유 규칙을 실행 순서대로 한 번씩 출력한다.

인자: topics는 하나 이상의 분류 이름, --help는 사용법.
출력: stdout 원문, stderr 진단. 성공 0, 읽기 실패 1, 입력 오류 2.
실행 조건: Python 3.9 이상·표준 라이브러리. 원본·평탄한 설치 구조 지원.
"""

from __future__ import annotations

__all__ = ["main"]

import argparse
import logging
from pathlib import Path
from typing import Final

RULES: Final = {
    "choice": (
        "repo-docs-design",
        "SKILL.md",
        ("적용", "요구 확인", "선택", "설명과 조사", "구조 경계"),
    ),
    "requirements": ("repo-docs-design", "references/requirements.md", ()),
    "infrastructure": ("repo-docs-design", "references/infrastructure.md", ()),
    "data-and-concurrency": ("code-style", "references/data-and-concurrency.md", ()),
    "resources": ("code-style", "references/resources.md", ()),
    "operations": ("code-style", "references/operations.md", ()),
    "interfaces": ("code-style", "references/interfaces.md", ()),
    "review": ("code-style", "SKILL.md", ("검증",)),
}
TOPICS: Final = {
    "product": tuple(RULES),
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
    parser.add_argument("topics", nargs="+", choices=tuple(TOPICS))
    args = parser.parse_args()
    try:
        text = _read_rules(args.topics)
    except (OSError, UnicodeError, ValueError) as error:
        logger.error("failed to read required rules: %s", error)
        return 1
    print(text, end="")
    return 0


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
    blocks = {part.split("\n", 1)[0]: "## " + part for part in text.split("\n## ")[1:]}
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
    for rule, (owner, path, headings) in RULES.items():
        if rule in selected:
            content = (_owner_path(owner) / path).read_text(encoding="utf-8")
            output.append(
                f"<!-- {owner}/{path} -->\n" + _select_sections(content, headings)
            )
    return "\n".join(output)


if __name__ == "__main__":
    raise SystemExit(main())
