"""just do 훅의 과업 연결과 저장소 `.local/` 상태를 다룬다.

사용:
  python3 task.py bind [--task <과업>] [--issue <이슈 URL>] [--session-id <세션 ID>] [--cwd <경로>]
  python3 task.py show [--session-id <세션 ID>] [--cwd <경로>]
  python3 task.py unbind [--session-id <세션 ID>] [--cwd <경로>]

인자: bind|show|unbind, --task 과업 이름(생략하면 현재 브랜치 이름, `/`는 `-`), --issue 이슈 URL, --session-id 세션 ID(생략하면 CODEX_THREAD_ID), --cwd 작업 경로(기본 현재 폴더)
출력: stdout JSON, 실패는 stderr와 종료 2

연결은 "이 세션이 어느 과업·이슈인지"만 기록한다.
결정 기록은 `.local/decisions/<과업>.tsv`(show-me-your-work log.sh 형식)이고 이 스크립트는 읽기만 한다.
`.local/`은 워크트리가 아니라 기본 체크아웃(공통 git 디렉터리의 상위)에 둔다. 워크트리를 지워도 연결과 기록이 남는다.
"""

from __future__ import annotations

import argparse
import contextlib
import contextvars
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Iterator

# 훅이 쓰는 다른 스킬의 파일. 위치가 바뀌면 이 표만 고친다.
RULE_READER = ("mode", "scripts/rules/read_rules.py")
CAREER_NOTES = ("markdown-notes-agent", "SKILL.md")
DECISION_LOGGER = ("show-me-your-work", "scripts/log.sh")
ENTRY_SKILL = "mode"
CATEGORIES = ("just", "code", "docs", "git", "design", "tools", "personal")

LOCAL = ".local"
SESSIONS = "sessions"
DECISIONS = "decisions"
TAIL_LINES = 5
DEADLINE_ENV = "JUST_DO_DEADLINE"
CONFIG_ENV = "SKILLS_CONFIG_DIR"
TASK_NAME = re.compile(r"[^/\\\s.][^/\\\s]{0,79}")
_EVENT_PATHS: contextvars.ContextVar[dict[Path, Path] | None] = contextvars.ContextVar("event_paths", default=None)


class TaskError(Exception):
    """연결·상태 파일을 다룰 수 없는 오류."""


def time_budget(limit: float) -> float:
    """외부 명령 대기 상한. 훅 마감 시각이 있으면 남은 시간으로 줄이고, 지났으면 TimeoutExpired."""
    try:
        deadline = float(os.environ[DEADLINE_ENV])
    except (KeyError, ValueError):
        return limit
    remaining = deadline - time.time()
    if remaining <= 0:
        raise subprocess.TimeoutExpired("just do hook", 0)
    return min(limit, remaining)


def config_directory() -> Path:
    return Path(os.environ.get(CONFIG_ENV) or Path.home() / ".config/skills").expanduser()


def skill_file(owner: tuple[str, str]) -> Path | None:
    """설치본(스킬 폴더 나란히) 또는 원본 저장소(분류 폴더 아래)의 스킬 파일."""
    name, relative = owner
    entry = Path(__file__).resolve().parents[2]
    candidates = [entry.parent / name / relative]
    candidates += [entry.parents[1] / category / name / relative for category in CATEGORIES]
    return next((path for path in candidates if path.is_file()), None)


def entry_skill() -> Path:
    """설치된 mode의 SKILL.md 절대 경로."""
    return Path(__file__).resolve().parents[2] / "SKILL.md"


def git_root(cwd: object) -> Path | None:
    if not isinstance(cwd, str) or not cwd:
        return None
    try:
        done = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=time_budget(2),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return Path(done.stdout.strip()) if done.returncode == 0 and done.stdout.strip() else None


@contextlib.contextmanager
def event_paths() -> Iterator[None]:
    """한 훅 이벤트 안에서만 작업본별 공통 경로의 성공한 조회를 재사용한다."""
    token = _EVENT_PATHS.set({})
    try:
        yield
    finally:
        _EVENT_PATHS.reset(token)


def shared_root(repo: Path) -> Path:
    """`.local/`을 둘 기본 체크아웃. 공통 git 디렉터리가 `.git`이 아니면(서브모듈 등) 작업본 자신."""
    paths = _EVENT_PATHS.get()
    if paths is not None and repo in paths:
        return paths[repo]
    done = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True, text=True, timeout=time_budget(2),
    )
    common = Path(done.stdout.strip()).resolve() if done.returncode == 0 and done.stdout.strip() else None
    root = common.parent if common is not None and common.name == ".git" else repo
    if common is not None and paths is not None:
        paths[repo] = root
    return root


def current_branch(repo: Path) -> str | None:
    """현재 브랜치 이름. 분리된 HEAD면 없음."""
    done = subprocess.run(
        ["git", "-C", str(repo), "symbolic-ref", "--short", "-q", "HEAD"],
        capture_output=True, text=True, timeout=time_budget(2),
    )
    return done.stdout.strip() if done.returncode == 0 and done.stdout.strip() else None


def on_work_branch(repo: Path) -> bool:
    """기본 브랜치가 아닌 브랜치에 있는가. 기본 브랜치는 `origin/HEAD`, 없으면 `main`이나 `master`다."""
    branch = current_branch(repo)
    if branch is None:
        return False
    done = subprocess.run(
        ["git", "-C", str(repo), "symbolic-ref", "--short", "-q", "refs/remotes/origin/HEAD"],
        capture_output=True, text=True, timeout=time_budget(2),
    )
    remote = done.stdout.strip().split("/", 1)[-1] if done.returncode == 0 else ""
    return branch != remote if remote else branch not in {"main", "master"}


