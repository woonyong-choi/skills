"""제품별 훅 JSON 어댑터. 인자: claude|codex, stdin 이벤트, stdout 훅 JSON.

사용량은 Claude status line 또는 명시적인 호스트 이벤트만 사용한다.
인자: 명령별 --help 또는 위 설명
출력: stdout JSON 또는 원래 status line, 실패 stderr와 종료 코드
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
from typing import Any

import continuity as core
import project_context
import document_guard

EDIT_TOOLS = frozenset({"Write", "Edit", "MultiEdit", "apply_patch"})


def session_tasks(root: Path, session: object) -> list[Path]:
    """session이 명시 bind된 task 폴더들. session이 없으면 빈 목록"""
    if not isinstance(session, str) or not session:
        return []
    return [
        path.parent
        for path in sorted(root.glob("*/binding.json"))
        if session in core.read(path).get("session_ids", [])
    ]


def hinted_task(root: Path, repo: str) -> Path | None:
    """ISSUE_CONTINUITY_TASK 힌트. 명시 session bind를 덮지 않으며 작업본 일치만 검증"""
    explicit = os.environ.get("ISSUE_CONTINUITY_TASK")
    if not explicit:
        return None
    candidate = core.task_path(root, explicit)
    return (
        candidate if core.read(candidate / "binding.json").get("repo") == repo else None
    )


def find_task(root: Path, payload: dict[str, Any]) -> Path | None:
    """session 명시 bind가 최우선이다. 둘 이상이면 선택하지 않고, 미등록일 때만 검증된 fallback을 쓴다."""
    bound = session_tasks(root, payload.get("session_id"))
    if bound:
        return bound[0] if len(bound) == 1 else None
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


def response(event: str, text: str) -> dict[str, Any]:
    return (
        {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}
        if text
        else {}
    )


CHECKPOINT_COMMAND = re.compile(r"continuity\.py\b[^\n;&|]*?\scheckpoint\b")


def tool_command(payload: dict[str, Any]) -> str:
    """Bash·exec_command·shell 입력의 명령 문자열. Codex 배열 명령은 공백 결합"""
    value = payload.get("tool_input")
    if isinstance(value, dict):
        value = value.get("command", value.get("cmd"))
    if isinstance(value, list):
        value = " ".join(str(part) for part in value)
    return value if isinstance(value, str) else ""


# bind 전 요청 임시 파일 보관 기한. 같은 턴의 bind 승계에만 쓰므로 하루 지난 파일은 다시 쓰일 일이 없다.
PROMPT_HOLD_SECONDS = 24 * 60 * 60


def pending_prompt_path(root: Path, host: str, session: str) -> Path:
    """bind 전 요청의 비공개 임시 보관 위치. 세션당 최신 하나"""
    return root / ".prompts" / (
        hashlib.sha256((host + session).encode()).hexdigest()[:20] + ".json"
    )


def hold_prompt(root: Path, host: str, payload: dict[str, Any]) -> None:
    """명시 bind 전 요청의 비공개 임시 보관. 같은 턴의 bind 뒤 원래 요청으로 승계"""
    prompt, session = payload.get("prompt"), payload.get("session_id")
    if (
        payload.get("hook_event_name") != "UserPromptSubmit"
        or not isinstance(prompt, str)
        or not prompt
        or not isinstance(session, str)
        or not session
        or not _in_git(payload.get("cwd"))
    ):
        return
    top = core.run(["git", "rev-parse", "--show-toplevel"], cwd=payload["cwd"]).strip()
    if not core.private_problem(root, top):
        prune_prompts(root, time.time())
        core.save(
            pending_prompt_path(root, host, session),
            {"text": core.clip(prompt, core.ORIGINAL_LIMIT)},
        )


def prune_prompts(root: Path, now: float) -> None:
    """보관 기한이 지난 bind 전 요청 파일 삭제. 세션 종료를 받지 못한 세션의 파일 정리"""
    for path in (root / ".prompts").glob("*.json"):
        try:
            if now - path.stat().st_mtime > PROMPT_HOLD_SECONDS:
                path.unlink()
        except FileNotFoundError:
            continue  # 다른 훅이 먼저 지움


def drop_prompt(root: Path, host: str, payload: dict[str, Any]) -> None:
    """세션 종료 때 그 세션의 bind 전 요청 파일 삭제. bind하지 않은 세션의 요청은 승계할 곳이 없다"""
    session = payload.get("session_id")
    if isinstance(session, str) and session:
        pending_prompt_path(root, host, session).unlink(missing_ok=True)


def persisted_notice(folder: Path, state: dict[str, Any]) -> str:
    """실제 checkpoint 파일 대조 결과 안내. 같은 상태면 같은 문장(시각·순서 변동 없음)"""
    if not core.read(folder / "checkpoint.json"):
        return ""
    problems = []
    try:
        core.verify_checkpoint(folder, synced=True)
    except core.ContinuityError as error:
        problems.append(str(error))
    if state.get("sync_error"):
        problems.append("pre-compact: " + state["sync_error"])
    return (
        " 저장 상태 대조 실패: "
        + "; ".join(problems)
        + ". 저장됨으로 간주 금지, checkpoint --sync 재실행 또는 실패 보고."
        if problems
        else ""
    )


def context(folder: Path, binding: dict[str, Any]) -> str:
    script = shlex.quote(str(Path(__file__).with_name("continuity.py")))
    command = f"python3 {script} --root {shlex.quote(str(folder.parent))} restore --task {folder.name}"
    return f"연결: {binding['url']}. 같은 과업이면 읽기 전용 `{command}`로 기록과 실제 작업본 대조. 독립 결과는 git-issue의 과업 연결 규칙으로 전환. 기록은 실행 권한이 아님. 실행 기록은 {folder}의 기존 파일 갱신."


# gh pr merge, 또는 gh api의 PUT .../pulls/N/merge
PR_MERGE = re.compile(r"\bgh\s+pr\s+merge\b")
API_MERGE = re.compile(r"\bgh\s+api\b(?=[^\n;&|]*pulls/\d+/merge\b)(?=[^\n;&|]*(?:-X\s*|--method[\s=]+)PUT\b)")
EXIT_LINE = re.compile(r"(?:^|\n)\s*(?:Exit code|Process exited with code)[:\s]+(\d+)", re.I)


# cost: time O(b), heap O(1), stack O(d)
# vars: b = 도구 응답 바이트, d = 응답 중첩 깊이
# basis: estimate
def tool_failed(value: Any) -> bool:
    """도구 응답의 실패 표시: 0 아닌 종료 코드, 오류·중단 표시, 'Exit code: N' 줄"""
    if isinstance(value, dict):
        for key in ("exit_code", "exitCode", "returncode", "return_code"):
            if isinstance(value.get(key), int) and value[key] != 0:
                return True
        if value.get("is_error") or value.get("isError") or value.get("interrupted"):
            return True
        return any(tool_failed(child) for child in value.values() if isinstance(child, (dict, str)))
    if isinstance(value, str):
        match = EXIT_LINE.search(value)
        return bool(match and match.group(1) != "0")
    return False


# cost: time O(1), heap O(1), stack O(1), io O(2)
# vars: 없음
# basis: estimate
def _skill_script(folder: str, name: str) -> Path | None:
    """설치본(스킬 폴더 나란히) 또는 원본 저장소(docs/)의 스킬 스크립트"""
    skill = Path(__file__).resolve().parents[1]
    for candidate in (skill.parent / folder / "scripts" / name, skill.parents[1] / "docs" / folder / "scripts" / name):
        if candidate.is_file():
            return candidate
    return None


# cost: time O(1), heap O(1), stack O(1), io O(1)
# vars: 없음
# basis: estimate
def _mode(name: str) -> str:
    path = project_context.config_directory() / name
    mode = json.loads(path.read_text(encoding="utf-8")).get("mode", "normal") if path.is_file() else "normal"
    return mode if mode in ("normal", "bypass") else "normal"


# cost: time O(b), heap O(1), stack O(d), io O(6)
# vars: b = 명령·도구 응답 바이트, d = 응답 중첩 깊이
# basis: estimate
def merge_notice(payload: dict[str, Any]) -> str:
    """세션 안 PR 머지 성공 뒤 안내 하나: career-record 기록 판단 → journal 판단 기록 순서. 스킬·Vault가 없는 쪽은 생략"""
    if payload.get("hook_event_name") != "PostToolUse":
        return ""
    command = tool_command(payload)
    if not (PR_MERGE.search(command) or API_MERGE.search(command)) or tool_failed(payload.get("tool_response")):
        return ""
    try:
        vault = project_context.resolve_vault()
    except (project_context.ContextError, OSError, ValueError):
        return ""
    parts = []
    record = _skill_script("career-record", "record.py")
    try:
        if record and (vault / "career").is_dir():
            script = shlex.quote(str(record))
            parts.append(
                f"1. career-record(모드 {_mode('career-record.json')}): 머지 뒤 기록 절 적용. "
                f"`gh pr view <번호> --json author,title,files,url | python3 {script} screen - --user <내 계정>`가 skip이면 묻지 않고 다음. "
                "기록 조건 세 가지(사용자 계정 PR, 동작·결과 변화, 검증 있음) 중 하나라도 아니면 묻지 않고 다음. "
                f"해당하면 `python3 {script} locate --remote <저장소 원격> --author <PR 작성자>`로 위치 → 같은 상황·행동 줄이면 merge, 아니면 add(--pr <PR 주소>). "
                f"끝나면 `python3 {script} stamp`."
            )
        journal = _skill_script("repo-docs-journal", "journal.py")
        if journal:
            script = shlex.quote(str(journal))
            parts.append(
                f"{len(parts) + 1}. repo-docs-journal(모드 {_mode('journal.json')}): PR 본문·연결 이슈·PR 댓글·이 PR로 이어진 대화에서 기록 기준 세 칸(대안 인용, 가정 인용, 구조 목록 이름) 확인 → "
                f"근거 원문을 표준 입력으로 `python3 {script} screen --source - --alternative <인용> --assumption <인용> --structure <목록 이름>`. 미충족이면 이유 한 줄로 끝."
            )
    except (OSError, ValueError):
        return ""
    return "PR 머지 성공. 아래 순서로 처리:\n" + "\n".join(parts) if parts else ""


# cost: time O(n), heap O(n), stack O(1), io O(n + 1)
# vars: n = 처리하는 파일·응답 크기와 외부 명령 작업량
# basis: estimate
def handle(host: str, payload: dict[str, Any], root: Path) -> dict[str, Any]:
    result = _handle(host, payload, root)
    notice = merge_notice(payload)
    if not notice or (result.get("hookSpecificOutput") or {}).get("permissionDecision"):
        return result
    output = result.setdefault("hookSpecificOutput", {"hookEventName": "PostToolUse"})
    output["additionalContext"] = (output.get("additionalContext", "") + "\n" + notice).lstrip("\n")
    return result


# cost: time O(n), heap O(n), stack O(1), io O(n + 1)
# vars: n = 처리하는 파일·응답 크기와 외부 명령 작업량
# basis: estimate
def _handle(host: str, payload: dict[str, Any], root: Path) -> dict[str, Any]:
    if payload.get("hook_event_name") == "PreToolUse":
        folder = find_task(root, payload)
        project = Path(core.read(folder / "binding.json")["repo"]) if folder else None
        guarded = document_guard.check_tool(payload, project)
        return guarded or _rule_gate(host, payload, root)
    guarded = _rule_gate(host, payload, root)
    if guarded:
        return guarded
    result = handle_continuity(host, payload, root)
    event = payload.get("hook_event_name", "")
    if event != "SessionStart" or not _in_git(payload.get("cwd")):
        return result
    context_result = project_context.inspect_project(Path(payload["cwd"]))
    if context_result["ready"]:
        notice = f"작업 전 필수 맥락: {context_result['index']}. 필요한 자료만 조회하고 실제 읽은 경로·버전을 기존 로컬 작업 기록에 반영. 검사 성공은 읽음 증거가 아님. 신규 문서 쓰기 전 project_context.py --write 검사 필수."
    else:
        error = context_result["error"]
        notice = f"프로젝트 맥락 미확인: {error}{document_guard.setup_hint(error, payload['cwd'])}. 문서 쓰기는 거부됨. 위 오류의 안내 절차로 해결, 임의 문서 위치 대체 금지. 단순 질문 제외."
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
    folder = find_task(root, payload)
    if event == "SessionEnd":
        drop_prompt(root, host, payload)
    if folder is None:
        hold_prompt(root, host, payload)
        if event in ("SessionStart", "UserPromptSubmit") and _in_git(payload.get("cwd")):
            if len(session_tasks(root, payload.get("session_id"))) > 1:
                return response(
                    event,
                    "현재 session이 여러 task에 연결되어 자동 선택하지 않습니다. 현재 과업의 task 하나만 남기도록 기록을 확인하세요. 기록은 지우지 말고 다른 task로 임의 진행하지 마세요.",
                )
            return response(
                event,
                f"개발 작업은 developer-thinking 적용, git-issue 과업 연결로 bind --session-id {payload.get('session_id', '현재채팅ID')}. 단순 질의응답 제외.",
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
        origin = {"host": host, "session_id": session}
        explicit = session in binding.get("session_ids", [])
        pending_prompt = pending_prompt_path(root, host, session)
        if explicit and pending_prompt.is_file():
            earlier = core.read(pending_prompt).get("text")
            if isinstance(earlier, str) and earlier:
                core.remember(folder, binding["repo"], prompt=earlier, origin=origin)
                state["prompt_captured"] = True
                state["prompt_at"] = time.time_ns()
            pending_prompt.unlink()
        if event == "SessionStart":
            state.update(
                {
                    "notified": 0,
                    "needs_restore": False,
                    "start_source": payload.get("source", "unknown"),
                }
            )
            text = (
                "개발 작업은 developer-thinking 현재 단계의 필수 원문 확인. "
                + context(folder, binding)
                + persisted_notice(folder, state)
            )
        elif event == "UserPromptSubmit":
            state["prompt_at"] = time.time_ns()
            prompt = payload.get("prompt")
            state["prompt_captured"] = isinstance(prompt, str) and bool(prompt)
            if not explicit:
                hold_prompt(root, host, payload)  # 저장소 추정 연결: bind 전까지 과업 기록과 분리
            elif state["prompt_captured"]:
                core.remember(folder, binding["repo"], prompt=prompt, origin=origin)
            paths = checkpoint.get("watch_paths")
            state["turn_task_snapshot"] = (
                core.digest(core.snapshot(binding["repo"], paths)) if paths else None
            )
            needs_restore = state.pop("needs_restore", False)
            if needs_restore or not checkpoint:
                text = (_developer_rules() if needs_restore else "") + context(
                    folder, binding
                )
                if needs_restore:
                    text += persisted_notice(folder, state)
            else:
                text = f"현재 연결: {folder.name}, {binding['url']}. developer-thinking의 현재 단계 적용. git-issue의 과업 판정에 따라 goal 유지·scope.outcomes 대조. 독립 결과 전환은 기존 기록 저장 후 bind --session-id {session} --from-task {folder.name}. 작업 경계는 checkpoint --sync, 착수·재개·단계 전환만 --status 진행|검토|보류. 단순 질문은 추가 기록 불필요."
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
            command = tool_command(payload)
            if CHECKPOINT_COMMAND.search(command):
                # 명령 실행·출력은 저장 주장일 뿐, Stop에서 실제 파일과 대조
                state["checkpoint_claim"] = {
                    "at": time.time_ns(),
                    "sync": "--sync" in command.split(),
                }
            meter = core.read(folder / "meter.json")
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
                text = f"현재 문맥 사용량 {percent}%. 다음 안전한 작업 경계에서 목표·제약·계획·가설·처리·결과·다음을 checkpoint에 저장. 80% 이상이면 새 작업보다 미저장 기록 정리를 우선. checkpoint --sync 후 남은 범위는 새 서브에이전트에 인계. 이 훅은 초기화·압축·재시작을 요청하지 않음."
        elif event == "PreCompact":
            if payload.get("permission_mode") not in ("plan", "planMode"):
                try:
                    core.sync(folder, checkpoint, binding)
                    core.verify_checkpoint(folder, synced=True)
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
            if explicit:
                record_exchange(host, folder, binding, payload, state, origin)
            if payload.get("permission_mode") in ("plan", "planMode"):
                core.save(state_path, state)
                return {}
            if not explicit:
                core.save(state_path, state)
                return {}
            claim = state.get("checkpoint_claim") or {}
            if claim.get("at", 0) >= state.get("prompt_at", 0) > 0:
                try:
                    core.verify_checkpoint(
                        folder, synced=claim.get("sync", False), since=state["prompt_at"]
                    )
                    problem = ""
                except core.ContinuityError as error:
                    problem = str(error)
                mark = core.digest([claim, problem])
                if (
                    problem
                    and not payload.get("stop_hook_active")
                    and state.get("last_claim_block") != mark
                ):
                    state["last_claim_block"] = mark
                    core.save(state_path, state)
                    return {
                        "decision": "block",
                        "reason": f"이 요청에서 checkpoint를 실행했지만 실제 저장 상태 대조 실패: {problem}. 저장·동기화 완료로 보고하지 말고 checkpoint를 다시 실행하거나 실패와 미전송 상태를 그대로 보고하세요.",
                    }
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
            try:
                core.verify_checkpoint(folder)
                state["end_check"] = "verified"
            except core.ContinuityError as error:
                state["end_check"] = str(error)
        core.save(state_path, state)
        return response(event, text)


# cost: time O(t), heap O(t), stack O(1), io 2
# vars: t = transcript 끝부분 바이트
# basis: estimate
def record_exchange(
    host: str,
    folder: Path,
    binding: dict[str, Any],
    payload: dict[str, Any],
    state: dict[str, Any],
    origin: dict[str, Any],
) -> None:
    """마지막 요청·응답의 비공개 저장. payload의 last_assistant_message 우선, 없거나 요청 미수신이면 호스트 어댑터의 transcript"""
    reply = payload.get("last_assistant_message")
    prompt = None
    if not isinstance(reply, str) or not state.get("prompt_captured"):
        try:
            prompt, logged = core.last_turn(core.HOSTS[host].locate(payload), host)
        except (core.ContinuityError, OSError):
            prompt, logged = None, None  # 경로 없음·형식 불명은 있는 값만 저장
        reply = reply if isinstance(reply, str) else logged
        if state.get("prompt_captured"):
            prompt = None
    if prompt:
        core.remember(folder, binding["repo"], prompt=prompt, origin=origin)
    if isinstance(reply, str):
        core.remember(folder, binding["repo"], reply=reply, origin=origin)


# cost: time O(n), heap O(n), stack O(1), io O(n + 1)
# vars: n = 처리하는 파일·응답 크기와 외부 명령 작업량
# basis: estimate
def main() -> int:
    try:
        host = sys.argv[1]
        if host not in core.HOSTS:
            raise core.ContinuityError("unknown host")
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise core.ContinuityError("hook input must be an object")
        print(
            json.dumps(
                handle(
                    host,
                    payload,
                    core.default_root(),
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
        print(f"Developer Thinking hook: {error}", file=sys.stderr)
        if (
            isinstance(locals().get("payload"), dict)
            and payload.get("hook_event_name") == "PreToolUse"
            and document_guard.guarded_write(payload)
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
def _in_git(cwd: object) -> bool:
    if not isinstance(cwd, str) or not cwd:
        return False
    try:
        done = subprocess.run(["git", "-C", cwd, "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True, timeout=project_context.time_budget(2))
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.stdout.strip() == "true"


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
    folder = find_task(root, payload)
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
    try:
        # 셸 apply_patch는 구조화 편집과 같은 필수 원문 확인. 판정 정본: document_guard.shell_patch
        edit = payload if payload.get("tool_name") in EDIT_TOOLS else document_guard.shell_patch(payload)
    except ValueError:
        edit = None  # 잘못된 셸은 document_guard가 거부
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
            # 읽기·실행 명령은 조회 강제 대상이 아니다. 실제 편집(셸 apply_patch 포함)만 규칙 하한을 선택한다.
            if edit is not None:
                reader.select_for_tool(edit, repo, scope)
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
        if event == "PreToolUse" and edit is None:
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
