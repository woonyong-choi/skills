"""등록 Vault의 프로젝트 연결·진입점·문서 경로를 검사한다.

인자: --project 작업 경로, 선택 --write 문서 경로 또는 --read 맥락 경로
출력: stdout JSON, 성공 0, 미등록·연결·경로 오류 2
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit


class ContextError(ValueError):
    pass


def config_directory() -> Path:
    return Path(os.environ.get("WORK_CONTINUITY_CONFIG_DIR", str(Path.home() / ".config/skills"))).expanduser().resolve()


def register_vault(path: Path) -> dict:
    import continuity
    path = path.expanduser().resolve(strict=True)
    if not path.is_dir() or not os.access(path, os.R_OK | os.W_OK | os.X_OK):
        raise ContextError("vault must be an accessible directory")
    with continuity.locked(config_directory()):
        continuity.save(config_directory() / "vault.json", {"path": str(path)})
    return {"registered": str(path)}


def resolve_vault() -> Path:
    value = os.environ.get("WOON_KNOWLEDGE_ROOT", "").strip()
    if not value:
        pointer = config_directory() / "vault.json"
        if pointer.is_file():
            value = json.loads(pointer.read_text(encoding="utf-8")).get("path", "")
    if not isinstance(value, str) or not value:
        raise ContextError(f"vault unregistered: ask the user for the Vault absolute path, then run python3 {Path(__file__).resolve()} --register-vault <path>; never guess or create one")
    path = Path(value).expanduser()
    if not path.is_absolute() or not path.is_dir():
        raise ContextError("registered vault is not an accessible absolute directory")
    return path.resolve()


def normalize_remote(value: str, base: Path | None = None) -> str:
    """원격 URL의 host/path identity. 로컬 경로·file:// 원격은 base 기준 절대 경로의 file: identity."""
    if value.startswith("file://"):
        parsed = urlsplit(value)
        if parsed.netloc not in {"", "localhost"} or not parsed.path:
            raise ContextError("unsupported remote identity")
        return "file:" + str(Path(unquote(parsed.path)).resolve())
    if value and "://" not in value and ":" not in value.split("/", 1)[0]:
        return "file:" + str(((base or Path.cwd()) / Path(value).expanduser()).resolve())
    if re.match(r"^[^/@]+@[^:]+:", value):
        value = "ssh://" + value.replace(":", "/", 1)
    parsed = urlsplit(value)
    if not parsed.hostname or not parsed.path:
        raise ContextError("unsupported remote identity")
    host = parsed.hostname.lower() + (":" + str(parsed.port) if parsed.port else "")
    return host + "/" + parsed.path.strip("/").removesuffix(".git")


# cost: time O(n), heap O(n), stack O(1), io O(4)
# vars: n = Git command output bytes
# basis: estimate
def identify_project(path: Path) -> dict:
    path = path.resolve(strict=True)
    # cost: time O(n), heap O(n), stack O(1), io O(1)
    # vars: n = command output bytes
    # basis: estimate
    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(path), *args], text=True, capture_output=True, timeout=3)
    top = git("rev-parse", "--show-toplevel")
    if top.returncode:
        return {"identity": "path:" + str(path), "path": str(path), "name": path.name}
    root = Path(top.stdout.strip()).resolve()
    remote = git("remote", "get-url", "origin")
    common = git("rev-parse", "--git-common-dir")
    if common.returncode:
        raise ContextError("cannot resolve Git common directory")
    common_path = (path / common.stdout.strip()).resolve()
    identity = normalize_remote(remote.stdout.strip(), root) if remote.returncode == 0 else "git:" + str(common_path)
    name = identity.split("/")[-1].removesuffix(".git") if remote.returncode == 0 else root.name
    return {"identity": identity, "path": str(root), "common": str(common_path), "name": name or root.name}


def read_registration(index: Path) -> dict:
    first = index.read_text(encoding="utf-8").splitlines()[0]
    prefix, suffix = "<!-- project-context: ", " -->"
    if not first.startswith(prefix) or not first.endswith(suffix):
        raise ContextError("index lacks project-context identity metadata")
    value = json.loads(first[len(prefix):-len(suffix)])
    if not isinstance(value, dict):
        raise ContextError("invalid project-context metadata")
    return value


# cost: time O(n), heap O(n), stack O(1), io O(p)
# vars: n = index bytes, p = registered projects
# basis: estimate
def resolve_project(path: Path) -> dict:
    vault = resolve_vault()
    actual = identify_project(path)
    matches = []
    for index in (vault / "worktree").glob("*/agent/index.md"):
        if not index.resolve().is_relative_to(vault):
            raise ContextError("project index escapes registered vault")
        registration = read_registration(index)
        if registration.get("identity") == actual["identity"]:
            matches.append((index, registration))
        elif actual["identity"].startswith("path:"):
            registered = registration.get("identity", "")
            if registered.startswith("path:") and path.resolve().is_relative_to(Path(registered[5:])):
                matches.append((index, registration))
    if actual["identity"].startswith("path:") and matches:
        matches.sort(key=lambda item: len(item[1]["identity"]), reverse=True)
        longest = len(matches[0][1]["identity"])
        matches = [item for item in matches if len(item[1]["identity"]) == longest]
        actual.update(identity=matches[0][1]["identity"], path=matches[0][1]["identity"][5:])
    if len(matches) != 1:
        raise ContextError("project is unregistered or has duplicate identities")
    index, registration = matches[0]
    registered_paths = registration.get("paths", [])
    same_worktree = actual.get("common") and actual["common"] == registration.get("common")
    if actual["path"] not in registered_paths and not same_worktree:
        raise ContextError("remote matches but local path is not registered")
    return {**actual, "vault": str(vault), "index": str(index), "area": str(index.parent.parent), "registration": registration}


