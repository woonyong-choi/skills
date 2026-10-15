"""제품별 훅 JSON 어댑터. 인자: claude|codex, stdin 이벤트, stdout 훅 JSON.

사용량은 Claude status line 또는 명시적인 호스트 이벤트만 사용한다.
인자: 명령별 --help 또는 위 설명
출력: stdout JSON 또는 원래 status line, 실패 stderr와 종료 코드
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import sys
import time
from typing import Any, BinaryIO

import continuity as core
import project_context
import document_guard


def session_tasks(root: Path, session: object) -> list[Path]:
    """session이 명시 bind된 task 폴더들. session이 없으면 빈 목록"""
    if not isinstance(session, str) or not session:
        return []
    return [
        path.parent
        for path in sorted(root.glob("*/binding.json"))
        if session in core.read(path).get("session_ids", [])
    ]


# cost: time O(1), heap O(1), stack O(1), io 1
# basis: estimate
def pane_identity(pane: str) -> str | None:
    """tmux가 알려주는 실제 pane·프로세스·창 식별자. 확인할 수 없으면 None"""
    try:
        done = subprocess.run(
            [
                "tmux",
                "display-message",
                "-p",
                "-t",
                pane,
                "#{pane_id}|#{pane_pid}|#{window_id}",
            ],
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def managed_window(
    root: Path, host: str | None = None
) -> tuple[Path, dict[str, Any]] | None:
    """환경이 가리키는 관리 창의 home과 기록. 기록된 pane·identity·host가 현재 tmux의 실제 값과 같을 때만 신뢰한다."""
    window = os.environ.get("ISSUE_CONTINUITY_WINDOW")
    pane = os.environ.get("TMUX_PANE")
    if not window or not pane:
        return None
    home = Path(window)
    if home.parent.resolve() != root.resolve():
        return None
    state = core.read(home / "window.json")
    if state.get("pane") != pane or not state.get("identity"):
        return None
    if host is not None and state.get("host") != host:
        return None
    return (home, state) if pane_identity(pane) == state["identity"] else None


def window_task(root: Path, host: str | None = None) -> Path | None:
    """검증된 관리 창이 현재 따라가는 task. 창이 시작한 cwd와 task의 작업본이 달라도 창 기록을 따른다."""
    window = managed_window(root, host)
    active = window[1].get("active_task") if window else None
    if not isinstance(active, str):
        return None
    try:
        candidate = core.task_path(root, active)
    except core.ContinuityError:
        return None
    return candidate if core.read(candidate / "binding.json") else None


def hinted_task(root: Path, repo: str) -> Path | None:
    """ISSUE_CONTINUITY_TASK 힌트. 명시 session bind를 덮지 않으며 작업본 일치만 검증"""
    explicit = os.environ.get("ISSUE_CONTINUITY_TASK")
    if not explicit:
        return None
    candidate = core.task_path(root, explicit)
    return (
        candidate if core.read(candidate / "binding.json").get("repo") == repo else None
    )


def find_task(
    root: Path, payload: dict[str, Any], host: str | None = None
) -> Path | None:
    """session 명시 bind가 최우선이다. 둘 이상이면 선택하지 않고, 미등록일 때만 검증된 fallback을 쓴다.

    관리 창 안(ISSUE_CONTINUITY_WINDOW)이면 창 기록을 검증해 활성 task를 따르고, 검증 실패는 다른 후보를 찾지 않고 중단한다.
    """
    bound = session_tasks(root, payload.get("session_id"))
    if bound:
        return bound[0] if len(bound) == 1 else None
    if os.environ.get("ISSUE_CONTINUITY_WINDOW"):
        return window_task(root, host)
    cwd = payload.get("cwd")
    if not cwd:
        return None
    try:
        repo = core.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd).strip()
    except core.ContinuityError:
        return None
    if os.environ.get("ISSUE_CONTINUITY_TASK"):
        return hinted_task(root, repo)
    candidates = [
        p.parent
        for p in root.glob("*/binding.json")
        if core.read(p).get("repo") == repo
    ]
    return candidates[0] if len(candidates) == 1 else None


def link_session(root: Path, folder: Path, session: str) -> None:
    """binding의 session_ids에만 session을 추가한다. 다른 task에 이미 있으면 거절하고 기존 연결은 보존한다."""
    with core.locked(root):
        for other in session_tasks(root, session):
            if other != folder:
                raise core.ContinuityError("session already bound to " + other.name)
        path = folder / "binding.json"
        binding = core.read(path)
        if not binding:
            raise core.ContinuityError("binding missing")
        if session not in binding.get("session_ids", []):
            binding["session_ids"] = sorted({*binding.get("session_ids", []), session})
            core.save(path, binding)


def adopt_new_session(
    root: Path, folder: Path, payload: dict[str, Any], host: str
) -> str:
    """제어기가 clear 중인 관리 창의 새 session만 활성 task에 연결한다. 연결 실패 사유를 돌려준다.

    창 안에서 따로 시작한 session(하위 CLI 등)은 clear 단계가 아니면 연결하지 않는다.
    """
    session = payload.get("session_id")
    binding = core.read(folder / "binding.json")
    if not isinstance(session, str) or session in binding.get("session_ids", []):
        return ""
    window = managed_window(root, host)
    if window is None or window_task(root, host) != folder:
        return ""
    state = window[1]
    if state.get("phase") != "clearing" or state.get("old_session") not in binding.get(
        "session_ids", []
    ):
        return ""
    try:
        link_session(root, folder, session)
    except core.ContinuityError as error:
        return str(error)
    return ""


CODEX_CLI_VERSION = "0.158.0"
CODEX_RECORD_MAX_AGE_SECONDS = 6 * 60 * 60
CODEX_METRIC_MAX_AGE_SECONDS = 6 * 60 * 60
CODEX_CLOCK_SKEW_SECONDS = 60
ROLLOUT_HEAD_BYTES = 1 << 20
ROLLOUT_TAIL_BYTES = 4 << 20
SESSION_ID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")


def codex_sessions_dir() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "sessions"


# cost: time O(1), heap O(1), stack O(1), io 3
# basis: estimate
def record_codex_session(root: Path, folder: Path, payload: dict[str, Any]) -> None:
    """검증된 Codex 관리 창에서 현재 session의 유일한 명시 bind가 folder일 때만 session ID와 rollout 경로를 창 home의 meter.json에 남긴다.

    창의 active_task가 없거나 낡았어도 기록한다. window.json은 쓰지 않고 관리기가 이 session의 bind를 따라 active_task를 갱신한다. 본문은 읽지 않는다.
    """
    session = payload.get("session_id")
    path = payload.get("transcript_path")
    window = managed_window(root, "codex")
    if window is None or not isinstance(session, str) or not session:
        return
    home = window[0]
    if session_tasks(root, session) != [folder]:
        return  # 미등록·중복 bind는 session을 확정할 수 없다
    record = {
        "host": "codex",
        "session_id": session,
        "transcript_path": path if isinstance(path, str) and path else None,
        "percent": None,
        "at": time.time(),
    }
    try:
        with core.locked(home):
            core.save(home / "meter.json", record)
    except (OSError, ValueError, core.ContinuityError) as error:
        # 기록 실패가 훅 응답을 막지 않게 한다. 사용량은 unknown으로 남는다.
        print(
            f"continuity hook: codex session record skipped: {error}", file=sys.stderr
        )


def codex_record(home: Path, now: float) -> tuple[str, Path] | None:
    """meter.json의 최근 Codex session 기록. 형식·최근성이 틀리면 None"""
    try:
        meter = core.read(home / "meter.json")
    except (OSError, ValueError):
        return None  # 깨진 기록은 session도 사용량도 알 수 없다
    session, path, at = (
        meter.get("session_id"),
        meter.get("transcript_path"),
        meter.get("at"),
    )
    if meter.get("host") != "codex" or not isinstance(path, str) or not path:
        return None
    if not isinstance(session, str) or not SESSION_ID.fullmatch(session):
        return None
    if not isinstance(at, (int, float)) or isinstance(at, bool):
        return None
    fresh = -CODEX_CLOCK_SKEW_SECONDS <= now - at <= CODEX_RECORD_MAX_AGE_SECONDS
    return (session, Path(path)) if fresh else None


def verified_rollout(path: Path, session: str) -> Path | None:
    """세션 로그 폴더 안의 일반 파일이고 이름이 session과 맞는 절대 경로만 통과한다. 링크는 거절한다."""
    try:
        real = path.resolve(strict=True)
        sessions = codex_sessions_dir().resolve()
    except OSError:
        return None
    named = real.name.startswith("rollout-") and real.name.endswith(f"-{session}.jsonl")
    return real if real == path and sessions in real.parents and named else None


def session_meta_matches(line: bytes, session: str) -> bool:
    if len(line) > ROLLOUT_HEAD_BYTES or not line.endswith(b"\n"):
        return False
    try:
        meta = json.loads(line)
    except ValueError:
        return False
    if not isinstance(meta, dict):
        return False  # 최상위가 객체가 아니면 알려진 session_meta가 아니다
    payload = meta.get("payload")
    return (
        meta.get("type") == "session_meta"
        and isinstance(payload, dict)
        and payload.get("id") == session
        and payload.get("cli_version") == CODEX_CLI_VERSION
    )


# cost: time O(t), heap O(t), stack O(1), io 1
# vars: t = ROLLOUT_TAIL_BYTES
# basis: estimate
def tail_lines(stream: BinaryIO, size: int) -> tuple[list[bytes], bool]:
    """끝부분의 완전한 줄과, 줄바꿈 없이 쓰는 중인 마지막 조각이 있는지. 잘린 첫 줄은 버린다."""
    start = max(0, size - ROLLOUT_TAIL_BYTES)
    stream.seek(start)
    lines = stream.read(size - start).split(b"\n")
    is_unfinished = bool(lines[-1])
    return (lines[1:-1] if start > 0 else lines[:-1]), is_unfinished


def token_metric(line: bytes, now: float) -> float | None:
    """token_count 줄의 last_token_usage.total_tokens / model_context_window(%). 값이 틀리면 None"""
    try:
        record = json.loads(line)
        info = record["payload"]["info"]
        used, window = (
            info["last_token_usage"]["total_tokens"],
            info["model_context_window"],
        )
        stamp = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
    except (ValueError, KeyError, TypeError, AttributeError):
        return None  # 알려진 형식이 아니면 사용량을 만들지 않는다
    if type(used) is not int or type(window) is not int:
        return None
    if used < 0 or window <= 0 or used > window:
        return None
    if stamp.tzinfo is None:
        return None  # 시간대 없는 시각은 현재와 비교할 수 없다
    age = now - stamp.timestamp()
    if not -CODEX_CLOCK_SKEW_SECONDS <= age <= CODEX_METRIC_MAX_AGE_SECONDS:
        return None  # 오래됐거나 미래인 사용량으로 자동 초기화하지 않는다
    return round(used * 100 / window, 1)


def latest_metric(lines: list[bytes], now: float) -> float | None:
    """마지막 token_count의 비율. 그 뒤에 압축 기록이 있거나 값이 틀리면 None"""
    metric = None
    for line in lines:
        head = line[:160]
        if b'"type":"compacted"' in head:
            metric = None
        elif b'"type":"token_count"' in head:
            metric = token_metric(line, now)
    return metric


# cost: time O(t), heap O(t), stack O(1), io 3
# vars: t = ROLLOUT_TAIL_BYTES
# basis: estimate
def codex_usage(
    home: Path, now: float | None = None
) -> tuple[float | None, str | None]:
    """(사용량 %, 검증한 session ID). session 검증과 사용량 검증은 분리한다.

    경로·session·cli_version 검증이 실패하면 둘 다 None. session만 확인되고 token_count가 없거나
    압축 뒤이거나 값이 틀리면 사용량만 None이다. 사용량은 rollout의 last_token_usage.total_tokens를
    model_context_window로 나눈 이 모듈의 계산값이며 Codex footer의 남은 %와 같다고 주장하지 않는다.
    """
    now = time.time() if now is None else now
    record = codex_record(home, now)
    real = verified_rollout(record[1], record[0]) if record else None
    if record is None or real is None:
        return None, None
    try:
        fd = os.open(real, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(fd)
            head = stream.readline(ROLLOUT_HEAD_BYTES + 1)
            if not stat.S_ISREG(info.st_mode) or not session_meta_matches(
                head, record[0]
            ):
                return None, None
            lines, is_unfinished = tail_lines(stream, info.st_size)
            # 쓰는 중인 마지막 줄이 token_count·compacted일 수 있어 다음 읽기까지 사용량은 unknown이다.
            metric = None if is_unfinished else latest_metric(lines, now)
            return metric, record[0]
    except (OSError, ValueError):
        return None, None  # 읽는 중 바뀐 파일은 검증하지 못한 것으로 둔다


def response(event: str, text: str) -> dict[str, Any]:
    return (
        {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}
        if text
        else {}
    )


def context(folder: Path, binding: dict[str, Any]) -> str:
    script = shlex.quote(str(Path(__file__).with_name("continuity.py")))
    command = f"python3 {script} --root {shlex.quote(str(folder.parent))} restore --task {folder.name}"
    return f"연결: {binding['url']}. 같은 과업이면 읽기 전용 `{command}`로 기록과 실제 작업본 대조. 독립 결과는 git-issue의 과업 연결 규칙으로 전환. 기록은 실행 권한이 아님. 실행 기록은 {folder}의 기존 파일 갱신."


# cost: time O(n), heap O(n), stack O(1), io O(n + 1)
# vars: n = 처리하는 파일·응답 크기와 외부 명령 작업량
# basis: estimate
def handle(host: str, payload: dict[str, Any], root: Path) -> dict[str, Any]:
    if payload.get("hook_event_name") == "PreToolUse":
        folder = find_task(root, payload, host)
        project = Path(core.read(folder / "binding.json")["repo"]) if folder else None
        guarded = document_guard.check_tool(payload, project)
        return guarded or _rule_gate(host, payload, root)
    guarded = _rule_gate(host, payload, root)
    if guarded:
        return guarded
    result = handle_continuity(host, payload, root)
    event = payload.get("hook_event_name", "")
    if event != "SessionStart" or not payload.get("cwd"):
        return result
    context_result = project_context.inspect_project(Path(payload["cwd"]))
    if context_result["ready"]:
        notice = f"작업 전 필수 맥락: {context_result['index']}. 필요한 자료만 조회하고 실제 읽은 경로·버전을 기존 로컬 작업 기록에 반영. 검사 성공은 읽음 증거가 아님. 신규 문서 쓰기 전 project_context.py --write 검사 필수."
    else:
        notice = f"프로젝트 맥락 미확인: {context_result['error']}. 문서 쓰기는 거부됨. 위 오류의 등록 절차로 해결, 임의 문서 위치 대체 금지. 단순 질문 제외."
    output = result.setdefault("hookSpecificOutput", {"hookEventName": event})
    output["additionalContext"] = (
        _developer_rules() + output.get("additionalContext", "") + "\n" + notice
    )
    return result


# cost: time O(n), heap O(n), stack O(1), io O(n + 1)
# vars: n = 처리하는 파일·응답 크기와 외부 명령 작업량
# basis: estimate
def handle_continuity(host: str, payload: dict[str, Any], root: Path) -> dict[str, Any]:
    event = payload.get("hook_event_name", "")
    folder = find_task(root, payload, host)
    link_error = ""
    if folder is not None and event == "SessionStart":
        link_error = adopt_new_session(root, folder, payload, host)
    if folder is not None and host == "codex":
        record_codex_session(root, folder, payload)
    if folder is None:
        if event in ("SessionStart", "UserPromptSubmit"):
            if len(session_tasks(root, payload.get("session_id"))) > 1:
                return response(
                    event,
                    "현재 session이 여러 task에 연결되어 자동 선택하지 않습니다. 현재 과업의 task 하나만 남기도록 기록을 확인하세요. 기록은 지우지 말고 다른 task로 임의 진행하지 마세요.",
                )
            return response(
                event,
                f"개발 작업은 developer-thinking 본문부터 현재 단계의 소유 규칙 적용. git-issue의 과업 연결·보드 초기화에 따라 bind --session-id {payload.get('session_id', '현재채팅ID')} 연결. 미확인을 완료로 처리 금지. 단순 질의응답 제외.",
            )
        return {}
    session = payload.get("session_id")
    if not isinstance(session, str) or not session:
        raise core.ContinuityError("missing session_id")
    state_path = folder / (
        "session-"
        + hashlib.sha256((host + session).encode()).hexdigest()[:20]
        + ".json"
    )
    with core.locked(folder):
        state = core.read(state_path)
        binding = core.read(folder / "binding.json")
        checkpoint = core.read(folder / "checkpoint.json")
        state["host"] = host
        state.setdefault("events", {})[event] = time.time_ns()
        text = ""
        if not Path(binding["repo"]).is_dir():
            if not state.get("missing_reported") and event in (
                "SessionStart",
                "UserPromptSubmit",
            ):
                state["missing_reported"] = True
                core.save(state_path, state)
                return response(
                    event,
                    "연결 작업본이 없어 자동 복구를 보류합니다. 현재 과업의 이슈·실제 경로를 확인하고 bind --session-id "
                    + session
                    + " --from-task "
                    + folder.name
                    + "로 전환하세요. 기존 기록을 지우거나 종료를 반복하지 마세요.",
                )
            core.save(state_path, state)
            return {}
        state.pop("missing_reported", None)
        if event == "SessionStart":
            state.update(
                {
                    "notified": 0,
                    "needs_restore": False,
                    "start_source": payload.get("source", "unknown"),
                }
            )
            text = (
                "개발 작업은 developer-thinking 본문과 현재 단계의 필수 원문 확인. "
                + context(folder, binding)
            )
            if link_error:
                text += f" 새 session을 현재 task에 연결하지 못했습니다: {link_error}. 자동 연결·재개 입력을 하지 말고 bind 상태를 확인하세요."
        elif event == "UserPromptSubmit":
            state["prompt_at"] = time.time_ns()
            paths = checkpoint.get("watch_paths")
            state["turn_task_snapshot"] = (
                core.digest(core.snapshot(binding["repo"], paths)) if paths else None
            )
            needs_restore = state.pop("needs_restore", False)
            if needs_restore or not checkpoint:
                text = (_developer_rules() if needs_restore else "") + context(
                    folder, binding
                )
            else:
                text = f"현재 연결: {folder.name}, {binding['url']}. developer-thinking의 현재 단계 적용. git-issue의 과업 판정에 따라 goal 유지·scope.outcomes 대조. 독립 결과 전환은 기존 기록 저장 후 bind --session-id {session} --from-task {folder.name}. 작업 경계는 checkpoint --sync --status 진행|검토|보류. 단순 질문은 추가 기록 불필요."
            if not paths:
                text += " 파일 변경 전 실행자가 checkpoint --watch-path 상대경로를 반복 지정해 현재 과업의 파일 범위를 등록하세요. 사용자에게 목록 작성을 요구하지 마세요. 범위 미등록은 저장소 전체로 대체하지 않으며 종료 변경 감지는 미활성입니다."
        elif event == "PostCompact":
            meter_path = folder / "meter.json"
            core.save(
                meter_path,
                {
                    **core.read(meter_path),
                    "session_id": session,
                    "percent": None,
                    "at": time.time(),
                },
            )
            state.update({"needs_restore": True, "notified": 0})
        elif event == "PostToolUse":
            window = managed_window(root, host)
            meter = core.read((window[0] if window else folder) / "meter.json")
            percent = (
                meter.get("percent")
                if meter.get("session_id") == session
                and time.time() - meter.get("at", 0) < 120
                else None
            )
            band = (
                80
                if percent is not None and percent >= 80
                else 75
                if percent is not None and percent >= 75
                else 0
            )
            if band > state.get("notified", 0):
                state["notified"] = band
                text = f"현재 문맥 사용량 {percent}%. 다음 안전한 작업 경계에서 목표·제약·계획·가설·처리·결과·다음을 checkpoint에 저장. 80% 이상이면 새 작업보다 미저장 기록 정리를 우선. checkpoint --sync 후 같은 채팅에서 계속. 이 훅은 초기화·압축·재시작을 요청하지 않음. 지원 여부를 검증한 CLI 초기화는 별도 창 실행기만 담당."
        elif event == "PreCompact":
            if payload.get("permission_mode") not in ("plan", "planMode"):
                try:
                    core.sync(folder, checkpoint, binding)
                    state.pop("sync_error", None)
                except (
                    core.ContinuityError,
                    OSError,
                    ValueError,
                    subprocess.TimeoutExpired,
                ) as error:
                    state["sync_error"] = str(error)
            state["needs_restore"] = True
        elif event == "Stop":
            if payload.get("permission_mode") in ("plan", "planMode"):
                core.save(state_path, state)
                return {}
            if session not in binding.get("session_ids", []):
                core.save(state_path, state)
                return {}
            paths = checkpoint.get("watch_paths")
            if not paths:
                core.save(state_path, state)
                return {}
            actual = core.snapshot(binding["repo"], paths)
            fingerprint = core.digest(actual)
            changed_this_turn = state.get("turn_task_snapshot") not in (
                None,
                fingerprint,
            )
            stale = checkpoint.get("task_snapshot") != actual
            changed_this_turn = changed_this_turn or (
                stale
                and state.get("prompt_at") is not None
                and checkpoint.get("saved_at", 0) >= state["prompt_at"]
            )
            if (
                stale
                and changed_this_turn
                and not payload.get("stop_hook_active")
                and (
                    state.get("last_stop_task_snapshot") != fingerprint
                    or state.get("last_stop_checkpoint") != checkpoint.get("saved_at")
                )
            ):
                state["last_stop_task_snapshot"] = fingerprint
                state["last_stop_checkpoint"] = checkpoint.get("saved_at")
                core.save(state_path, state)
                return {
                    "decision": "block",
                    "reason": "이 요청 중 현재 과업에 등록된 파일이 변경됐습니다. 현재 과업의 변경이면 결과별 scope와 checkpoint를 갱신하세요. 다른 작업자의 변경이면 저장 없이 계속하세요. 사용자에게 확인이나 기록 작성을 요구하지 마세요.",
                }
        elif event == "SessionEnd":
            state["ended"] = True
        core.save(state_path, state)
        return response(event, text)


# cost: time O(n), heap O(n), stack O(1), io O(n + 1)
# vars: n = 처리하는 파일·응답 크기와 외부 명령 작업량
# basis: estimate
def main() -> int:
    try:
        host = sys.argv[1]
        if host not in ("claude", "codex"):
            raise core.ContinuityError("unknown host")
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise core.ContinuityError("hook input must be an object")
        print(
            json.dumps(
                handle(
                    host,
                    payload,
                    Path(os.environ.get("ISSUE_CONTINUITY_ROOT", core.ROOT)),
                ),
                ensure_ascii=False,
            )
        )
        return 0
    except (
        core.ContinuityError,
        OSError,
        ValueError,
        KeyError,
        IndexError,
        subprocess.TimeoutExpired,
    ) as error:
        print(f"continuity hook: {error}", file=sys.stderr)
        if (
            isinstance(locals().get("payload"), dict)
            and payload.get("hook_event_name") == "PreToolUse"
            and payload.get("tool_name") in {"Write", "Edit", "MultiEdit", "apply_patch"}
        ):
            print(
                json.dumps(
                    document_guard.deny(
                        "document guard failed; fix its configuration before writing documents"
                    )
                )
            )
        else:
            print("{}")
        # 안내 훅 실패가 Stop 재시도를 유발하지 않도록 종료하고 준비 검사는 별도로 실패 처리한다.
        return 0


# cost: time O(n), heap O(n), stack O(1), io O(1)
# vars: n = 최상위 지침 바이트
# basis: estimate
def _developer_rules() -> str:
    skill = Path(__file__).resolve().parents[1]
    candidates = (
        skill.parent / "developer-thinking/SKILL.md",
        skill.parents[1] / "code/developer-thinking/SKILL.md",
    )
    source = next((path for path in candidates if path.is_file()), None)
    if source is None:
        raise core.ContinuityError("developer-thinking entrypoint missing")
    text = source.read_text(encoding="utf-8")
    if not text.strip():
        raise core.ContinuityError("developer-thinking entrypoint empty")
    return f"개발 작업의 실행 지침. 원본 위치: {source.parent}. 아래 본문은 이미 제공됐으므로 재조회 없이 적용.\n{text}\n"


# cost: time O(b), heap O(b), stack O(1), io O(f)
# vars: b = 도구 출력·필수 원문 바이트, f = 선택 파일 수
# basis: estimate
def _rule_gate(host: str, payload: dict[str, Any], root: Path) -> dict[str, Any]:
    folder = find_task(root, payload, host)
    session = payload.get("session_id")
    event = payload.get("hook_event_name")
    if folder is None or not isinstance(session, str) or not session:
        return {}
    if event not in {
        "SessionStart",
        "PostCompact",
        "PreToolUse",
        "PostToolUse",
        "Stop",
    }:
        return {}
    skill = Path(__file__).resolve().parents[1]
    source = skill.parent / "developer-thinking/scripts/read_rules.py"
    if not source.is_file():
        source = skill.parents[1] / "code/developer-thinking/scripts/read_rules.py"
    spec = importlib.util.spec_from_file_location("developer_rule_reader", source)
    if spec is None or spec.loader is None:
        raise core.ContinuityError("developer rule reader unavailable")
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    state_path = folder / (
        "session-"
        + hashlib.sha256(
            (host + session + str(payload.get("agent_id") or "")).encode()
        ).hexdigest()[:20]
        + ".json"
    )
    with core.locked(folder):
        state = core.read(state_path)
        if event in {"PreToolUse", "PostToolUse"}:
            observed = state.setdefault("rule_tools", {}).setdefault(event, [])
            name = str(payload.get("tool_name", ""))
            if name not in observed:
                observed.append(name)
        is_query = False
        if event in {"SessionStart", "PostCompact"}:
            state["rule_seen"] = []
            state.pop("rule_scope", None)
            state.pop("rule_stop_notice", None)
        elif event in {"PreToolUse", "PostToolUse"}:
            repo = Path(core.read(folder / "binding.json")["repo"])
            scope = state.setdefault("rule_scope", {})
            is_query = reader.select_query(payload, scope)
            if not reader.is_rule_query(payload):
                reader.select_for_tool(payload, repo, scope)
        try:
            pending = reader.pending_rules(state)
        except (OSError, ValueError) as error:
            diagnostic = str(error)
            repeated = state.get("rule_error") == diagnostic
            state["rule_error"] = diagnostic
            core.save(state_path, state)
            return (
                {}
                if repeated
                else response(
                    event,
                    "필수 규칙 자동 조회 실패: "
                    + diagnostic
                    + ". 읽음·검사 통과로 처리하지 마세요. 해당 소유 원문을 직접 확인하거나 조회기를 복구한 뒤 영향 작업을 계속하세요. 문서 위치 검사는 유지됩니다.",
                )
            )
        state.pop("rule_error", None)
        if event == "PostToolUse":
            output = reader.collect_tool_output(payload)
            delivered = [digest for digest, _, body in pending if body in output]
            state["rule_seen"] = list(
                dict.fromkeys([*state.get("rule_seen", []), *delivered])
            )
            if delivered:
                state.pop("rule_stop_notice", None)
        core.save(state_path, state)
        command = f"python3 {shlex.quote(str(source))} --pending {shlex.quote(str(state_path))}"
        if event == "PreToolUse" and is_query:
            value = payload["tool_input"]
            if isinstance(value, str):
                value = {"command": value}
            key = "command" if "command" in value else "cmd"
            return {
                "hookSpecificOutput": {
                    "hookEventName": event,
                    "permissionDecision": "allow",
                    "updatedInput": {**value, key: command},
                }
            }
        if event not in {"PreToolUse", "Stop"} or not pending:
            return {}
        if event == "PreToolUse" and reader.is_rule_query(payload):
            return {}
        reason = f"필수 원문 {len(pending)}개가 아직 도구 결과로 전달되지 않았습니다. 먼저 `{command}`를 실행하세요. 출력은 자르거나 요약하지 말고, 남은 원문 안내가 있으면 같은 명령을 이어 실행하세요. 이미 전달된 원문은 자동 제외합니다. 원문을 적용한 뒤 원래 작업을 다시 실행할 수 있습니다. 사용자 승인이나 기록 작성 요청은 불필요합니다."
        if event == "PreToolUse":
            return document_guard.deny(reason)
        fingerprint = core.digest([row[0] for row in pending])
        if (
            payload.get("stop_hook_active")
            or state.get("rule_stop_notice") == fingerprint
        ):
            return {}
        state["rule_stop_notice"] = fingerprint
        core.save(state_path, state)
        return {"decision": "block", "reason": reason}


if __name__ == "__main__":
    raise SystemExit(main())
