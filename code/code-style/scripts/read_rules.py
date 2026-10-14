"""정본 문서에서 요청한 규칙 절만 출력.
인자: --ids 규칙ID [규칙ID ...] 또는 --catalog
출력: 규칙 ID·조건·정본 경로·본문 JSON, 잘못된 ID·손상된 정본은 stderr와 종료 2
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def select_rules(root: Path, identities: list[str]) -> list[dict]:
    manifest = json.loads((root / "references/rule-map.json").read_text())
    catalog = {row["id"]: row for row in manifest["sections"]}
    unknown = set(identities) - catalog.keys()
    if unknown:
        raise ValueError("unknown rule IDs: " + ", ".join(sorted(unknown)))
    output = []
    for identity in dict.fromkeys(identities):
        row = catalog[identity]
        text = (root / row["path"]).read_text()
        blocks = re.split(r"(?=^## )", text, flags=re.M)
        block = next(
            part for part in blocks if part.startswith("## " + row["title"] + "\n")
        )
        normalized = (
            block.replace("(cost.md)", "(references/cost.md)")
            if identity == "CS-COST"
            else block
        )
        if hashlib.sha256(normalized.encode()).hexdigest() != row["sha256"]:
            raise ValueError("rule changed; review source and catalog: " + identity)
        output.append(
            {
                "id": identity,
                "condition": row["condition"],
                "source": row["path"],
                "sha256": row["sha256"],
                "text": block,
            }
        )
    return output


# cost: time O(n), heap O(n), stack O(1), io O(f)
# vars: n = 선택한 정본 문서 바이트, f = 선택 규칙 수
# basis: estimate
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--catalog", action="store_true")
    mode.add_argument("--ids", nargs="+")
    args = parser.parse_args()
    try:
        if args.catalog:
            manifest = json.loads((ROOT / "references/rule-map.json").read_text())
            result = [
                {key: value for key, value in row.items() if key != "sha256"}
                for row in manifest["sections"]
            ]
        else:
            result = select_rules(ROOT, args.ids)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError, StopIteration) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
