"""스킬 원본 저장소 하나를 Codex, Antigravity, Claude Code에 같은 내용으로 설치하고 Claude 계정용 zip 생성.

사용:
  python3 install.py [--source 원본 저장소]          설치된 도구 폴더에 동기화, dist/claude/*.zip 생성
  python3 install.py --dry-run                      바꿀 내용만 출력
  python3 install.py --remove 이름 [이름 ...]       도구 폴더에서 해당 스킬을 휴지통 폴더로 이동

원본 저장소 찾는 순서: --source, 환경 변수 SKILLS_SOURCE, 이 스크립트가 든 git 저장소, 마지막으로 쓴 원본(~/.config/skills/source)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
import zipfile
from pathlib import Path

HOME = Path.home()
TARGETS = {
    "codex": HOME / ".codex" / "skills",
    "antigravity": HOME / ".gemini" / "config" / "skills",
    "claude-code": HOME / ".claude" / "skills",
}
TOOL_HOMES = {"codex": HOME / ".codex", "antigravity": HOME / ".gemini", "claude-code": HOME / ".claude"}
MANIFEST = ".repo-skills.json"
POINTER = HOME / ".config" / "skills" / "source"
TRASH = HOME / ".skill-trash"
SKIP = {"__pycache__", ".DS_Store"}


# cost: time O(k), heap O(k), stack O(1), io k
# vars: k = 원본 폴더 항목 수
# basis: estimate
def is_skill_source(folder: Path) -> bool:
    return folder.is_dir() and any((path / "SKILL.md").is_file() for path in folder.iterdir())


# cost: time O(k), heap O(1), stack O(1), io 4 + k
# vars: k = 후보 폴더 항목 수
# basis: estimate
def resolve_source(argument: str | None) -> Path:
    own_repository = Path(__file__).resolve().parents[2]
    candidates = [
        Path(argument).expanduser() if argument else None,
        Path(os.environ["SKILLS_SOURCE"]).expanduser() if os.environ.get("SKILLS_SOURCE") else None,
        own_repository if (own_repository / ".git").exists() else None,
        Path(POINTER.read_text().strip()).expanduser() if POINTER.is_file() else None,
    ]
    for candidate in candidates:
        if candidate is not None and is_skill_source(candidate):
            return candidate.resolve()
    raise SystemExit("스킬 원본 저장소를 찾지 못함: --source로 경로 지정")


# cost: time O(k), heap O(k), stack O(1), io k
# vars: k = 원본 폴더 항목 수
# basis: estimate
def source_skills(source: Path) -> list[Path]:
    return sorted(path for path in source.iterdir() if (path / "SKILL.md").is_file())


# cost: time O(b), heap O(f), stack O(d), io f
# vars: b = 스킬 폴더 바이트 수, f = 파일 수, d = 폴더 깊이
# basis: estimate
def tree_hash(folder: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(folder.rglob("*")):
        if path.is_file() and not SKIP.intersection(path.parts):
            digest.update(path.relative_to(folder).as_posix().encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


# cost: time O(b), heap O(1), stack O(1), io 1
# vars: b = 옮기는 폴더 바이트 수(다른 볼륨일 때만)
# basis: estimate
def move_to_trash(path: Path) -> None:
    if not path.exists():
        return
    label = path.parent.relative_to(HOME).as_posix().replace("/", "_") if path.parent.is_relative_to(HOME) else "other"
    destination = TRASH / time.strftime("%Y%m%d-%H%M%S") / label / path.name
    while destination.exists():
        destination = destination.with_name(destination.name + "_")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(destination))


# cost: time O(s·b), heap O(s), stack O(d), io s·f
# vars: s = 스킬 수, b = 스킬 폴더 바이트 수, f = 스킬별 파일 수, d = 폴더 깊이
# basis: estimate
def sync(root: Path, skills: list[Path], dry_run: bool) -> None:
    manifest_path = root / MANIFEST
    installed = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    current = {skill.name: tree_hash(skill) for skill in skills}
    for skill in skills:
        target = root / skill.name
        if installed.get(skill.name) == current[skill.name] and target.is_dir() and tree_hash(target) == current[skill.name]:
            continue
        print(f"{target}: 설치")
        if not dry_run:
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(skill, target, ignore=shutil.ignore_patterns(*SKIP))
    for name in sorted(set(installed) - set(current)):
        print(f"{root / name}: 원본에서 빠진 스킬, 휴지통 폴더로 이동")
        if not dry_run:
            move_to_trash(root / name)
    if not dry_run:
        manifest_path.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")


# cost: time O(s·b), heap O(s), stack O(d), io s·f
# vars: s = 스킬 수, b = 스킬 폴더 바이트 수, f = 스킬별 파일 수, d = 폴더 깊이
# basis: estimate
def build_claude_zips(source: Path, skills: list[Path], dry_run: bool) -> list[Path]:
    output = source / "dist" / "claude"
    record_path = output / MANIFEST
    record = json.loads(record_path.read_text()) if record_path.is_file() else {}
    changed = []
    for skill in skills:
        digest = tree_hash(skill)
        archive = output / f"{skill.name}.zip"
        if record.get(skill.name) == digest and archive.is_file():
            continue
        changed.append(archive)
        if dry_run:
            continue
        output.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(skill.rglob("*")):
                if path.is_file() and not SKIP.intersection(path.parts):
                    info = zipfile.ZipInfo(f"{skill.name}/{path.relative_to(skill).as_posix()}", date_time=(2020, 1, 1, 0, 0, 0))
                    info.external_attr = 0o644 << 16
                    bundle.writestr(info, path.read_bytes(), zipfile.ZIP_DEFLATED)
        record[skill.name] = digest
    if not dry_run and changed:
        record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return changed


# cost: time O(t·s·b), heap O(s), stack O(d), io t·s·f
# vars: t = 도구 수, s = 스킬 수, b = 스킬 폴더 바이트 수, f = 스킬별 파일 수, d = 폴더 깊이
# basis: estimate
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--remove", nargs="+", metavar="NAME")
    args = parser.parse_args(argv)
    roots = [TARGETS[tool] for tool, home in TOOL_HOMES.items() if home.is_dir()]
    if args.remove:
        for root in roots:
            for name in args.remove:
                if (root / name).exists():
                    print(f"{root / name}: 휴지통 폴더로 이동")
                    if not args.dry_run:
                        move_to_trash(root / name)
        return 0
    source = resolve_source(args.source)
    skills = source_skills(source)
    for root in roots:
        if not args.dry_run:
            root.mkdir(parents=True, exist_ok=True)
        sync(root, skills, args.dry_run)
    changed = build_claude_zips(source, skills, args.dry_run)
    if not args.dry_run:
        POINTER.parent.mkdir(parents=True, exist_ok=True)
        POINTER.write_text(str(source) + "\n")
    print("Claude 계정에 올릴 zip: " + (", ".join(str(path) for path in changed) if changed else "없음"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
