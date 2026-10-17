"""just do 훅의 이벤트별 동작을 실행한다.

인자: claude|codex, stdin 훅 이벤트 JSON
출력: stdout 훅 응답 JSON. 실패는 stderr 진단과 `{}`(git 저장소 안 편집 도구 PreToolUse는 거부)로 끝내고 종료 0

이벤트별 동작:
  SessionStart·PostCompact 뒤 첫 UserPromptSubmit: just-mode 진입 안내 한 줄, 연결 과업이면 결정 기록 꼬리와 이슈 URL
  UserPromptSubmit: 요청 시작 시점의 작업본·결정 기록 지문 저장
  PreToolUse: git 저장소 안 코드 편집 전 필수 규칙 원문 전달 확인(미전달이면 거부), 규칙 조회 명령을 미전달분 조회로 바꿈
  PostToolUse: 규칙 원문 전달 기록, 문맥 사용량 80% 안내, PR 머지 뒤 경력 기록 확인 안내
  PreCompact: 이번 요청 이후 결정 기록 갱신 여부 안내
  Stop: 규칙 미전달 편집 또는 파일 변경 뒤 결정 기록 누락이면 한 번 막음
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
from types import ModuleType
from typing import Any

import task as store

EDIT_TOOLS = frozenset({"Write", "Edit", "MultiEdit", "apply_patch"})
SHELL_PATCH = re.compile(r"\bapply_?patch\b")
PLAN_MODES = ("plan", "planMode")
USAGE_LIMIT = 80
METER_FRESH_SECONDS = 120
# gh pr merge, 또는 gh api의 PUT .../pulls/N/merge
PR_MERGE = re.compile(r"\bgh\s+pr\s+merge\b")
API_MERGE = re.compile(r"\bgh\s+api\b(?=[^\n;&|]*pulls/\d+/merge\b)(?=[^\n;&|]*(?:-X\s*|--method[\s=]+)PUT\b)")
EXIT_LINE = re.compile(r"(?:^|\n)\s*(?:Exit code|Process exited with code)[:\s]+(\d+)", re.I)


def response(event: str, text: str) -> dict[str, Any]:
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}} if text else {}


def deny(reason: str) -> dict[str, Any]:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}}


def tool_command(payload: dict[str, Any]) -> str:
    """Bash·exec_command 입력의 명령 문자열. Codex 배열 명령은 공백 결합"""
    value = payload.get("tool_input")
    if isinstance(value, dict):
        value = value.get("command", value.get("cmd"))
    if isinstance(value, list):
        value = " ".join(str(part) for part in value)
    return value if isinstance(value, str) else ""


def edit_request(payload: dict[str, Any]) -> dict[str, Any] | None:
    """구조화 편집 도구 또는 셸 apply_patch. 셸 패치는 apply_patch 도구 입력으로 바꿔 규칙 선택에 넘긴다."""
    if payload.get("tool_name") in EDIT_TOOLS:
        return payload
    command = tool_command(payload)
    if payload.get("tool_name") in {"Bash", "exec_command"} and SHELL_PATCH.search(command):
        return {**payload, "tool_name": "apply_patch", "tool_input": {"command": command}}
    return None


def entry_notice(repo: Path | None, session: str) -> str:
    """세션 시작·압축 뒤 안내. 한 줄 안내 + 연결 과업이면 이슈 URL과 결정 기록 마지막 줄들, 아니면 연결 명령과 최근 결정 기록 이름."""
    lines = [f"코드를 바꾸는 개발 일이면 {store.entry_skill()}를 읽고 그 순서로 진행한다."]
    if repo is None or not session:
        return lines[0]
    bound = store.binding(repo, session)
    if not bound:
        script = shlex.quote(str(Path(__file__).with_name("task.py")))
        branch = store.branch_task(repo)
        task = shlex.quote(branch) if branch else "<과업>"
        lines.append(f"과업 연결: `python3 {script} bind --session-id {session} --task {task} --issue <이슈 URL>`")
        recent = store.recent_tasks(repo)
        if recent:
            lines.append(f"최근 결정 기록({store.decisions_folder(repo)}): {', '.join(recent)}. 이어받을 일이면 그 과업 이름으로 연결한다.")
        return "\n".join(lines)
    log = store.decision_log(repo, bound["task"])
    lines.append(f"연결 과업: {bound['task']}" + (f", 이슈 {bound['issue']}" if bound.get("issue") else ""))
    rows = store.decision_rows(log)
    if rows:
        lines.append(f"결정 기록 {log} 마지막 {min(len(rows), store.TAIL_LINES)}줄:")
        lines += rows[-store.TAIL_LINES:]
    else:
        lines.append(f"결정 기록 {log} 없음. 단계 경계마다 한 줄씩 남긴다.")
    return "\n".join(lines)


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


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise store.TaskError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def merge_notice(payload: dict[str, Any]) -> str:
    """셸 PR 머지 성공 뒤 경력 원본 확인 안내 한 줄. hanger 스킬이 설치되지 않았으면 생략"""
    if payload.get("hook_event_name") != "PostToolUse":
        return ""
    command = tool_command(payload)
    if not (PR_MERGE.search(command) or API_MERGE.search(command)) or tool_failed(payload.get("tool_response")):
        return ""
    skill = store.skill_file(store.CAREER_NOTES)
    if skill is None:
        return ""
    return (
        "PR 머지 성공. 경력 원본에 남길 성과(내 PR, 동작·결과 변화, 검증 근거 있음)인지 판단하고, "
        f"남길 성과면 사실과 근거(PR 링크, 바뀐 동작, 검증)를 정리해 hanger 스킬({skill})에 경력 원본 기록을 요청한다."
    )


def handle(host: str, payload: dict[str, Any]) -> dict[str, Any]:
    event = payload.get("hook_event_name", "")
    session = payload.get("session_id") if isinstance(payload.get("session_id"), str) else ""
    repo = store.git_root(payload.get("cwd"))
    if event == "SessionStart":
        if repo is not None and session:
            reset_session(repo, session, payload)
        return response(event, entry_notice(repo, session))
    if repo is None or not session:
        return response(event, merge_notice(payload)) if event == "PostToolUse" else {}
    if event == "PreToolUse":
        return rule_gate(payload, repo, session)
    if event == "PostToolUse":
        rule_gate(payload, repo, session)
        return response(event, "\n".join(text for text in (usage_notice(repo, session), merge_notice(payload)) if text))
    if event == "UserPromptSubmit":
        return response(event, prompt_started(repo, session))
    if event == "PostCompact":
        reset_session(repo, session, payload)
        return {}
    if event == "PreCompact":
        return compact_check(repo, session)
    if event == "Stop":
        if payload.get("permission_mode") in PLAN_MODES:
            return {}
        return rule_gate(payload, repo, session) or decision_gate(payload, repo, session)
    return {}


def reset_session(repo: Path, session: str, payload: dict[str, Any]) -> None:
    """세션 시작·압축 뒤: 규칙 전달 기록 초기화, 사용량 안내 초기화, 압축 뒤면 다음 요청에 안내 재주입."""
    path = store.session_path(repo, session)
    with store.locked(repo):
        state = store.read(path)
        state["notified"] = False
        if payload.get("hook_event_name") == "PostCompact":
            state["reinject"] = True
        store.save(path, state)
        for rules in path.parent.glob(f"{path.stem}.*.rules.json"):
            rules.unlink(missing_ok=True)


def prompt_started(repo: Path, session: str) -> str:
    path = store.session_path(repo, session)
    with store.locked(repo):
        state = store.read(path)
        state.update({
            "session_id": session,
            "prompt_at": time.time(),
            "tree": store.tree_mark(repo),
            "decisions": store.decision_mark(repo, state.get("task")),
            "stop_blocked": False,
        })
        reinject = state.pop("reinject", False)
        stale = state.pop("compact_stale", False)
        store.save(path, state)
    if not reinject:
        return ""
    text = entry_notice(repo, session)
    if stale:
        text += "\n압축 전 이번 요청의 결정이 결정 기록에 없었다. 이어서 하기 전에 지금까지의 결정을 먼저 한 줄로 남긴다."
    return text


def usage_notice(repo: Path, session: str) -> str:
    path = store.session_path(repo, session)
    with store.locked(repo):
        state = store.read(path)
        meter = state.get("meter") or {}
        percent = meter.get("percent")
        fresh = time.time() - meter.get("at", 0) < METER_FRESH_SECONDS
        if not fresh or not isinstance(percent, (int, float)) or percent < USAGE_LIMIT or state.get("notified"):
            return ""
        state["notified"] = True
        store.save(path, state)
    return f"문맥 사용량 {percent}%. 결정 기록에 지금까지의 결정과 다음 할 일을 남긴 뒤 남은 범위는 새 서브에이전트에 인계한다."


def compact_check(repo: Path, session: str) -> dict[str, Any]:
    path = store.session_path(repo, session)
    with store.locked(repo):
        state = store.read(path)
        if "decisions" not in state:
            return {}
        stale = store.decision_mark(repo, state.get("task")) <= state["decisions"]
        state["compact_stale"] = stale
        store.save(path, state)
    if not stale:
        return {}
    return {"systemMessage": "이번 요청 이후 결정 기록에 새 줄이 없다. 압축 뒤 첫 요청에서 결정 기록을 먼저 갱신하도록 안내한다."}


def decision_gate(payload: dict[str, Any], repo: Path, session: str) -> dict[str, Any]:
    """이번 요청에서 파일이 바뀌었는데 결정 기록에 새 줄이 없으면 한 번 막는다."""
    if payload.get("stop_hook_active"):
        return {}
    path = store.session_path(repo, session)
    with store.locked(repo):
        state = store.read(path)
        if "tree" not in state or state.get("stop_blocked"):
            return {}
        changed = store.tree_mark(repo) != state["tree"]
        task = state.get("task")
        if not changed or store.decision_mark(repo, task) > state.get("decisions", 0):
            return {}
        state["stop_blocked"] = True
        store.save(path, state)
    logger = store.skill_file(store.DECISION_LOGGER)
    target = store.decision_log(repo, task or store.branch_task(repo) or "<과업>")
    command = f"bash {shlex.quote(str(logger))} {shlex.quote(str(target))} <phase> <decision> <why> <evidence> <result>" if logger else str(target)
    return {
        "decision": "block",
        "reason": f"이번 요청에서 파일이 바뀌었는데 결정 기록에 새 줄이 없다. `{command}`로 이번 단계의 결정을 한 줄 남긴 뒤 끝낸다.",
    }


def rule_reader() -> ModuleType:
    source = store.skill_file(store.RULE_READER)
    if source is None:
        raise store.TaskError("rule reader missing: " + "/".join(store.RULE_READER))
    return load_module(source, "rule_reader")


def rule_gate(payload: dict[str, Any], repo: Path, session: str) -> dict[str, Any]:
    """git 저장소 안 편집 전 필수 규칙 원문 전달 확인. 상태는 세션·서브에이전트마다 따로 둔다."""
    event = payload.get("hook_event_name")
    if event not in {"PreToolUse", "PostToolUse", "Stop"}:
        return {}
    edit = edit_request(payload)
    reader = rule_reader()
    state_path = store.rules_path(repo, session, str(payload.get("agent_id") or ""))
    with store.locked(repo):
        state = store.read(state_path)
        is_query = False
        if event in {"PreToolUse", "PostToolUse"}:
            scope = state.setdefault("rule_scope", {})
            is_query = reader.select_query(payload, scope)
            if edit is not None:
                reader.select_for_tool(edit, repo, scope)
        try:
            pending = reader.pending_rules(state)
        except (OSError, ValueError, TypeError) as error:
            diagnostic = str(error)
            repeated = state.get("rule_error") == diagnostic
            state["rule_error"] = diagnostic
            store.save(state_path, state)
            if repeated or event == "Stop":
                return {}
            return response(event, f"필수 규칙 자동 조회 실패: {diagnostic}. 읽음으로 처리하지 않는다. 해당 규칙 원문을 직접 읽거나 조회기를 고친 뒤 계속한다.")
        state.pop("rule_error", None)
        if event == "PostToolUse":
            output = reader.collect_tool_output(payload)
            delivered = [digest for digest, _, body in pending if body in output]
            state["rule_seen"] = list(dict.fromkeys([*state.get("rule_seen", []), *delivered]))
            if delivered:
                state.pop("rule_stop_notice", None)
        store.save(state_path, state)
    command = f"python3 {shlex.quote(str(Path(reader.__file__)))} --pending {shlex.quote(str(state_path))}"
    if event == "PreToolUse" and is_query:
        value = payload["tool_input"]
        if isinstance(value, str):
            value = {"command": value}
        key = "command" if "command" in value else "cmd"
        return {"hookSpecificOutput": {"hookEventName": event, "permissionDecision": "allow", "updatedInput": {**value, key: command}}}
    if event == "PostToolUse" or not pending or (event == "PreToolUse" and edit is None):
        return {}
    reason = f"필수 규칙 원문 {len(pending)}개가 아직 전달되지 않았다. 먼저 `{command}`를 실행한다. 출력은 자르거나 요약하지 않고, 남은 원문 안내가 있으면 같은 명령을 이어 실행한다. 원문을 적용한 뒤 원래 작업을 다시 실행한다."
    if event == "PreToolUse":
        return deny(reason)
    fingerprint = store.session_key(json.dumps([row[0] for row in pending]))
    if payload.get("stop_hook_active") or state.get("rule_stop_notice") == fingerprint:
        return {}
    with store.locked(repo):
        state = store.read(state_path)
        state["rule_stop_notice"] = fingerprint
        store.save(state_path, state)
    return {"decision": "block", "reason": reason}


def main() -> int:
    payload: Any = None
    try:
        host = sys.argv[1] if len(sys.argv) == 2 else ""
        if host not in {"claude", "codex"}:
            raise store.TaskError("unknown host")
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise store.TaskError("hook input must be an object")
        print(json.dumps(handle(host, payload), ensure_ascii=False))
        return 0
    except (store.TaskError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        print(f"just do hook: {error}", file=sys.stderr)
        if isinstance(payload, dict) and payload.get("hook_event_name") == "PreToolUse" and edit_request(payload) is not None and store.git_root(payload.get("cwd")) is not None:
            print(json.dumps(deny(f"just do rule gate failed: {error}; fix the hook before editing")))
        else:
            print("{}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
