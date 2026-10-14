"""선택한 개발 범위와 필수 의존 규칙을 중복 없이 출력한다.

인자: topics는 하나 이상의 분류 이름, --help는 사용법.
출력: stdout에 선택 원문, stderr에 오류. 성공 0, 읽기 실패 1, 입력 오류 2.
"""

from __future__ import annotations

__all__ = ["main"]

import argparse
import logging
from pathlib import Path
from typing import Final

RULES: Final = (
    "requirements",
    "decisions",
    "data-and-concurrency",
    "resources",
    "interfaces",
    "infrastructure-cost",
    "operations",
    "diagnosis",
)
TOPICS: Final = {
    "product": RULES,
    "spec": ("requirements",),
    "choice": ("requirements", "decisions"),
    "data": ("data-and-concurrency",),
    "resources": ("requirements", "resources"),
    "interface": ("interfaces",),
    "external": ("interfaces", "operations"),
    "infrastructure": (
        "requirements",
        "decisions",
        "infrastructure-cost",
        "operations",
    ),
    "operations": ("operations",),
    "review": (),
}
logger = logging.getLogger(__name__)


# cost: time O(n+b), heap O(n+b), stack O(1), io k file reads and stdout
# vars: n = 분류 인자 수, b = 선택 원문의 총 길이, k = 선택 파일 수
# basis: estimate
def main() -> int:
    logging.basicConfig(level=logging.ERROR, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topics", nargs="+", choices=tuple(TOPICS))
    args = parser.parse_args()
    try:
        text = _read_rules(args.topics)
    except (OSError, UnicodeError) as error:
        logger.error("failed to read required rules: %s", error)
        return 1
    print(text, end="")
    return 0


# cost: time O(n+b), heap O(b), stack O(1), io k file reads
# vars: n = 분류 인자 수, b = 선택 원문의 총 길이, k = 선택 파일 수
# basis: estimate
def _read_rules(topics: list[str]) -> str:
    selected = {"diagnosis"}
    for topic in topics:
        selected.update(TOPICS[topic])
    root = Path(__file__).parent.parent / "references"
    sections = []
    for rule in RULES:
        if rule in selected:
            content = (root / f"{rule}.md").read_text(encoding="utf-8")
            sections.append(f"<!-- references/{rule}.md -->\n{content}")
    return "\n".join(sections)


if __name__ == "__main__":
    raise SystemExit(main())