def branch_task(repo: Path) -> str | None:
    """연결 과업이 없을 때 쓰는 과업 이름. 현재 브랜치 이름의 `/`를 `-`로 바꾼다. 분리된 HEAD면 없음."""
    name = (current_branch(repo) or "").replace("/", "-")
    return name if TASK_NAME.fullmatch(name) else None


def local_folder(repo: Path, *parts: str) -> Path:
    """기본 체크아웃 `.local/` 아래 폴더. `.local/`이 git 무시 대상이 아니면 `.local/.gitignore`로 스스로 무시한다."""
    repo = shared_root(repo)
    local = repo / LOCAL
    if local.is_symlink():
        raise TaskError(f"{local} must not be a symlink")
    folder = local.joinpath(*parts)
    folder.mkdir(parents=True, exist_ok=True)
    marker = local / ".gitignore"
    if not marker.exists():
        ignored = subprocess.run(
            ["git", "-C", str(repo), "check-ignore", "-q", f"{LOCAL}/{SESSIONS}/probe"],
            capture_output=True, timeout=time_budget(2),
        )
        if ignored.returncode != 0:
            marker.write_text("*\n", encoding="utf-8")
    return folder


def session_key(session: str, agent: str = "") -> str:
    return hashlib.sha256((session + "\0" + agent).encode()).hexdigest()[:20]


def session_path(repo: Path, session: str) -> Path:
    return local_folder(repo, SESSIONS) / f"{session_key(session)}.json"


def rules_path(repo: Path, session: str, agent: str) -> Path:
    """세션·서브에이전트별 규칙 전달 상태. 같은 세션의 파일은 `<세션 키>.*.rules.json`으로 모인다."""
    return local_folder(repo, SESSIONS) / f"{session_key(session)}.{session_key(agent)[:12]}.rules.json"


def read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except ValueError as error:
        raise TaskError(f"broken state file {path}: {error}") from error
    return value if isinstance(value, dict) else {}


def save(path: Path, value: dict[str, Any]) -> None:
    draft = path.with_name(path.name + ".pending")
    draft.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(draft, path)


@contextlib.contextmanager
def locked(repo: Path) -> Iterator[None]:
    with (local_folder(repo, SESSIONS) / ".lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def decisions_folder(repo: Path) -> Path:
    return shared_root(repo) / LOCAL / DECISIONS


def decision_log(repo: Path, task: str) -> Path:
    return decisions_folder(repo) / f"{task}.tsv"


def recent_tasks(repo: Path, limit: int = 3) -> list[str]:
    """최근에 고친 결정 기록의 과업 이름. 새 세션이 이어받을 기록을 고르게 알려 준다."""
    paths = sorted(decisions_folder(repo).glob("*.tsv"), key=lambda path: path.stat().st_mtime, reverse=True)
    return [path.stem for path in paths[:limit]]


def decision_rows(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    return [line for line in lines[1:] if line.strip()]


def decision_mark(repo: Path, task: str | None) -> int:
    """결정 기록 줄 수. 연결 과업이 있으면 그 기록, 없으면 `.local/decisions/` 전체."""
    if task:
        return len(decision_rows(decision_log(repo, task)))
    return sum(len(decision_rows(path)) for path in decisions_folder(repo).glob("*.tsv"))


def tree_mark(repo: Path) -> str:
    """작업본 변경 지문: 바뀐 경로와 각 파일의 크기·수정 시각. `.local/`은 git 무시 대상이라 빠진다."""
    done = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        capture_output=True, timeout=time_budget(3),
    )
    if done.returncode:
        raise TaskError("git status failed")
    rows = []
    for entry in done.stdout.decode("utf-8", "surrogateescape").split("\0"):
        if len(entry) < 4:
            continue
        path = repo / entry[3:]
        try:
            stat = path.stat()
            rows.append([entry, stat.st_size, stat.st_mtime_ns])
        except OSError:
            rows.append([entry, None, None])
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


def binding(repo: Path, session: str) -> dict[str, Any]:
    state = read(session_path(repo, session))
    return {key: state[key] for key in ("task", "issue") if state.get(key)}


def _session(value: str | None) -> str:
    session = value or os.environ.get("CODEX_THREAD_ID", "")
    if not session:
        raise TaskError("--session-id required (훅 안내의 세션 ID 사용)")
    return session


def _repo(cwd: str) -> Path:
    repo = git_root(cwd)
    if repo is None:
        raise TaskError(f"not inside a git repository: {cwd}")
    return repo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("bind", "show", "unbind"):
        command = commands.add_parser(name)
        command.add_argument("--session-id")
        command.add_argument("--cwd", default=os.getcwd())
        if name == "bind":
            command.add_argument("--task")
            command.add_argument("--issue", default="")
    args = parser.parse_args(argv)
    try:
        repo = _repo(args.cwd)
        session = _session(args.session_id)
        path = session_path(repo, session)
        with locked(repo):
            state = read(path)
            if args.command == "bind":
                name = args.task or branch_task(repo)
                if not name:
                    raise TaskError("--task required (detached HEAD has no branch name)")
                if not TASK_NAME.fullmatch(name):
                    raise TaskError("task name: 1-80 chars, no path separator or space, not starting with '.'")
                state.update({"session_id": session, "task": name, "issue": args.issue})
                save(path, state)
            elif args.command == "unbind":
                for key in ("task", "issue"):
                    state.pop(key, None)
                save(path, state)
        result = {"repo": str(repo), "session_id": session, **binding(repo, session)}
        if result.get("task"):
            result["decisions"] = str(decision_log(repo, result["task"]))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (TaskError, OSError, subprocess.TimeoutExpired) as error:
        print(f"task.py: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
