"""인자: 없음.
출력: 현재 카탈로그 무결성·작업별 UTF-8 바이트 JSON, 불일치 종료 1.
현재 해시 일치는 과거 규칙의 의미 보존을 증명하지 않는다."""

import hashlib
import json
from pathlib import Path
import re


# cost: time O(n), heap O(n), stack O(1), io O(f)
# vars: n = 규칙 문서 바이트, f = 규칙 문서 수
# basis: estimate
def main() -> int:
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "references/rule-map.json").read_text())
    failures = []
    for rule in manifest["sections"]:
        text = (root / rule["path"]).read_text()
        sections = re.split(r"(?=^## )", text, flags=re.M)
        section = next(
            (s for s in sections if s.startswith("## " + rule["title"] + "\n")), ""
        )
        if rule["title"] == "비용 주석":
            section = section.replace("(cost.md)", "(references/cost.md)")
        if hashlib.sha256(section.encode()).hexdigest() != rule["sha256"]:
            failures.append(rule["title"])
    core_bytes = (root / "SKILL.md").stat().st_size
    paths = {
        "review": ["language", "structure", "errors"],
        "api": ["language", "structure", "errors", "cost-policy", "testing"],
        "ui": ["language", "structure"],
        "refactor": ["language", "structure", "testing"],
    }
    workloads = {
        name: core_bytes
        + sum((root / "references" / (p + ".md")).stat().st_size for p in refs)
        for name, refs in paths.items()
    }
    print(
        json.dumps(
            {
                "catalog_failures": failures,
                "semantic_preservation": "requires source comparison",
                "core_bytes": core_bytes,
                "workload_bytes": workloads,
                "unit": "UTF-8 bytes; not model tokens; language and dependent skills excluded",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
