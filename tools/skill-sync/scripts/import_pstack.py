"""cursor/plugins의 pstack 영어 원본을 lazy-mode/_upstream/에 갱신하고 바뀐 원본 파일을 알린다.

사용: python3 import_pstack.py --source <cursor/plugins 작업본> [--dest <이 저장소>]
인자: --source cursor/plugins git 작업본(pstack/ 포함), --dest 저장소 루트(기본 이 저장소)
출력: stdout 원본 버전·commit과 바뀐 파일 목록(`+` 추가, `-` 삭제, `~` 변경), 종료 0 성공·1 원본 형식 오류·2 인자 오류
한국어 이식본(lazy-mode/<스킬>/)은 건드리지 않는다. 목록을 보고 이식본에 같은 변경을 옮긴다
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

UPSTREAM = "_upstream"
REPOSITORY = "https://github.com/cursor/plugins"


class UpstreamError(Exception):
    """원본 형식이 기대와 다름"""


# cost: time O(1), heap O(1), stack O(1), io 1
# basis: estimate
def commit_of(source: Path) -> str:
    done = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    if done.returncode:
        raise UpstreamError(f"git 작업본 아님: {source}")
    return done.stdout.strip()


# cost: time O(b), heap O(f), stack O(d), io O(f)
# vars: b = 폴더 바이트, f = 파일 수, d = 폴더 깊이
# basis: estimate
def digests(root: Path) -> dict[str, str]:
    if not root.is_dir():
        return {}
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file() and "node_modules" not in path.parts and path.name != "SOURCE.json"
    }


# cost: time O(b), heap O(f), stack O(d), io O(f)
# vars: b = 원본 바이트, f = 원본 파일 수, d = 폴더 깊이
# basis: estimate
def refresh(source: Path, dest: Path) -> tuple[dict, list[str]]:
    root = source / "pstack"
    manifest = json.loads((root / "plugin.json").read_text(encoding="utf-8"))
    if not any((root / "skills").glob("*/SKILL.md")):
        raise UpstreamError("pstack/skills 아래 스킬 없음")
    target = dest / "lazy-mode" / UPSTREAM
    before = digests(target)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(root, target, ignore=shutil.ignore_patterns("node_modules", ".DS_Store"))
    after = digests(target)
    changes = sorted(
        [f"+ {name}" for name in after.keys() - before.keys()]
        + [f"- {name}" for name in before.keys() - after.keys()]
        + [f"~ {name}" for name in after.keys() & before.keys() if after[name] != before[name]],
        key=lambda line: line[2:],
    )
    record = {"repository": REPOSITORY, "path": "pstack", "commit": commit_of(source), "version": manifest.get("version"), "skills": len(list((root / "skills").glob("*/SKILL.md")))}
    (target / "SOURCE.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record, changes


# cost: time O(b), heap O(f), stack O(d), io O(f)
# vars: b = 원본 바이트, f = 원본 파일 수, d = 폴더 깊이
# basis: estimate
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--dest", type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args(argv)
    try:
        record, changes = refresh(args.source.resolve(), args.dest.resolve())
    except (UpstreamError, OSError, ValueError, KeyError) as error:
        print(error, file=sys.stderr)
        return 1
    print(f"pstack {record['version']} {record['commit'][:7]}: 원본 스킬 {record['skills']}개, 바뀐 파일 {len(changes)}개")
    print("\n".join(changes))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
