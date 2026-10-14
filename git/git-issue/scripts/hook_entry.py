"""캐시 교체와 독립된 훅 진입점.

인자: claude|codex
출력: 실제 훅 JSON과 종료 코드
"""

from __future__ import annotations

import fcntl
import json
from pathlib import Path
import subprocess
import sys


# cost: time O(n), heap O(n), stack O(1), io O(1)
# vars: n = hook input and output bytes
# basis: estimate
def main() -> int:
    payload = sys.stdin.read()
    configuration = Path(__file__).resolve().parent
    host = sys.argv[1] if len(sys.argv) == 2 else ""
    try:
        if host not in {"claude", "codex"}:
            raise ValueError("unknown hook host")
        home = configuration.parent.parent
        target = home / (".claude" if host == "claude" else ".codex") / "skills/git-issue/scripts/continuity_hook.py"
        with (configuration / "runtime.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_SH)
            result = subprocess.run([sys.executable, str(target), host], input=payload, text=True, capture_output=True, timeout=25)
        if result.returncode or not result.stdout.strip():
            raise ValueError("installed hook runtime did not return a result")
        json.loads(result.stdout)
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        return 0
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"Work Continuity unavailable: {error}", file=sys.stderr)
        try:
            request = json.loads(payload)
            event = request.get("hook_event_name")
            is_file_write = request.get("tool_name") in {"Write", "Edit", "MultiEdit", "apply_patch"}
        except (ValueError, AttributeError):
            event = None
            is_file_write = False
        failure = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "Work Continuity document guard unavailable; repair installation before writing"}} if event == "PreToolUse" and is_file_write else {}
        print(json.dumps(failure))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
