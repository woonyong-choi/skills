"""스킬 설치본 교체와 독립된 just do 훅 진입점. 설치기가 `~/.config/skills/just-do.py`로 복사한다.

인자: claude|codex, stdin 훅 이벤트 JSON
출력: 설치된 just-mode 훅(`~/.<host>/skills/just-mode/scripts/hooks/hook.py`)의 응답 JSON.
런타임이 없거나 실패·시간 초과면 stderr 진단과 `{}`, git 저장소 안 편집 도구 PreToolUse는 복구 명령과 함께 거부
"""

from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time


RUNTIME = "skills/just-mode/scripts/hooks/hook.py"
FALLBACK_REPAIR = "python3 tools/skill-sync/scripts/install.py in the skills source repo"
# hooks/{host}.json의 이벤트별 timeout(초). 시험이 두 파일과 같은지 검사한다.
HOOK_TIMEOUTS = {
    host: {"SessionStart": 5, "UserPromptSubmit": 5, "PreToolUse": 5, "PostToolUse": 5, "PreCompact": 5, "PostCompact": 5, "Stop": 5}
    for host in ("claude", "codex")
}
# 진입점 기동·출력에 남기는 시간, 런타임 내부 마감과 런타임 종료 사이 여유(초)
START_MARGIN = 1.0
DEADLINE_MARGIN = 0.5
# task.DEADLINE_ENV와 같은 이름. 진입점은 런타임 모듈을 불러오지 않는다.
DEADLINE_ENV = "JUST_DO_DEADLINE"
SHELL_PATCH = re.compile(r"\bapply_?patch\b")
FILE_TOOLS = {"Write", "Edit", "MultiEdit", "apply_patch"}


def budget(host: str, event: object) -> tuple[float, float]:
    """(런타임 대기 상한, 런타임 내부 마감까지 남은 시간). 호스트가 훅을 끊기 전에 진입점이 응답한다."""
    limits = HOOK_TIMEOUTS.get(host, {})
    limit = limits.get(event) if isinstance(event, str) else None
    limit = limit or min(limits.values(), default=5)
    child = limit - START_MARGIN
    return child, child - DEADLINE_MARGIN


def guarded_edit(request: dict) -> bool:
    """런타임 없이 판정하는 거부 대상: 구조화 편집 도구, apply_patch를 부르는 셸 명령."""
    if request.get("tool_name") in FILE_TOOLS:
        return True
    value = request.get("tool_input")
    command = value.get("command", value.get("cmd")) if isinstance(value, dict) else value
    if isinstance(command, list):
        command = " ".join(str(part) for part in command)
    return request.get("tool_name") in {"Bash", "exec_command"} and isinstance(command, str) and bool(SHELL_PATCH.search(command))


def inside_git(cwd: object) -> bool:
    """규칙 훅의 적용 범위(git 저장소 안). 판정할 수 없으면 안전 쪽(안)으로 본다."""
    if not isinstance(cwd, str) or not cwd:
        return False
    try:
        done = subprocess.run(["git", "-C", cwd, "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True, timeout=1)
    except subprocess.TimeoutExpired:
        return True
    except OSError:
        return False
    return done.stdout.strip() == "true"


def repair_command(configuration: Path) -> str:
    """install.py가 기록한 원본 포인터(source)로 만든 절대 경로 복구 명령. 포인터가 무효면 상대 안내."""
    try:
        source = Path((configuration / "source").read_text(encoding="utf-8").strip()).expanduser()
    except (OSError, UnicodeDecodeError):
        return FALLBACK_REPAIR
    installer = source / "tools/skill-sync/scripts/install.py"
    return f"python3 {shlex.quote(str(installer))}" if source.is_absolute() and installer.is_file() else FALLBACK_REPAIR


def main() -> int:
    started = time.time()
    payload = sys.stdin.read()
    configuration = Path(__file__).resolve().parent
    host = sys.argv[1] if len(sys.argv) == 2 else ""
    try:
        request = json.loads(payload)
    except ValueError:
        request = None
    request = request if isinstance(request, dict) else {}
    wait, deadline = budget(host, request.get("hook_event_name"))
    try:
        if host not in {"claude", "codex"}:
            raise ValueError("unknown hook host")
        home = configuration.parent.parent
        target = home / f".{host}" / RUNTIME
        with (configuration / "runtime.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_SH)
            remaining = wait - (time.time() - started)
            environment = {**os.environ, DEADLINE_ENV: str(started + deadline)}
            result = subprocess.run([sys.executable, str(target), host], input=payload, text=True, capture_output=True, timeout=max(remaining, 0.1), env=environment)
        if result.returncode or not result.stdout.strip():
            raise ValueError("installed hook runtime did not return a result")
        json.loads(result.stdout)
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        return 0
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"just do hook unavailable: {error}", file=sys.stderr)
        failure = {}
        if request.get("hook_event_name") == "PreToolUse" and guarded_edit(request) and inside_git(request.get("cwd")):
            reason = f"just do rule gate unavailable; repair: run {repair_command(configuration)} (skill-sync install), then retry"
            failure = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}}
        print(json.dumps(failure))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
