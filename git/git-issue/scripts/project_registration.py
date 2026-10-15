"""명시적으로 요청한 프로젝트의 Vault 진입점을 보존하며 등록한다."""

from __future__ import annotations

import json
from pathlib import Path
import re

import continuity
import project_context as context


def slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9.-]+", "-", value.lower()).strip("-.")
    if not value:
        raise context.ContextError("project needs an explicit nonempty name")
    return value


def select_index(vault: Path, actual: dict, name: str | None) -> Path:
    matches = [p for p in (vault / "worktree").glob("*/agent/index.md") if context.read_registration(p).get("identity") == actual["identity"]]
    if len(matches) > 1:
        raise context.ContextError("duplicate project identities require reconciliation")
    if matches:
        return matches[0]
    label = slug(name or actual["name"])
    area = vault / "worktree" / label
    if area.exists() and not name:
        owner = actual["identity"].split("/")[-2]
        area = vault / "worktree" / slug(owner + "-" + actual["name"])
    if area.exists():
        raise context.ContextError("project name collision: specify a distinct --name")
    return area / "agent/index.md"


def bootstrap(index: Path) -> str:
    return ("# Project context\n\n<!-- project-context-bootstrap -->\n"
            f"작업 전 `{index}`를 반드시 읽는다. 필요한 규칙과 자료만 선택하여 읽는다.\n"
            "연결 실패를 읽음으로 처리하지 않는다. 지침·맥락·신규 작업 문서는 등록 Vault의 지정 영역에서만 관리한다.\n"
            "사용자의 명시적 요청·승인 없이 프로젝트에 추가 문서나 맥락 사본을 만들지 않는다. 코드·실행 필수 설정과 승인 문서는 보존한다.\n")


def prepare_migration(root: Path, index: Path, migrate: bool) -> dict[Path, str]:
    writes = {}
    agents, claude = root / "AGENTS.md", root / "CLAUDE.md"
    for source, label in [(agents, "project"), (claude, "claude")]:
        if source.is_symlink():
            if source == claude and source.resolve() == agents.resolve():
                continue
            raise context.ContextError("external entrypoint symlink requires manual scope review")
        if not source.exists():
            continue
        text = source.read_text(encoding="utf-8")
        if source == claude and agents.is_file() and text == agents.read_text(encoding="utf-8"):
            continue
        if text == bootstrap(index) or (source == claude and text.strip() == "@AGENTS.md"):
            continue
        if not migrate:
            raise context.ContextError("existing instructions: review scope and rerun with --migrate")
        target = index.parent / (label + ".md")
        migrated = f"<!-- original-scope: {root}; relative paths and commands retain this base -->\n" + text
        if target.exists():
            canonical = target.read_text(encoding="utf-8")
            if canonical == migrated or same_worktree_instructions(root, index, canonical, text):
                continue
            raise context.ContextError("existing canonical instructions differ; reconcile without overwriting")
        writes[target] = migrated
    return writes


# cost: time O(n), heap O(n), stack O(1), io O(1)
# vars: n = instruction and registration bytes
# basis: estimate
def same_worktree_instructions(root: Path, index: Path, canonical: str, text: str) -> bool:
    header, separator, body = canonical.partition("\n")
    if not separator or body != text:
        return False
    if not re.fullmatch(r"<!-- original-scope: /[^\r\n;]+; relative paths and commands retain this base -->", header):
        return False
    actual = context.identify_project(root)
    registered = context.read_registration(index)
    return (
        registered.get("identity") == actual["identity"]
        and bool(actual.get("common"))
        and registered.get("common") == actual["common"]
    )


# cost: time O(n), heap O(n), stack O(1), io O(p)
# vars: n = instructions and indexes bytes, p = registered projects
# basis: estimate
def register_project(path: Path, name: str | None, migrate: bool) -> dict:
    vault, actual = context.resolve_vault(), context.identify_project(path)
    with continuity.locked(context.config_directory()):
        index = select_index(vault, actual, name)
        if not index.resolve().is_relative_to(vault):
            raise context.ContextError("project area escapes vault")
        root = Path(actual["path"])
        existing = context.read_registration(index) if index.exists() else {}
        # 같은 원격의 다른 clone: 저장된 common 유지, 경로만 추가. 등록된 경로의 common 변경은 조정 필요.
        other_clone = existing.get("common") and existing["common"] != actual.get("common")
        if other_clone and actual["path"] in existing.get("paths", []):
            raise context.ContextError("registered Git common differs; reconcile without overwriting")
        writes = prepare_migration(root, index, migrate)
        registration = existing or {"identity": actual["identity"], "paths": []}
        registration["paths"] = sorted(set(registration.get("paths", []) + [actual["path"]]))
        if actual.get("common") and not other_clone:
            registration["common"] = actual["common"]
        body = "\n".join(index.read_text(encoding="utf-8").splitlines()[1:]) + "\n" if index.exists() else "# Project context\n\n- 필수: 적용 범위에 해당하는 상위 지침. 현재 과업에 필요한 자료만 조회, 전체 agent 재귀 읽기 금지\n- 진행·결정·검사·다음 행동: 기존 Continuity 기록 재사용, 별도 상태 사본 금지\n"
        for target, text in writes.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            link = f"- {'Claude에서 추가 적용' if target.stem == 'claude' else '필수 프로젝트 지침'}: [{target.stem}]({target.name})\n"
            if link not in body:
                body += link
        index.parent.mkdir(parents=True, exist_ok=True)
        index.write_text("<!-- project-context: " + json.dumps(registration, ensure_ascii=False) + " -->\n" + body, encoding="utf-8")
        agents = root / "AGENTS.md"
        agents.write_text(bootstrap(index), encoding="utf-8")
        claude = root / "CLAUDE.md"
        if not claude.is_symlink():
            claude.write_text("@AGENTS.md\n", encoding="utf-8")
    return context.check_project(root)
