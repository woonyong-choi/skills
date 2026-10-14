"""정본 문서에서 요청한 규칙 절만 출력.
인자: --ids ID... 또는 --catalog. --text는 원문, --language NAME...은 언어 원문 추가
출력: 기본 JSON. --text는 조건·출처·원문과 필수 참조. 실패 시 부분 출력 없이 stderr·2
"""

from __future__ import annotations

__all__ = ["select_rules", "main", "parse_arguments", "read_dependencies"]

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def select_rules(root: Path, identities: list[str]) -> list[dict]:
    catalog = {row["id"]: row for row in _read_catalog(root)}
    unknown = set(identities) - catalog.keys()
    if unknown:
        raise ValueError("unknown rule IDs: " + ", ".join(sorted(unknown)))
    output = []
    contents = {}
    for identity in dict.fromkeys(identities):
        row = catalog[identity]
        source = root / row["path"]
        if source not in contents:
            contents[source] = source.read_text(encoding="utf-8")
        text = contents[source]
        blocks = re.split(r"(?=^## )", text, flags=re.M)
        block = next(
            (part for part in blocks if part.startswith("## " + row["title"] + "\n")),
            None,
        )
        if block is None:
            raise ValueError(f"rule section missing: {identity} in {source}")
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
# vars: n = 선택 규칙·언어·참조 바이트, f = 선택 규칙·언어·참조 파일 수
# basis: estimate
def main() -> int:
    args = parse_arguments()
    try:
        if args.catalog:
            result = [
                {key: value for key, value in row.items() if key != "sha256"}
                for row in _read_catalog(ROOT)
            ]
        else:
            identities = (["CS-LANGUAGE"] if args.language else []) + args.ids
            result = select_rules(ROOT, identities)
        if args.text:
            output = [
                f"<!-- {row['id']} | {row['condition']} | code-style/{row['source']} -->\n{row['text']}"
                for row in result
            ]
            output.extend(read_dependencies(result, args.language or []))
            print("\n".join(output))
        else:
            print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError) as error:
        print(str(error), file=sys.stderr)
        return 2


def parse_arguments(arguments: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--catalog", action="store_true")
    mode.add_argument("--ids", nargs="+")
    parser.add_argument("--text", action="store_true")
    parser.add_argument("--language", nargs="+", action="extend", metavar="NAME")
    args = parser.parse_args(arguments)
    if args.text and not args.ids:
        parser.error("--text requires --ids")
    if args.language and not (args.ids and args.text):
        parser.error("--language requires --ids and --text")
    return args


# cost: time O(b), heap O(b), stack O(1), io k file reads
# vars: b = 필수 참조 바이트, k = 중복 제거한 참조 파일 수
# basis: estimate
def read_dependencies(rules: list[dict], languages: list[str]) -> list[str]:
    sources = []
    for language in dict.fromkeys(languages):
        if not re.fullmatch(r"[a-z][a-z0-9-]*", language):
            raise ValueError("invalid language name: " + language)
        name = "code-style-" + language
        source = ROOT.parent / name / "SKILL.md"
        sources.append((name + "/SKILL.md", source))
    if any(row["id"] == "CS-COST" for row in rules):
        sources.append(("code-style/references/cost.md", ROOT / "references/cost.md"))
    return [
        f"<!-- {name} -->\n{source.read_text(encoding='utf-8')}"
        for name, source in sources
    ]


# cost: time O(n), heap O(n), stack O(1), io 1
# vars: n = 목록 파일 바이트
# basis: estimate
def _read_catalog(root: Path) -> list[dict]:
    source = root / "references/rule-map.json"
    manifest = json.loads(source.read_text(encoding="utf-8"))
    rows = manifest.get("sections") if isinstance(manifest, dict) else None
    fields = ("id", "title", "path", "condition", "sha256")
    if not isinstance(rows, list) or any(
        not isinstance(row, dict)
        or any(not isinstance(row.get(field), str) for field in fields)
        for row in rows
    ):
        raise ValueError(f"invalid rule catalog: {source}")
    identities = [row["id"] for row in rows]
    if len(set(identities)) != len(identities):
        raise ValueError(f"duplicate rule ID in catalog: {source}")
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
