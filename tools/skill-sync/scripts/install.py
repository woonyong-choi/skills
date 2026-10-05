"""스킬 원본 저장소 하나를 Codex, Antigravity, Claude Code에 같은 내용으로 설치하고 Claude 계정용 zip 생성.

사용:
  python3 install.py [--source 원본 저장소]          설치된 도구 폴더에 동기화, dist/claude/*.zip 생성
  python3 install.py --dry-run                      바꿀 내용만 출력
  python3 install.py --remove 이름 [이름 ...]       도구 폴더에서 해당 스킬을 휴지통 폴더로 이동

원본 저장소 찾는 순서: --source, 환경 변수 SKILLS_SOURCE, 이 스크립트가 든 git 저장소, 마지막으로 쓴 원본(~/.config/skills/source)

인자: --target-home 대상 홈, --source 원본, --dist zip 폴더, --dry-run, --remove 이름 목록
출력: stdout 설치·zip 결과, stderr 충돌·실패, 종료 0 성공·1 실패
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import uuid
import shutil
import sys
import time
import zipfile
from pathlib import Path

INSTALL_HOME = Path.home()
TARGETS = {
    "codex": INSTALL_HOME / ".codex" / "skills",
    "antigravity": INSTALL_HOME / ".gemini" / "config" / "skills",
    "claude-code": INSTALL_HOME / ".claude" / "skills",
}
TOOL_HOMES = {"codex": INSTALL_HOME / ".codex", "antigravity": INSTALL_HOME / ".gemini", "claude-code": INSTALL_HOME / ".claude"}
MANIFEST = ".repo-skills.json"
POINTER = INSTALL_HOME / ".config" / "skills" / "source"
TRASH = INSTALL_HOME / ".skill-trash"
SKIP = {".DS_Store", ".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__"}
CATEGORIES = ("git", "code", "docs", "design", "tools")


def configure_target_home(target_home: Path) -> None:
    global INSTALL_HOME, TARGETS, TOOL_HOMES, POINTER, TRASH
    INSTALL_HOME = target_home.expanduser().resolve()
    TARGETS = {
        "codex": INSTALL_HOME / ".codex" / "skills",
        "antigravity": INSTALL_HOME / ".gemini" / "config" / "skills",
        "claude-code": INSTALL_HOME / ".claude" / "skills",
    }
    TOOL_HOMES = {tool: TARGETS[tool].parents[1] if tool == "antigravity" else TARGETS[tool].parent for tool in TARGETS}
    POINTER = INSTALL_HOME / ".config" / "skills" / "source"
    TRASH = INSTALL_HOME / ".skill-trash"


# cost: time O(k log k), heap O(k), stack O(1), io O(k)
# vars: k = 원본 폴더 항목 수
# basis: estimate
def is_skill_source(folder: Path) -> bool:
    return folder.is_dir() and bool(source_skills(folder))


# cost: time O(p + k log k), heap O(p + k), stack O(1), io O(p + k)
# vars: p = 스크립트 상위 폴더 수, k = 후보 폴더 항목 수
# basis: estimate
def resolve_source(argument: str | None) -> Path:
    if argument is not None:
        explicit = Path(argument).expanduser()
        if not is_skill_source(explicit):
            raise ValueError(f"invalid source: {explicit}")
        return explicit.resolve()
    own_repository = next(
        (parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists()),
        None,
    )
    candidates = [
        Path(argument).expanduser() if argument else None,
        Path(os.environ["SKILLS_SOURCE"]).expanduser() if os.environ.get("SKILLS_SOURCE") else None,
        own_repository,
        Path(POINTER.read_text().strip()).expanduser() if POINTER.is_file() else None,
    ]
    for candidate in candidates:
        if candidate is not None and is_skill_source(candidate):
            return candidate.resolve()
    raise SystemExit("스킬 원본 저장소를 찾지 못함: --source로 경로 지정")


# cost: time O(k log k), heap O(k), stack O(1), io O(k)
# vars: k = 원본 폴더 항목 수
# basis: estimate
def source_skills(source: Path) -> list[Path]:
    roots = [source, *(source / category for category in CATEGORIES)]
    skills = sorted(
        (path.parent for root in roots for path in root.glob("*/SKILL.md")),
        key=lambda path: path.name,
    )
    names = [skill.name for skill in skills]
    if len(names) != len(set(names)):
        raise ValueError("duplicate skill name")
    return skills


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
def move_to_trash(path: Path) -> Path | None:
    if not path.exists():
        return
    label = path.parent.relative_to(INSTALL_HOME).as_posix().replace("/", "_") if path.parent.is_relative_to(INSTALL_HOME) else "other"
    destination = TRASH / time.strftime("%Y%m%d-%H%M%S") / label / path.name
    while destination.exists():
        destination = destination.with_name(destination.name + "_")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(destination))
    return destination


def _skill_path(root: Path, name: str) -> Path:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise ValueError(f"invalid skill name: {name}")
    target = root / name
    if root.is_symlink() or target.is_symlink() or target.resolve().parent != root.resolve():
        raise ValueError(f"unsafe skill path: {target}")
    return target


# cost: time O(n), heap O(n), stack O(1), io 1
# vars: n = manifest 항목 수
# basis: estimate
def _read_manifest(root: Path) -> dict[str, str]:
    if root.is_symlink():
        raise ValueError(f"symlink target root: {root}")
    path = root / MANIFEST
    if path.is_symlink():
        raise ValueError(f"symlink manifest: {path}")
    record = json.loads(path.read_text()) if path.is_file() else {}
    if not isinstance(record, dict):
        raise ValueError(f"invalid manifest: {path}")
    for name, digest in record.items():
        _skill_path(root, name)
        if not isinstance(digest, str):
            raise ValueError(f"invalid digest: {name}")
    return record


# cost: time O(n), heap O(n), stack O(1), io 3
# vars: n = manifest 항목 수
# basis: estimate
def _write_manifest(root: Path, record: dict[str, str]) -> None:
    stage = root / (MANIFEST + "." + uuid.uuid4().hex)
    try:
        stage.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        os.replace(stage, root / MANIFEST)
    finally:
        if stage.exists():
            stage.unlink()


# cost: time O(b), heap O(f), stack O(d), io O(f)
# vars: b = 스킬 바이트 수, f = 파일 수, d = 폴더 깊이
# basis: estimate
def _replace_skill(root: Path, skill: Path, digest: str, installed: dict[str, str]) -> None:
    target = _skill_path(root, skill.name)
    if skill.is_symlink() or any(path.is_symlink() for path in skill.rglob("*")):
        raise ValueError(f"source symlink: {skill}")
    suffix = uuid.uuid4().hex
    stage = root / f".{skill.name}.stage-{suffix}"
    backup = root / f".{skill.name}.backup-{suffix}"
    try:
        shutil.copytree(skill, stage, ignore=shutil.ignore_patterns(*SKIP))
        if tree_hash(stage) != digest:
            raise ValueError(f"source changed during copy: {skill}")
        _skill_path(root, skill.name)
        if target.exists():
            target.rename(backup)
        try:
            stage.rename(target)
            _write_manifest(root, {**installed, skill.name: digest})
        except (OSError, ValueError):
            if target.exists():
                shutil.rmtree(target)
            if backup.exists():
                backup.rename(target)
            raise
        installed[skill.name] = digest
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    if backup.exists():
        shutil.rmtree(backup)


# cost: time O(n + b), heap O(n), stack O(1), io 5
# vars: n = manifest 항목 수, b = 다른 볼륨으로 옮기는 바이트 수
# basis: estimate
def _remove_skill(root: Path, name: str, installed: dict[str, str], dry_run: bool) -> None:
    target = _skill_path(root, name)
    if name not in installed:
        raise ValueError(f"unmanaged skill: {target}")
    print(f"{target}: 휴지통 폴더로 이동")
    if dry_run:
        return
    destination = move_to_trash(target)
    next_manifest = {key: value for key, value in installed.items() if key != name}
    try:
        _write_manifest(root, next_manifest)
    except OSError:
        if destination is not None:
            shutil.move(str(destination), str(target))
        raise
    installed.pop(name)


# cost: time O(s·b), heap O(s + f), stack O(d), io O(s·f)
# vars: s = 스킬 수, b = 스킬 바이트 수, f = 스킬 파일 수, d = 폴더 깊이
# basis: estimate
def sync(root: Path, skills: list[Path], dry_run: bool) -> bool:
    installed = _read_manifest(root)
    current = {skill.name: tree_hash(skill) for skill in skills}
    for name in current:
        _skill_path(root, name)
    success = True
    for skill in skills:
        target = _skill_path(root, skill.name)
        if installed.get(skill.name) == current[skill.name] and target.is_dir() and tree_hash(target) == current[skill.name]:
            print(f"{target}: 일치")
            continue
        if skill.name not in installed and target.exists():
            print(f"{target}: 충돌, 비관리 대상 보존", file=sys.stderr)
            success = False
            continue
        try:
            if not dry_run:
                _replace_skill(root, skill, current[skill.name], installed)
            print(f"{target}: {'설치 예정' if dry_run else '설치 성공'}")
        except (OSError, ValueError) as error:
            print(f"{target}: 설치 실패: {error}", file=sys.stderr)
            success = False
    for name in sorted(set(installed) - set(current)):
        try:
            _remove_skill(root, name, installed, dry_run)
        except (OSError, ValueError) as error:
            print(f"{root / name}: 제거 실패: {error}", file=sys.stderr)
            success = False
    return success


# cost: time O(f), heap O(f), stack O(1), io 1
# vars: f = zip 안 파일 수
# basis: estimate
def is_valid_archive(archive: Path, skill_name: str) -> bool:
    with zipfile.ZipFile(archive) as bundle:
        entries = bundle.infolist()
        skill_files = [item.filename for item in entries if Path(item.filename).name == "SKILL.md"]
        return skill_files == [f"{skill_name}/SKILL.md"] and not any(
            SKIP.intersection(Path(item.filename).parts) for item in entries
        )


# cost: time O(s·b + s·f log f + s·f·d), heap O(s + f + b), stack O(d), io O(s·f)
# vars: s = 스킬 수, b = 스킬 폴더 바이트 수, f = 스킬별 파일 수, d = 폴더 깊이
# basis: estimate
def build_claude_zips(source: Path, skills: list[Path], dry_run: bool, output: Path | None = None) -> list[Path]:
    output = output if output is not None else source / "dist" / "claude"
    record = _read_manifest(output)
    changed = []
    record_changed = False
    current_names = {skill.name for skill in skills}
    for name in sorted(set(record) - current_names):
        archive = output / f"{name}.zip"
        print(f"{archive}: 원본에서 빠진 스킬, 배포 zip 제거")
        if not dry_run and archive.exists():
            archive.unlink()
        record.pop(name)
        record_changed = True
    for skill in skills:
        digest = tree_hash(skill)
        archive = output / f"{skill.name}.zip"
        if archive.is_symlink():
            raise ValueError(f"symlink archive: {archive}")
        if record.get(skill.name) == digest and archive.is_file() and is_valid_archive(archive, skill.name):
            continue
        changed.append(archive)
        if dry_run:
            continue
        output.mkdir(parents=True, exist_ok=True)
        staged_archive = output / f".{skill.name}.{uuid.uuid4().hex}.zip"
        nested_skills = {path.parent for path in skill.rglob("SKILL.md") if path.is_file() and path.parent != skill}
        try:
            with zipfile.ZipFile(staged_archive, "w", zipfile.ZIP_DEFLATED) as bundle:
                for path in sorted(skill.rglob("*")):
                    if not path.is_file() or SKIP.intersection(path.parts) or nested_skills.intersection(path.parents):
                        continue
                    info = zipfile.ZipInfo(f"{skill.name}/{path.relative_to(skill).as_posix()}", date_time=(2020, 1, 1, 0, 0, 0))
                    info.external_attr = 0o644 << 16
                    bundle.writestr(info, path.read_bytes(), zipfile.ZIP_DEFLATED)
            if not is_valid_archive(staged_archive, skill.name):
                raise ValueError(f"invalid archive: {archive}: expected exactly one {skill.name}/SKILL.md and no cache files")
            os.replace(staged_archive, archive)
        finally:
            if staged_archive.exists():
                staged_archive.unlink()
        record[skill.name] = digest
        record_changed = True
    if not dry_run and record_changed:
        _write_manifest(output, record)
    return changed


# cost: time O(t·s·b + s·f log f + s·f·d), heap O(s + f + b), stack O(d), io O(t·s·f)
# vars: t = 도구 수 + 1, s = 스킬 수, b = 스킬 폴더 바이트 수, f = 스킬별 파일 수, d = 폴더 깊이
# basis: estimate
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source")
    parser.add_argument("--target-home", type=Path, help="설치 대상 홈 (기본: 현재 사용자 홈)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--dist", type=Path, help="Claude zip 출력 폴더")
    parser.add_argument("--remove", nargs="+", metavar="NAME")
    args = parser.parse_args(argv)
    if args.target_home is not None:
        configure_target_home(args.target_home)
    roots = [TARGETS[tool] for tool, home in TOOL_HOMES.items() if home.is_dir()]
    success = True
    try:
        if args.remove:
            records = [(root, _read_manifest(root)) for root in roots]
            for root, record in records:
                for name in args.remove:
                    _skill_path(root, name)
                    if name not in record:
                        raise ValueError(f"unmanaged skill: {root / name}")
            for root, record in records:
                for name in args.remove:
                    _remove_skill(root, name, record, args.dry_run)
            return 0 if roots else 1
        source = resolve_source(args.source)
        skills = source_skills(source)
        for skill in skills:
            _skill_path(skill.parent, skill.name)
            if any(path.is_symlink() for path in skill.rglob("*")):
                raise ValueError(f"source symlink: {skill}")
        for root in roots:
            if root.is_symlink():
                raise ValueError(f"symlink target root: {root}")
            if not args.dry_run:
                root.mkdir(parents=True, exist_ok=True)
            if not sync(root, skills, args.dry_run):
                success = False
        changed = build_claude_zips(source, skills, args.dry_run, args.dist)
        if not args.dry_run and success:
            POINTER.parent.mkdir(parents=True, exist_ok=True)
            POINTER.write_text(str(source) + "\n")
        print("Claude 계정에 올릴 zip: " + (", ".join(str(path) for path in changed) if changed else "없음"))
        return 0 if success else 1
    except (OSError, ValueError) as error:
        print(f"install failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
