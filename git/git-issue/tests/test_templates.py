"""이슈 #35: 종류별 완료 조건의 체크박스와 확인 수단 계약."""

import re
from pathlib import Path

import pytest

REFERENCES = Path(__file__).resolve().parents[1] / "references"


# cost: time O(n), heap O(n), stack O(1), io 1
# vars: n = 틀 글자 수
# basis: estimate
@pytest.mark.parametrize("kind", ["design", "bug", "build", "experiment"])
def test_issue_template_has_verifiable_completion_criteria(kind: str) -> None:
    template = (REFERENCES / f"{kind}.md").read_text(encoding="utf-8")
    body = template.split("```text\n", 1)[1].split("```", 1)[0]

    sections = re.split(r"^## ", body, flags=re.MULTILINE)
    criteria = [section for section in sections if section.startswith("완료 조건\n")]

    assert len(criteria) == 1, f"{kind}: 완료 조건 절 하나 필수"
    items = [line for line in criteria[0].splitlines()[1:] if line.strip()]
    assert items, f"{kind}: 완료 조건 항목 필수"
    assert all(re.fullmatch(r"- \[ \] .+ \(확인: .+\)", item) for item in items)
