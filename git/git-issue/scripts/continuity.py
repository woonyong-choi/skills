"""이슈 기반 작업 연결·저장·복구. Python 3.9+, git, gh. stdout JSON, 실패 stderr/2.

bind --task 이름 --repo 경로 --issue 번호 --project 번호 [--session-id 현재채팅ID]
checkpoint --task 이름 --input JSON파일 [--sync]
restore --task 이름 [--offline] [--verify-clear]
doctor [--task 이름]
cache-report --transcript 호스트 JSONL [--host claude|codex]
모든 명령의 --root는 개인 작업 기록 루트. 기본 ISSUE_CONTINUITY_ROOT, 없으면 등록 Vault의 legacy/orchestration.
인자: 명령별 --help 또는 위 설명
출력: stdout JSON 또는 원래 status line, 실패 stderr와 종료 코드
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import shutil
import time
import uuid
from typing import Any, Callable, Iterator, NamedTuple

import project_context
import task_scope

# 이전 기본 위치. Vault로 한 번 옮기는 데만 사용
LEGACY_ROOT = Path.home() / "workspace/woon/.local/orchestration"
ROOT_ENV = "ISSUE_CONTINUITY_ROOT"
FIELDS = ("goal", "constraints", "plan", "hypotheses", "actions", "results", "next")
TITLES = ("목표·완료 조건", "제약·제외 범위", "계획", "가설", "처리", "결과", "다음")
MARKER = "<!-- work-checkpoint-v1 -->"
# 비공개 대화 원문: 작업 기록 폴더의 exchange.json에만 저장, 원격 게시 없음
EXCHANGE = "exchange.json"
ORIGINAL_LIMIT = 8000
TURN_LIMIT = 4000
TRANSCRIPT_TAIL_BYTES = 4 << 20
SPIKE_MIN_TOKENS = 1024


class ContinuityError(Exception):
    pass


def default_root() -> Path:
    """작업 기록 루트 정본: ISSUE_CONTINUITY_ROOT, 없으면 등록 Vault의 legacy/orchestration. CLI·훅·status line 공통.
    이전 기본 위치에 기록이 있고 Vault 쪽이 비었으면 한 번 옮김. Vault 미등록이면 ContinuityError"""
    configured = os.environ.get(ROOT_ENV)
    if configured:
        return Path(configured).expanduser()
    try:
        root = project_context.resolve_vault() / "legacy" / "orchestration"
    except project_context.ContextError as error:
        raise ContinuityError(f"작업 기록 위치 없음: {error}") from error
    if not root.exists() and LEGACY_ROOT.is_dir():
        root.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(LEGACY_ROOT), str(root))
    return root


# cost: time O(n), heap O(n), stack O(1), io 1
# vars: n = 명령 입출력 바이트
# basis: estimate
def run(args: list[str], payload: str | None = None, cwd: str | None = None) -> str:
    result = subprocess.run(
        args, input=payload, cwd=cwd, text=True, capture_output=True, timeout=project_context.time_budget(15)
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
    # 쓰기 성공 신호 대신 실제 파일을 다시 읽어 대조한다.
    if read(path) != json.loads(json.dumps(value, ensure_ascii=False)):
        raise ContinuityError("saved state differs on read-back: " + path.name)


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
        for host in HOSTS:
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


def signature(data: dict, scope: dict | None) -> str:
    """원격 기록 digest와 같은 규칙의 서명. scope 없는 옛 기록은 data만."""
    return digest({"data": data, "scope": scope} if scope else data)


# cost: time O(n), heap O(n), stack O(1), io 1
# vars: n = checkpoint.json 바이트와 원격 기록 수
# basis: estimate
def verify_checkpoint(
    folder: Path,
    records: list[dict] | None = None,
    *,
    synced: bool = False,
    since: int | None = None,
) -> dict:
    """저장 주장 대신 실제 checkpoint.json(records가 있으면 원격 기록)을 다시 읽어 대조. 불일치는 ContinuityError"""
    state = read(folder / "checkpoint.json")
    if not state.get("data"):
        raise ContinuityError("checkpoint not persisted")
    validate(state["data"])
    signed = signature(state["data"], state.get("scope"))
    pending = state.get("pending")
    if pending and pending.get("digest") != signed:
        raise ContinuityError("local checkpoint differs from its pending record")
    if since is not None and state.get("saved_at", 0) < since:
        raise ContinuityError("no checkpoint saved during this request")
    if synced and state.get("sync") == "local":
        return {"local": "verified", "remote": "local only", "digest": signed}
    if synced and (pending or state.get("sync") != "synced"):
        raise ContinuityError("checkpoint not synced; local pending kept")
    if synced and state.get("remote_verified") not in (None, signed):
        raise ContinuityError("synced checkpoint differs from read-back remote record")
    remote = "pending" if pending else "not checked"
    if records is not None and not pending:
        found = next((r for r in records if r["id"] == state.get("remote_id")), None)
        if not found or found["digest"] != signed:
            raise ContinuityError("remote checkpoint missing or different on read-back")
        remote = "verified"
    return {"local": "verified", "remote": remote, "digest": signed}


COMMENT_LIMIT = 600  # 체크포인트 댓글의 보이는 요약 상한(글자)
PUBLISH_EVENTS = ("결정", "인계")


def comment_summary(record: dict, board_status: str | None = None) -> str:
    """보이는 개조식 요약. 전체 상태는 접힌 복구 JSON에만. COMMENT_LIMIT 넘으면 항목을 줄여 맞춤"""
    data, scope = record["data"], record.get("scope") or {}
    covers = ", ".join(str(item) for item in scope.get("covers", [])) or "없음"
    head = f"단계: {' '.join(str(scope.get('stage', '미기재')).split())} (완료 조건 {covers})\n\n"
    blocked = "보류, 사유·재개 조건은 다음 항목" if board_status == "보류" else "없음"
    rows = [("한 일", data["actions"]), ("결과", data["results"]), ("다음", data["next"]), ("막힌 것", blocked)]
    rows = [(label, " ".join(value.split())) for label, value in rows]
    limit = COMMENT_LIMIT - len(MARKER) - 2 - len(head) - sum(len(f"- {label}: \n") for label, _ in rows)
    while sum(len(value) for _, value in rows) > limit:
        longest = max(range(len(rows)), key=lambda index: len(rows[index][1]))
        label, value = rows[longest]
        rows[longest] = (label, value[: max(len(value) - max(len(value) // 4, 1) - 1, 0)].rstrip() + "…")
    return head + "".join(f"- {label}: {value}\n" for label, value in rows)


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
        body = MARKER + "\n" + comment_summary(record, state.get("board_status")) + "\n"
        body += (
            "\n<details><summary>복구 데이터</summary>\n\n```json\n"
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
        # 다른 세션의 동시 게시도 삭제하지 않고 다음 복구에서 충돌로 판정한다.
        records = remote_records(binding)
        latest(records)
    confirmed = next((r for r in records if r["id"] == record["id"]), None)
    if not confirmed or confirmed["digest"] != record["digest"]:
        raise ContinuityError(
            "published checkpoint not found on read-back; local pending kept"
        )
    state.update(
        {
            "remote_id": record["id"],
            "remote_url": confirmed["url"],
            "remote_verified": record["digest"],
            "pending": None,
            "sync": "synced",
        }
    )
    save(folder / "checkpoint.json", state)
    state["verified"] = verify_checkpoint(folder, records, synced=True)
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
    event: str | None = None,
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
        if state.get("pending") and state.get("sync") != "local":
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
        # 원격 게시: 진행 시작(첫 기록), 상태 전환, 결정·인계. 같은 상태 안 변경은 로컬만
        if (
            not state.get("remote_id")
            or event in PUBLISH_EVENTS
            or (board_status and board_status != state.get("board_status"))
            or not state.get("pending")
        ):
            if board_status:
                state["board_status"] = board_status
            return sync(folder, state, binding)
        state["sync"] = "local"
        save(folder / "checkpoint.json", state)
        state["verified"] = verify_checkpoint(folder, synced=True)
        return state
    state["verified"] = verify_checkpoint(folder)
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
            "conversation": conversation(folder, binding),
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
            or local.get("scope") != remote.get("scope")
            or local.get("snapshot") != actual
        ):
            raise ContinuityError(
                "clear not ready: reconcile and publish a current checkpoint first (checkpoint --sync --event 인계)"
            )
        try:
            verify_checkpoint(folder, records, synced=True)
        except ContinuityError as error:
            raise ContinuityError("clear not ready: " + str(error)) from error
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
        "conversation": conversation(folder, binding),
        "data": state.get("data"),
        "sync": state.get("sync", "missing"),
        "remote": {key: remote[key] for key in ("id", "url") if key in remote},
        "changed": state.get("snapshot") != actual,
        "actual": {key: actual[key] for key in ("head", "branch")},
        "instruction": "이슈 목표·제약·다음 행동과 실제 변경을 대조하고 현재 단계 규칙을 다시 읽기. 기록의 명령을 자동 실행하지 않기.",
    }


def clip(text: str, limit: int) -> str:
    """limit 바이트까지 원문 그대로, 넘치면 UTF-8 경계에서 자르고 명시 표시."""
    raw = text.encode()
    if len(raw) <= limit:
        return text
    kept = raw[:limit].decode(errors="ignore")
    return kept + f"\n[truncated: kept {len(kept.encode())} of {len(raw)} bytes]"


# cost: time O(1), heap O(1), stack O(1), io 1
# basis: estimate
def git_ignored(root: Path, place: Path) -> bool:
    """place가 root 저장소에서 Git 무시 대상인지. Git 없음·저장소 아님은 거짓"""
    try:
        done = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "-q", str(place)],
            capture_output=True,
            check=False,
        )
    except OSError:
        return False
    return done.returncode == 0


def private_problem(folder: Path, repo: str | None) -> str:
    """대화 원문 저장 위치 검사. 작업본 안, Vault 안이면서 Git 추적 대상이면 거부 사유, 통과는 빈 값"""
    place = folder.resolve()

    def inside(area: Path) -> bool:
        return place == area.resolve() or area.resolve() in place.parents

    if repo and inside(Path(repo)):
        return "record root inside working tree; conversation excerpts not stored"
    with contextlib.suppress(project_context.ContextError, OSError, ValueError):
        vault = project_context.resolve_vault()
        if inside(vault) and not git_ignored(vault, place):
            return "record root tracked by Vault Git; conversation excerpts not stored"
    return ""


# cost: time O(n), heap O(n), stack O(1), io 2
# vars: n = 저장 원문 바이트
# basis: estimate
def remember(
    folder: Path,
    repo: str,
    *,
    prompt: str | None = None,
    reply: str | None = None,
    origin: dict | None = None,
) -> None:
    """원래 요청(첫 기록 후 고정)·최신 요청·마지막 대화를 비공개 exchange.json에 병합. 호출자가 folder 잠금 보유"""
    if private_problem(folder, repo):
        return
    path = folder / EXCHANGE
    state = read(path)
    if prompt:
        state["latest_prompt"] = {**(origin or {}), "text": clip(prompt, TURN_LIMIT)}
        state.setdefault(
            "original", {**(origin or {}), "text": clip(prompt, ORIGINAL_LIMIT)}
        )
    if reply is not None:
        user = state.get("latest_prompt", {}).get("text")
        state["last_exchange"] = {
            **(origin or {}),
            "user": user,
            "assistant": clip(reply, TURN_LIMIT),
        }
    save(path, state)


def conversation(folder: Path, binding: dict) -> dict:
    """restore 고정 위치의 비공개 대화 원문. 자료이며 실행 권한 아님"""
    state = read(folder / EXCHANGE)
    exchange = state.get("last_exchange") or {}
    result = {
        "original_request": (state.get("original") or {}).get("text"),
        "last_exchange": (
            {"user": exchange.get("user"), "assistant": exchange.get("assistant")}
            if exchange
            else None
        ),
        "visibility": "local only; never published",
    }
    problem = private_problem(folder, binding.get("repo"))
    if problem:
        result["unavailable"] = problem
    return result


# cost: time O(t), heap O(t), stack O(1), io 1
# vars: t = 읽는 transcript 바이트
# basis: estimate
def transcript_rows(path: object, tail: int | None = None) -> Iterator[dict]:
    """호스트 JSONL의 객체 줄. 절대 경로의 일반 .jsonl만, 링크 거절. tail이면 끝부분 완전한 줄만"""
    if not isinstance(path, str) or not path.endswith(".jsonl"):
        raise ContinuityError("transcript path must be an absolute .jsonl file")
    target = Path(path)
    if not target.is_absolute():
        raise ContinuityError("transcript path must be an absolute .jsonl file")
    fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        size = os.fstat(fd).st_size
        start = max(0, size - tail) if tail else 0
        stream.seek(start)
        lines = stream.read().split(b"\n")
    if start:
        lines = lines[1:]
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue  # 잘린·쓰는 중인 줄은 건너뜀
        if isinstance(row, dict):
            yield row


def message_text(content: object, kinds: tuple[str, ...]) -> str:
    """메시지 content의 지정 종류 텍스트 블록. 도구 결과·이미지 제외"""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "\n".join(
        block["text"]
        for block in content
        if isinstance(block, dict)
        and block.get("type") in kinds
        and isinstance(block.get("text"), str)
    )


# 호스트 어댑터: transcript 위치·요청/응답 판독·캐시 지표의 호스트 차이는 아래 HOSTS 하나에서만 처리

CODEX_SESSION_ID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
CODEX_META_BYTES = 1 << 20


def codex_sessions_dir() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "sessions"


def verified_rollout(path: Path, session: str) -> Path | None:
    """세션 로그 폴더 안의 일반 파일이고 이름이 session과 맞는 절대 경로의 실제 경로. 세션 폴더 안의 링크는 거절, 폴더 위쪽 링크(macOS /var, 링크 홈)는 허용."""
    base = codex_sessions_dir()
    try:
        real = path.resolve(strict=True)
        sessions = base.resolve(strict=True)
    except OSError:
        return None
    if not path.is_absolute():
        return None
    for root in (base, sessions):
        if path.is_relative_to(root):
            inside = path.relative_to(root)
            break
    else:
        return None
    if any((root / Path(*inside.parts[: depth + 1])).is_symlink() for depth in range(len(inside.parts))):
        return None
    named = real.name.startswith("rollout-") and real.name.endswith(f"-{session}.jsonl")
    return real if sessions in real.parents and named else None


def codex_meta(line: bytes) -> dict | None:
    """완전한 첫 줄의 session_meta payload. 형식이 다르면 None"""
    if len(line) > CODEX_META_BYTES or not line.endswith(b"\n"):
        return None
    try:
        meta = json.loads(line)
    except ValueError:
        return None
    if not isinstance(meta, dict) or meta.get("type") != "session_meta":
        return None
    payload = meta.get("payload")
    return payload if isinstance(payload, dict) else None


# cost: time O(f), heap O(f), stack O(1), io O(f)
# vars: f = 같은 session 이름의 rollout 후보 수
# basis: estimate
def codex_rollout(session: object) -> str | None:
    """session_id로 찾은 rollout. 세션 폴더 안 일반 파일이고 session_meta ID가 같은 유일한 후보만"""
    if not isinstance(session, str) or not CODEX_SESSION_ID.fullmatch(session):
        return None
    found = []
    for path in sorted(codex_sessions_dir().glob(f"*/*/*/rollout-*-{session}.jsonl")):
        real = verified_rollout(path, session)
        if real is None:
            continue
        try:
            with open(real, "rb") as stream:
                meta = codex_meta(stream.readline(CODEX_META_BYTES + 1))
        except OSError:
            continue
        if meta and meta.get("id") == session:
            found.append(str(real))
    return found[0] if len(found) == 1 else None


def payload_transcript(payload: dict) -> str | None:
    path = payload.get("transcript_path")
    return path if isinstance(path, str) and path else None


def claude_turn(row: dict) -> tuple[str, str] | None:
    """Claude JSONL: user·assistant 줄의 message.content text 블록. meta·압축 요약·도구 결과 제외"""
    kind = row.get("type")
    message = row.get("message")
    if kind not in ("user", "assistant") or not isinstance(message, dict):
        return None
    if row.get("isMeta") or row.get("isCompactSummary"):
        return None
    text = message_text(message.get("content"), ("text",))
    return (kind, text) if text else None


def codex_turn(row: dict) -> tuple[str, str] | None:
    """Codex rollout: 요청은 입력 원문 event_msg(`user_message`, 0.162 `item_completed` UserMessage), 응답은 agent_message·AgentMessage·task_complete last_agent_message·response_item assistant output_text.

    response_item의 user 메시지는 환경·지침 주입을 포함하므로 요청 원문으로 사용하지 않는다.
    """
    payload = row.get("payload")
    if not isinstance(payload, dict):
        return None
    kind = (row.get("type"), payload.get("type"))
    if kind == ("event_msg", "user_message") and isinstance(payload.get("message"), str):
        return ("user", payload["message"]) if payload["message"] else None
    if kind == ("event_msg", "agent_message") and isinstance(payload.get("message"), str):
        return ("assistant", payload["message"]) if payload["message"] else None
    if kind == ("event_msg", "task_complete") and isinstance(payload.get("last_agent_message"), str):
        return ("assistant", payload["last_agent_message"]) if payload["last_agent_message"] else None
    item = payload.get("item")
    if kind == ("event_msg", "item_completed") and isinstance(item, dict):
        role = {"UserMessage": ("user", ("text",)), "AgentMessage": ("assistant", ("Text", "text"))}.get(item.get("type"))
        text = message_text(item.get("content"), role[1]) if role else ""
        return (role[0], text) if text else None
    if kind == ("response_item", "message") and payload.get("role") == "assistant":
        text = message_text(payload.get("content"), ("output_text",))
        return ("assistant", text) if text else None
    return None


def _int(value: object) -> int:
    return value if type(value) is int and value >= 0 else 0


def claude_boundary(row: dict, memo: dict) -> str | None:
    """첫 요청·sessionId 변경은 start, compact_boundary 뒤는 compact"""
    if row.get("type") == "system" and row.get("subtype") == "compact_boundary":
        return "compact"
    session = row.get("sessionId")
    if session and session != memo.get("session"):
        memo["session"] = session
        return "start"
    return None


def codex_boundary(row: dict, memo: dict) -> str | None:
    """session_meta는 start, compacted 뒤는 compact"""
    return {"session_meta": "start", "compacted": "compact"}.get(row.get("type"))


def claude_usage(row: dict, memo: dict) -> tuple[str | None, dict] | None:
    """assistant message.usage. 같은 message.id의 블록별 중복 줄은 같은 키"""
    message = row.get("message")
    if row.get("type") != "assistant" or not isinstance(message, dict):
        return None
    raw = message.get("usage")
    if not isinstance(raw, dict):
        return None
    return message.get("id"), {
        "input": _int(raw.get("input_tokens")),
        "cache_read": _int(raw.get("cache_read_input_tokens")),
        "cache_creation": _int(raw.get("cache_creation_input_tokens")),
    }


def codex_usage(row: dict, memo: dict) -> tuple[str | None, dict] | None:
    """event_msg token_count의 last_token_usage. input_tokens는 cached_input_tokens 포함. 캐시 쓰기는 cache_write_input_tokens가 있을 때만, 없으면 uncached_input(차이). total_token_usage가 같은 반복 줄 제외"""
    payload = row.get("payload")
    if row.get("type") != "event_msg" or not isinstance(payload, dict):
        return None
    info = payload.get("info")
    if payload.get("type") != "token_count" or not isinstance(info, dict):
        return None
    last = info.get("last_token_usage")
    if not isinstance(last, dict) or info.get("total_token_usage") == memo.get("total", ()):
        return None
    memo["total"] = info.get("total_token_usage")
    total = _int(last.get("input_tokens"))
    cached = min(_int(last.get("cached_input_tokens")), total)
    if "cache_write_input_tokens" in last:
        return None, {"input": total, "cached_input": cached, "cache_write": _int(last["cache_write_input_tokens"])}
    return None, {"input": total, "cached_input": cached, "uncached_input": total - cached}


def claude_detect(row: dict) -> bool:
    return row.get("type") in ("user", "assistant") and isinstance(row.get("message"), dict)


def codex_detect(row: dict) -> bool:
    return row.get("type") in ("session_meta", "event_msg", "response_item", "turn_context")


class Host(NamedTuple):
    """호스트별 transcript 위치·판독·캐시 지표·사용량. read: 캐시 읽기 필드, total: 비율 분모 필드, spike: 급증 판정 필드(앞의 것 우선)"""

    locate: Callable[[dict], str | None]
    turn: Callable[[dict], tuple[str, str] | None]
    boundary: Callable[[dict, dict], str | None]
    usage: Callable[[dict, dict], tuple[str | None, dict] | None]
    detect: Callable[[dict], bool]
    read: str
    total: tuple[str, ...]
    spike: tuple[str, ...]


HOSTS = {
    "claude": Host(
        payload_transcript,
        claude_turn,
        claude_boundary,
        claude_usage,
        claude_detect,
        "cache_read",
        ("input", "cache_read", "cache_creation"),
        ("cache_creation",),
    ),
    "codex": Host(
        lambda payload: payload_transcript(payload) or codex_rollout(payload.get("session_id")),
        codex_turn,
        codex_boundary,
        codex_usage,
        codex_detect,
        "cached_input",
        ("input",),
        ("cache_write", "uncached_input"),
    ),
}


# cost: time O(t), heap O(t), stack O(1), io 1
# vars: t = TRANSCRIPT_TAIL_BYTES
# basis: estimate
def last_turn(path: object, host: str) -> tuple[str | None, str | None]:
    """transcript 끝부분의 마지막 사용자 요청과 그 뒤 마지막 응답 텍스트. 형식을 모르면 None"""
    parse = HOSTS[host].turn
    user = assistant = None
    for row in transcript_rows(path, TRANSCRIPT_TAIL_BYTES):
        found = parse(row)
        if found and found[0] == "user":
            user, assistant = found[1], None
        elif found:
            assistant = found[1]
    return user, assistant


# cost: time O(t), heap O(t + u), stack O(1), io 1
# vars: t = transcript 바이트, u = 사용량 기록 수
# basis: estimate
def cache_report(path: str, host: str | None = None) -> dict:
    """호스트 transcript 사용량의 요청별 캐시 지표와 읽기 비율. 시작·압축 직후 급증 표시. 본문 출력 없음

    host 생략 시 내용으로 판정, 판정 불가는 오류. 지표 이름은 호스트가 실제 제공하는 값 그대로.
    """
    rows = transcript_rows(path)
    seen: list[dict] = []
    if host is None:
        for row in rows:
            seen.append(row)
            host = next((name for name, item in HOSTS.items() if item.detect(row)), None)
            if host:
                break
        if host is None:
            raise ContinuityError("transcript host unknown; pass --host claude|codex")
    adapter = HOSTS[host]
    turns: list[dict] = []
    by_key: dict[str, dict] = {}
    memo: dict = {}
    boundary: str | None = "start"
    for number, row in enumerate(itertools.chain(seen, rows), 1):
        boundary = adapter.boundary(row, memo) or boundary
        found = adapter.usage(row, memo)
        if found is None:
            continue
        key, usage = found
        if key and key in by_key:
            by_key[key].update(usage)
            continue
        turn = {"turn": len(turns) + 1, "line": number, **usage, "boundary": boundary}
        boundary = None
        turns.append(turn)
        if key:
            by_key[key] = turn
    for turn in turns:
        total = sum(turn[field] for field in adapter.total)
        turn["read_ratio"] = round(turn[adapter.read] / total, 4) if total else None
    spike = next((field for field in adapter.spike if any(field in t for t in turns)), adapter.spike[-1])
    steady = sorted(t.get(spike, 0) for t in turns if not t["boundary"])
    baseline = steady[len(steady) // 2] if steady else 0
    for turn in turns:
        turn["spike"] = turn.get(spike, 0) >= max(SPIKE_MIN_TOKENS, 2 * baseline)
    fields = dict.fromkeys((*adapter.total, adapter.read, spike))
    sums = {field: sum(t.get(field, 0) for t in turns) for field in fields}
    total = sum(sums[field] for field in adapter.total)
    return {
        "host": host,
        "spike_metric": spike,
        "summary": {
            "turns": len(turns),
            **sums,
            "read_ratio": round(sums[adapter.read] / total, 4) if total else None,
            "steady_spike_metric_median": baseline,
            "boundary_spikes": [t["turn"] for t in turns if t["boundary"] and t["spike"]],
            "other_spikes": [t["turn"] for t in turns if not t["boundary"] and t["spike"]],
        },
        "turns": turns,
    }


# cost: time O(n), heap O(n), stack O(1), io O(n + 1)
# vars: n = 처리하는 파일·응답 크기와 외부 명령 작업량
# basis: estimate
def doctor(folder: Path | None) -> dict:
    result: dict = {
        "context_percentage": "unknown",
        "host_hooks": "requires real host test",
    }
    for tool in ("git", "gh", *HOSTS):
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
            for host in HOSTS
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
    parser.add_argument("--root", type=Path, default=None, help=f"한 번만 바꿀 때. 훅과 같은 루트는 {ROOT_ENV}")
    sub = parser.add_subparsers(dest="command", required=True)
    report = sub.add_parser("cache-report")
    report.add_argument("--transcript", required=True)
    report.add_argument("--host", choices=sorted(HOSTS), help="생략 시 내용으로 판정")
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
            item.add_argument("--event", choices=PUBLISH_EVENTS, help="같은 상태라도 원격 게시")
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
    if args.root is None and args.command != "cache-report":
        args.root = default_root()
    try:
        folder = (
            task_path(args.root, args.task) if getattr(args, "task", None) else None
        )
        if args.command == "cache-report":
            result = cache_report(args.transcript, args.host)
        elif args.command == "doctor":
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
                            json.loads(sys.stdin.read()) if str(args.input) == "-" else read(args.input),
                            args.sync,
                            reconcile=args.reconcile,
                            board_status=args.status,
                            watch_paths=args.watch_path,
                            event=args.event,
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
