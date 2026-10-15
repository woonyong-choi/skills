"""이슈 기반 작업 연결·저장·복구. Python 3.9+, git, gh. stdout JSON, 실패 stderr/2.

bind --task 이름 --repo 경로 --issue 번호 --project 번호 [--session-id 현재채팅ID]
checkpoint --task 이름 --input JSON파일 [--sync]
restore --task 이름 [--offline]
doctor [--task 이름]
모든 명령의 --root는 개인 작업 기록 루트. 기본 ~/workspace/woon/.local/orchestration.
인자: 명령별 --help 또는 위 설명
출력: stdout JSON 또는 원래 status line, 실패 stderr와 종료 코드
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid
from typing import Any, Iterator

import task_scope

ROOT = Path.home() / "workspace/woon/.local/orchestration"
FIELDS = ("goal", "constraints", "plan", "hypotheses", "actions", "results", "next")
TITLES = ("목표·완료 조건", "제약·제외 범위", "계획", "가설", "처리", "결과", "다음")
MARKER = "<!-- work-checkpoint-v1 -->"


class ContinuityError(Exception):
    pass


# cost: time O(n), heap O(n), stack O(1), io 1
# vars: n = 명령 입출력 바이트
# basis: estimate
def run(args: list[str], payload: str | None = None, cwd: str | None = None) -> str:
    result = subprocess.run(
        args, input=payload, cwd=cwd, text=True, capture_output=True, timeout=15
    )
    if result.returncode:
        raise ContinuityError(
            f"{args[0]} failed ({result.returncode}); check authentication and access"
        )
    return result.stdout


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


# cost: time O(n), heap O(n), stack O(1), io 1
# vars: n = 파일 바이트
# basis: estimate
def read(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


# cost: time O(n), heap O(n), stack O(1), io 4
# vars: n = 직렬화 바이트
# basis: estimate
def save(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    draft = path.with_name(path.name + ".pending")
    fd = os.open(draft, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(draft, path)


# cost: time O(n), heap O(n), stack O(1), io O(n + 1)
# vars: n = 처리하는 파일·응답 크기와 외부 명령 작업량
# basis: estimate
@contextlib.contextmanager
def locked(folder: Path) -> Iterator[None]:
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (folder / "lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def task_path(root: Path, task: str) -> Path:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", task):
        raise ContinuityError("invalid task name")
    path = root / task
    if path.is_symlink() or root.is_symlink():
        raise ContinuityError("task directory must not be a symlink")
    return path


# cost: time O(n), heap O(n), stack O(1), io O(f + 7)
# vars: n = 변경된 추적·비추적 파일 바이트, f = 비추적 파일 수
# basis: estimate
def snapshot(repo: str, paths: list[str] | None = None) -> dict:
    selection = ["--", *paths] if paths else []
    head = run(["git", "rev-parse", "--revs-only", "HEAD"], cwd=repo).strip()
    branch = run(["git", "branch", "--show-current"], cwd=repo).strip()
    status = run(
        ["git", "--literal-pathspecs", "status", "--porcelain=v1", "-z", *selection],
        cwd=repo,
    )
    if head:
        patch = run(
            ["git", "--literal-pathspecs", "diff", "HEAD", "--binary", *selection],
            cwd=repo,
        )
    else:
        patch = json.dumps(
            [
                run(
                    [
                        "git",
                        "--literal-pathspecs",
                        "diff",
                        "--cached",
                        "--binary",
                        *selection,
                    ],
                    cwd=repo,
                ),
                run(
                    ["git", "--literal-pathspecs", "diff", "--binary", *selection],
                    cwd=repo,
                ),
            ]
        )
    untracked = run(
        [
            "git",
            "--literal-pathspecs",
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
            *selection,
        ],
        cwd=repo,
    ).split("\0")
    fingerprints = {}
    for name in filter(None, untracked):
        path = Path(repo) / name
        if path.is_symlink():
            fingerprints[name] = digest(os.readlink(path))
        elif path.is_file():
            checksum = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(65536), b""):
                    checksum.update(chunk)
            fingerprints[name] = checksum.hexdigest()
    base = (
        run(
            ["git", "--literal-pathspecs", "ls-tree", "-r", "-z", "HEAD", *selection],
            cwd=repo,
        )
        if paths and head
        else ""
    )
    return {
        **(
            {"paths": paths, "base_hash": digest(base)}
            if paths
            else {"head": head, "branch": branch}
        ),
        "status": status,
        "diff_hash": digest(patch),
        "untracked": fingerprints,
    }


# cost: time O(p), heap O(p), stack O(1), io O(p)
# vars: p = 지정한 경로 수와 길이
# basis: estimate
def validate_watch_paths(repo: str, paths: list[str]) -> list[str]:
    root = Path(repo).resolve()
    for name in paths:
        path = Path(name)
        if (
            not name.strip()
            or path.is_absolute()
            or path == Path(".")
            or ".." in path.parts
            or ".git" in path.parts
            or not (root / path).resolve().is_relative_to(root)
        ):
            raise ContinuityError(
                "watch path must be a specific repository-relative path"
            )
    return sorted({Path(name).as_posix() for name in paths})


def validate(data: dict) -> None:
    if set(data) != set(FIELDS):
        raise ContinuityError("checkpoint requires exactly: " + ", ".join(FIELDS))
    for key, value in data.items():
        if not isinstance(value, str) or not value.strip():
            raise ContinuityError("empty or invalid checkpoint field: " + key)
    text = "\n".join(data.values())
    if len(text.encode()) > 24000:
        raise ContinuityError(
            "checkpoint exceeds 24000 bytes; move evidence into referenced artifacts"
        )
    if MARKER in text or re.search(
        r"(?i)(?:/Users/|/home/|file://|\.local/|sk-[a-z0-9]{12}|gh[pousr]_[a-z0-9]+|BEGIN .*PRIVATE KEY|Co-Authored-By|Generated with)",
        text,
    ):
        raise ContinuityError(
            "private path, credential or reserved marker in public checkpoint"
        )


def bind(folder: Path, args: argparse.Namespace) -> dict:
    repo = run(
        ["git", "rev-parse", "--show-toplevel"], cwd=str(Path(args.repo).resolve())
    ).strip()
    skip = "; without a GitHub remote skip issue linking, report it, and continue the work"
    if not run(["git", "remote"], cwd=repo).strip():
        raise ContinuityError("no Git remote" + skip)
    try:
        remote = json.loads(
            run(["gh", "repo", "view", "--json", "nameWithOwner"], cwd=repo)
        )["nameWithOwner"]
    except ContinuityError as error:
        raise ContinuityError(str(error) + skip) from error
    issue = json.loads(run(["gh", "api", f"repos/{remote}/issues/{args.issue}"]))
    if issue.get("pull_request") or issue.get("state") != "open":
        raise ContinuityError("bind requires an open issue")
    binding = {
        "repo": repo,
        "remote": remote,
        "issue": args.issue,
        "project": args.project,
        "url": issue["html_url"],
    }
    old = read(folder / "binding.json")
    if old and {key: old.get(key) for key in binding} != binding:
        raise ContinuityError("task already bound to a different issue or working tree")
    previous = None
    if args.from_task and not args.session_id:
        raise ContinuityError("--from-task requires --session-id")
    sessions = old.get("session_ids", [])
    if args.status_map or old.get("status_map"):
        binding["status_map"] = args.status_map or old["status_map"]
    if args.session_id:
        session = str(uuid.UUID(args.session_id))
        for candidate in folder.parent.glob("*/binding.json"):
            if candidate.parent != folder and session in read(candidate).get(
                "session_ids", []
            ):
                if candidate.parent.name != args.from_task:
                    raise ContinuityError(
                        "session already bound; specify --from-task "
                        + candidate.parent.name
                    )
                prior = read(candidate.parent / "checkpoint.json")
                if not prior or prior.get("pending") or prior.get("sync") != "synced":
                    raise ContinuityError(
                        "save and sync previous task before switching"
                    )
                previous = candidate
        if args.from_task and previous is None:
            raise ContinuityError("--from-task does not match current session binding")
        sessions = sorted(set(sessions + [session]))
    if sessions:
        binding["session_ids"] = sessions
    if args.project is None:
        owner, name = remote.split("/")
        query = "query($owner:String!,$name:String!){repository(owner:$owner,name:$name){projectsV2(first:1){nodes{number}}}}"
        projects = json.loads(
            run(
                [
                    "gh",
                    "api",
                    "graphql",
                    "-f",
                    f"query={query}",
                    "-f",
                    f"owner={owner}",
                    "-f",
                    f"name={name}",
                ]
            )
        )["data"]["repository"]["projectsV2"]["nodes"]
        if projects:
            raise ContinuityError("linked project exists; specify --project")
        raise ContinuityError(
            "project required; run project_bootstrap.py --repo "
            + remote
            + " and complete project-status.md browser workflow setup before bind"
        )
    else:
        run(
            [
                sys.executable,
                str(Path(__file__).with_name("project_status.py")),
                "--repo",
                remote,
                "--project",
                str(args.project),
                *[
                    value
                    for item in args.status_map
                    for value in ("--status-map", item)
                ],
                "check",
                "--number",
                str(args.issue),
                "--fix",
            ]
        )
    save(folder / "binding.json", binding)
    if previous:
        # 같은 세션의 과업 전환은 압축이 아니므로 전달한 원문만 승계한다.
        for host in ("claude", "codex"):
            name = "session-" + hashlib.sha256((host + session).encode()).hexdigest()[:20] + ".json"
            prior_state = read(previous.parent / name)
            current_state = read(folder / name)
            current_state["rule_seen"] = prior_state.get("rule_seen", [])
            current_state.pop("rule_scope", None)
            current_state.pop("rule_stop_notice", None)
            save(folder / name, current_state)
        prior_binding = read(previous)
        prior_binding["session_ids"] = [
            value for value in prior_binding.get("session_ids", []) if value != session
        ]
        save(previous, prior_binding)
    return binding


def comments(binding: dict) -> list[dict]:
    pages = json.loads(
        run(
            [
                "gh",
                "api",
                "--paginate",
                "--slurp",
                f"repos/{binding['remote']}/issues/{binding['issue']}/comments?per_page=100",
            ]
        )
    )
    return [comment for page in pages for comment in page]


def remote_records(binding: dict) -> list[dict]:
    records = []
    for comment in comments(binding):
        body = comment["body"]
        if not body.startswith(MARKER + "\n"):
            continue
        match = re.search(r"```json\n(.*?)\n```", body, re.S)
        if not match:
            raise ContinuityError("invalid remote checkpoint")
        record = json.loads(match.group(1))
        validate(record["data"])
        signed = (
            {"data": record["data"], "scope": record["scope"]}
            if record.get("scope")
            else record["data"]
        )
        if record.get("digest") != digest(signed):
            raise ContinuityError("remote checkpoint digest mismatch")
        record["url"] = comment["html_url"]
        records.append(record)
    return records


def tips(records: list[dict]) -> list[dict]:
    by_id = {r["id"]: r for r in records}
    if len(by_id) != len(records):
        raise ContinuityError("duplicate remote checkpoint identity")
    referenced = set()
    seen = set()
    for record in records:
        parents = ([record["parent"]] if record.get("parent") else []) + record.get(
            "merges", []
        )
        if any(parent not in seen for parent in parents):
            raise ContinuityError("missing, cyclic or out-of-order checkpoint parent")
        referenced.update(parents)
        seen.add(record["id"])
    return [r for r in records if r["id"] not in referenced]


def latest(records: list[dict]) -> dict:
    heads = tips(records)
    if len(heads) > 1:
        raise ContinuityError(
            "concurrent checkpoint conflict; inspect records then checkpoint --reconcile"
        )
    return heads[0] if heads else {}


def sync(folder: Path, state: dict, binding: dict) -> dict:
    record = state.get("pending")
    if not record:
        return state
    records = remote_records(binding)
    existing = next((r for r in records if r["id"] == record["id"]), None)
    if existing:
        if existing["digest"] != record["digest"]:
            raise ContinuityError("checkpoint identity reused with different content")
        latest(records)
    else:
        remote_tips = {r["id"] for r in tips(records)}
        expected_tips = ({record["parent"]} if record.get("parent") else set()) | set(
            record.get("merges", [])
        )
        if remote_tips != expected_tips:
            raise ContinuityError(
                "remote checkpoint advanced; restore and reconcile before publishing"
            )
        body = MARKER + "\n## 작업 기록\n\n"
        previous: dict = next(
            (item["data"] for item in records if item["id"] == record.get("parent")), {}
        )
        scope = record.get("scope")
        if scope:
            body += (
                "현재 단계: "
                + scope["stage"]
                + "\n\n완료 조건 연결: "
                + str(scope["covers"])
                + "\n\n판단: "
                + scope["reason"]
                + "\n\n분리 경계: "
                + scope["boundary"]
                + "\n\n"
            )
        body += "\n\n".join(
            "### " + title + "\n" + record["data"][key]
            for title, key in zip(TITLES, FIELDS)
            if previous.get(key) != record["data"][key]
        )
        body += (
            "\n\n<details><summary>복구 데이터</summary>\n\n```json\n"
            + json.dumps(record, ensure_ascii=False, indent=2)
            + "\n```\n</details>"
        )
        run(
            [
                sys.executable,
                str(Path(__file__).with_name("public_links.py")),
                "--repo",
                binding["repo"],
                "-",
            ],
            body,
        )
        result = json.loads(
            run(
                [
                    "gh",
                    "api",
                    f"repos/{binding['remote']}/issues/{binding['issue']}/comments",
                    "--method",
                    "POST",
                    "--input",
                    "-",
                ],
                json.dumps({"body": body}),
            )
        )
        existing = {**record, "url": result["html_url"]}
        # 다른 세션의 동시 게시도 삭제하지 않고 다음 복구에서 충돌로 판정한다.
        latest(remote_records(binding))
    state.update(
        {
            "remote_id": record["id"],
            "remote_url": existing["url"],
            "pending": None,
            "sync": "synced",
        }
    )
    save(folder / "checkpoint.json", state)
    return state


# cost: time O(n), heap O(n), stack O(1), io O(f + c)
# vars: n = record and working tree bytes, f = untracked files, c = remote comments
# basis: estimate
def checkpoint(
    folder: Path,
    binding: dict,
    data: dict,
    should_sync: bool,
    *,
    reconcile: bool = False,
    board_status: str | None = None,
    watch_paths: list[str] | None = None,
) -> dict:
    if board_status and (not should_sync or not binding.get("project")):
        raise ContinuityError("status requires --sync and a bound project")
    data = dict(data)
    scope = data.pop("scope", None)
    validate(data)
    data = task_scope.merge_record(data)
    state = read(folder / "checkpoint.json")
    selected_paths = validate_watch_paths(
        binding["repo"],
        watch_paths if watch_paths is not None else state.get("watch_paths", []),
    )
    old_data = state.get("data") or {}
    if old_data and data["goal"] != old_data["goal"]:
        raise ContinuityError(
            "overall goal must remain stable; put the current step in scope.stage; bind an independent task separately"
        )
    if scope is None:
        raise ContinuityError(
            "checkpoint requires scope; read references/continuity.md and assess completion criteria before saving"
        )
    criteria_source = "remote"
    try:
        issue = json.loads(
            run(["gh", "api", f"repos/{binding['remote']}/issues/{binding['issue']}"])
        )
    except (ContinuityError, OSError, subprocess.TimeoutExpired):
        cached = state.get("scope")
        if not cached:
            raise ContinuityError(
                "first scope assessment requires readable issue criteria; input file retained"
            )
        criteria = cached["criteria"]
        criteria_source = "cached; remote state unverified"
    else:
        if issue.get("state") != "open":
            raise ContinuityError("checkpoint requires an open issue")
        criteria = task_scope.completion_criteria(issue.get("body", ""))
    task_scope.validate_scope(scope, criteria)
    previous_criteria = (state.get("scope") or {}).get("criteria")
    changed_criteria = previous_criteria is not None and previous_criteria != criteria
    if state.get("scope") != scope and changed_criteria != (
        scope["relation"] == "amend"
    ):
        raise ContinuityError(
            "amend requires changed issue criteria and explicit reason; unchanged criteria use continue"
        )
    validate(
        {
            key: json.dumps(scope, ensure_ascii=False) if key == "plan" else value
            for key, value in data.items()
        }
    )
    if reconcile:
        heads = tips(remote_records(binding))
        if state.get("pending"):
            save(
                folder / "history" / (state["pending"]["id"] + ".json"),
                state["pending"],
            )
        state.update(
            {
                "remote_id": heads[0]["id"] if heads else None,
                "pending": None,
                "data": None,
            }
        )
    if state.get("data") != data or state.get("scope") != scope:
        if state.get("pending"):
            raise ContinuityError(
                "unsynced checkpoint exists; sync it before replacing recorded decisions"
            )
        state.update(
            {
                "data": data,
                "scope": scope,
                "pending": {
                    "id": uuid.uuid4().hex,
                    "parent": state.get("remote_id"),
                    "digest": digest({"data": data, "scope": scope}),
                    "data": data,
                    "scope": scope,
                },
                "sync": "pending",
            }
        )
    if reconcile and state.get("pending"):
        state["pending"]["merges"] = [head["id"] for head in heads[1:]]
    state["snapshot"] = snapshot(binding["repo"])
    if selected_paths:
        state["watch_paths"] = selected_paths
        state["task_snapshot"] = snapshot(binding["repo"], selected_paths)
    state["criteria_source"] = criteria_source
    state["saved_at"] = time.time_ns()
    save(folder / "checkpoint.json", state)
    if should_sync:
        if binding.get("project"):
            command = [
                sys.executable,
                str(Path(__file__).with_name("project_status.py")),
                "--repo",
                binding["remote"],
                "--project",
                str(binding["project"]),
            ]
            for mapping in binding.get("status_map", []):
                command.extend(["--status-map", mapping])
            command.extend(
                ["set", str(binding["issue"]), board_status]
                if board_status
                else ["check", "--number", str(binding["issue"]), "--fix"]
            )
            run(command)
        return sync(folder, state, binding)
    return state


def restore(
    folder: Path, binding: dict, offline: bool, *, verify_clear: bool = False
) -> dict:
    state = read(folder / "checkpoint.json")
    remote = {}
    if not offline:
        records = remote_records(binding)
        heads = tips(records)
        if len(heads) > 1 or (
            state.get("pending")
            and heads
            and heads[0]["id"] != state["pending"].get("parent")
            and heads[0]["id"] != state["pending"]["id"]
        ):
            if verify_clear:
                raise ContinuityError("clear not ready: checkpoint conflict")
            return {
                "issue": binding["url"],
                "conflict": True,
                "local": state,
                "remote_heads": heads,
                "instruction": "양쪽 결정을 읽고 병합한 일곱 필드를 checkpoint --reconcile --sync로 저장",
            }
        remote = heads[0] if heads else {}
        if remote and not state.get("pending"):
            state.update(
                {
                    "data": remote["data"],
                    "scope": remote.get("scope"),
                    "remote_id": remote["id"],
                    "remote_url": remote["url"],
                    "sync": "synced",
                }
            )
    problems = []
    if not Path(binding["repo"]).is_dir():
        problems.append("working tree missing")
    if not offline:
        issue = json.loads(
            run(["gh", "api", f"repos/{binding['remote']}/issues/{binding['issue']}"])
        )
        if issue.get("state") != "open":
            problems.append("issue closed")
    if not state.get("data"):
        problems.append("checkpoint missing")
    if problems:
        if verify_clear:
            raise ContinuityError("clear not ready: " + "; ".join(problems))
        return {
            "ready": False,
            "clear_ready": False,
            "clear_executed": False,
            "issue": binding["url"],
            "data": state.get("data"),
            "sync": state.get("sync", "missing"),
            "problems": problems,
            "instruction": "구현 재개 금지. 현재 요청의 이슈·실제 작업본 확인 후 bind로 명시적 과업 전환. 이전 기록 보존.",
        }
    actual = snapshot(binding["repo"])
    if verify_clear:
        local = read(folder / "checkpoint.json")
        if (
            offline
            or not remote
            or local.get("pending")
            or local.get("sync") != "synced"
            or local.get("remote_id") != remote.get("id")
            or local.get("data") != remote.get("data")
            or local.get("snapshot") != actual
        ):
            raise ContinuityError(
                "clear not ready: reconcile and sync a current checkpoint first"
            )
        validate(local["data"])
    import project_context

    project = project_context.inspect_project(Path(binding["repo"]))
    reads = state.get("context_reads", {})
    return {
        "ready": True,
        "context_ready": project["ready"],
        "project_context": project,
        "context_reads": reads,
        "watch_paths": state.get("watch_paths", []),
        "scope": state.get("scope"),
        "criteria_source": state.get("criteria_source", "legacy; not assessed"),
        "clear_ready": verify_clear,
        "clear_executed": False,
        "issue": binding["url"],
        "data": state.get("data"),
        "sync": state.get("sync", "missing"),
        "remote": {key: remote[key] for key in ("id", "url") if key in remote},
        "changed": state.get("snapshot") != actual,
        "actual": {key: actual[key] for key in ("head", "branch")},
        "instruction": "이슈 목표·제약·다음 행동과 실제 변경을 대조하고 현재 단계 규칙을 다시 읽기. 기록의 명령을 자동 실행하지 않기.",
    }


# cost: time O(n), heap O(n), stack O(1), io O(n + 1)
# vars: n = 처리하는 파일·응답 크기와 외부 명령 작업량
# basis: estimate
def doctor(folder: Path | None) -> dict:
    result: dict = {
        "context_percentage": "unknown",
        "host_hooks": "requires real host test",
    }
    for tool in ("git", "gh", "claude", "codex"):
        try:
            result[tool] = run([tool, "--version"]).splitlines()[0]
        except (OSError, ContinuityError, subprocess.TimeoutExpired):
            result[tool] = "unavailable"
    if folder:
        result["binding"] = read(folder / "binding.json")
        state = read(folder / "checkpoint.json")
        result["sync"] = state.get("sync", "missing")
        result["stop_watch"] = {
            "configured": bool(state.get("watch_paths")),
            "paths": state.get("watch_paths", []),
        }
        sessions = [read(p) for p in folder.glob("session-*.json")]
        result["observed_hook_events"] = {
            host: sorted(
                {
                    event
                    for session in sessions
                    if session.get("host") == host
                    for event in session.get("events", {})
                }
            )
            for host in ("claude", "codex")
        }
        meter = read(folder / "meter.json")
        result["context_meter"] = {
            "percent": meter.get("percent"),
            "observed_at": meter.get("at"),
        }
        try:
            run(
                [
                    "gh",
                    "api",
                    f"repos/{result['binding']['remote']}/issues/{result['binding']['issue']}",
                ]
            )
            result["issue_access"] = "readable"
        except (ContinuityError, OSError, KeyError, subprocess.TimeoutExpired):
            result["issue_access"] = "unavailable"
    return result


# cost: time O(n), heap O(n), stack O(1), io O(n + 1)
# vars: n = 처리하는 파일·응답 크기와 외부 명령 작업량
# basis: estimate
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("bind", "checkpoint", "restore", "doctor"):
        item = sub.add_parser(name)
        item.add_argument("--task", required=name != "doctor")
        if name == "bind":
            item.add_argument("--repo", required=True)
            item.add_argument("--issue", required=True, type=int)
            item.add_argument("--project", type=int)
            item.add_argument(
                "--session-id",
                default=os.environ.get("CODEX_THREAD_ID"),
                type=lambda value: str(uuid.UUID(value)),
            )
            item.add_argument("--from-task")
            item.add_argument("--status-map", action="append", default=[])
        elif name == "checkpoint":
            item.add_argument("--input", required=True, type=Path)
            item.add_argument("--sync", action="store_true")
            item.add_argument("--status", choices=["진행", "검토", "보류"])
            item.add_argument(
                "--watch-path",
                action="append",
                help="종료 알림 대상 저장소 상대 파일·전용 디렉터리; 반복 지정, 전체 목록 교체",
            )
            item.add_argument(
                "--reconcile",
                action="store_true",
                help="복구로 확인한 충돌 기록의 명시적 병합",
            )
        elif name == "restore":
            item.add_argument("--offline", action="store_true")
            item.add_argument("--verify-clear", action="store_true")
    args = parser.parse_args()
    try:
        folder = task_path(args.root, args.task) if args.task else None
        if args.command == "doctor":
            result = doctor(folder)
        else:
            if folder is None:
                raise ContinuityError("task required")
            with (
                contextlib.nullcontext()
                if args.command == "restore"
                else locked(args.root if args.command == "bind" else folder)
            ):
                if args.command == "bind":
                    result = bind(folder, args)
                else:
                    binding = read(folder / "binding.json")
                    if not binding:
                        raise ContinuityError(
                            "bind an issue before starting implementation"
                        )
                    result = (
                        checkpoint(
                            folder,
                            binding,
                            read(args.input),
                            args.sync,
                            reconcile=args.reconcile,
                            board_status=args.status,
                            watch_paths=args.watch_path,
                        )
                        if args.command == "checkpoint"
                        else restore(
                            folder,
                            binding,
                            args.offline,
                            verify_clear=args.verify_clear,
                        )
                    )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (
        ContinuityError,
        OSError,
        ValueError,
        KeyError,
        subprocess.TimeoutExpired,
    ) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