def check_entrypoints(project: dict) -> None:
    root = Path(project["path"])
    agents, claude = root / "AGENTS.md", root / "CLAUDE.md"
    if not agents.is_file() or not claude.is_file():
        raise ContextError("missing AGENTS.md or CLAUDE.md entrypoint")
    text = agents.read_text(encoding="utf-8")
    if project["index"] not in text:
        raise ContextError("AGENTS.md does not link the registered project index")
    if claude.resolve() != agents.resolve() and claude.read_text(encoding="utf-8").strip() != "@AGENTS.md":
        raise ContextError("CLAUDE.md must link or import AGENTS.md without a duplicate body")


def check_write(project: dict, target: Path) -> None:
    target = target.resolve()
    vault, area = Path(project["vault"]), Path(project["area"])
    allowed = [area / "agent", area / "docs", vault / "legacy", vault / "inbox", vault / "publish"]
    if any(target.is_relative_to(root) for root in allowed):
        return
    extension = target.suffix.lower().lstrip(".")
    if extension and target.is_relative_to(vault / "assets" / extension):
        return
    for entry in project["registration"].get("source_document_roots", []):
        relative = Path(entry.get("path", ""))
        if relative.is_absolute() or ".." in relative.parts or not relative.name:
            raise ContextError("source document root must be project-relative")
        source = (Path(project["path"]) / relative).resolve()
        if entry.get("approval") and source.is_relative_to(Path(project["path"])) and target.is_relative_to(source):
            return
    exceptions = project["registration"].get("approved_documents", [])
    for item in exceptions:
        if not isinstance(item, dict) or not item.get("approval"):
            continue
        relative = Path(item.get("path", ""))
        if relative.is_absolute() or ".." in relative.parts or not relative.name:
            raise ContextError("approved document must be an exact project-relative path")
        root = Path(project["path"])
        if target.is_relative_to(root) and target == (root / relative).resolve():
            return
    raise ContextError("document path is outside its registered area or explicit approval")


def check_project(path: Path) -> dict:
    project = resolve_project(path)
    check_entrypoints(project)
    index = Path(project["index"])
    return {**project, "index_sha256": hashlib.sha256(index.read_bytes()).hexdigest(), "ready": True}


# cost: time O(n), heap O(n), stack O(1), io O(p)
# vars: n = index bytes, p = registered projects
# basis: estimate
def inspect_project(path: Path) -> dict:
    try:
        return check_project(path)
    except (ContextError, OSError, ValueError, IndexError, subprocess.TimeoutExpired) as error:
        return {"ready": False, "error": str(error)}


# cost: time O(n), heap O(n), stack O(1), io O(p)
# vars: n = index bytes, p = registered projects
# basis: estimate
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--register-vault", type=Path, help="persist the user-confirmed vault in the existing skills configuration directory")
    parser.add_argument("--register-project", action="store_true", help="create project entrypoints and its Vault index")
    parser.add_argument("--name", help="explicit project alias for a name collision")
    parser.add_argument("--migrate", action="store_true", help="preserve reviewed existing root instructions in the Vault before replacing entrypoints")
    parser.add_argument("--write", type=Path, help="check a document target before writing")
    parser.add_argument("--read", type=Path, help="return one selected agent document and its revision; no recursive reading")
    parser.add_argument("--task-record", type=Path, help="existing continuity checkpoint.json for a local read receipt")
    args = parser.parse_args()
    try:
        if args.register_vault:
            print(json.dumps(register_vault(args.register_vault), ensure_ascii=False))
            return 0
        if args.register_project:
            import project_registration
            print(json.dumps(project_registration.register_project(args.project, args.name, args.migrate), ensure_ascii=False))
            return 0
        result = check_project(args.project)
        if args.write:
            check_write(result, args.write)
        if args.read:
            target = args.read.resolve(strict=True)
            if not target.is_relative_to(Path(result["area"]) / "agent"):
                raise ContextError("context read must remain inside this project's agent area")
            data = target.read_bytes()
            result["read"] = {"path": str(target), "sha256": hashlib.sha256(data).hexdigest(), "text": data.decode("utf-8")}
            if args.task_record:
                import continuity
                record = args.task_record.resolve(strict=True)
                if record.name != "checkpoint.json":
                    raise ContextError("read receipt requires an existing checkpoint.json")
                binding = continuity.read(record.parent / "binding.json")
                if binding.get("repo") != result["path"]:
                    raise ContextError("read receipt task belongs to another project")
                with continuity.locked(record.parent):
                    state = continuity.read(record)
                    state.setdefault("context_reads", {})[str(target)] = result["read"]["sha256"]
                    continuity.save(record, state)
        elif args.task_record:
            raise ContextError("--task-record requires --read")
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ContextError, OSError, ValueError, IndexError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"ready": False, "error": str(error)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
