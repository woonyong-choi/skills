"""기존 status line 명령의 stdin·stdout·종료 코드를 보존하며 사용량 기록.

인자: --command-file 기존 statusLine 설정 JSON. stdin: Claude status line JSON.
인자: 명령별 --help 또는 위 설명
출력: stdout JSON 또는 원래 status line, 실패 stderr와 종료 코드
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import continuity as core
from continuity_hook import find_task, managed_window


# cost: time O(n), heap O(n), stack O(1), io O(n + 1)
# vars: n = 처리하는 파일·응답 크기와 외부 명령 작업량
# basis: estimate
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command-file", required=True, type=Path)
    args = parser.parse_args()
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
        payload["cwd"] = payload.get("cwd") or payload.get("workspace", {}).get(
            "current_dir"
        )
        root = core.default_root()
        folder = find_task(root, payload, "claude")
        percent = payload.get("context_window", {}).get("used_percentage")
        managed = managed_window(root, "claude")
        if os.environ.get("ISSUE_CONTINUITY_WINDOW") and not managed:
            raise core.ContinuityError("managed window record unverified")
        # 관리 창은 task가 바뀌어도 같은 window home의 meter를 읽는다.
        target = managed[0] if managed else folder
        if target:
            with core.locked(target):
                core.save(
                    target / "meter.json",
                    {
                        "session_id": payload.get("session_id"),
                        "task": folder.name if folder else None,
                        "percent": percent
                        if type(percent) in (int, float) and 0 <= percent <= 100
                        else None,
                        "at": time.time(),
                    },
                )
    except (
        ValueError,
        OSError,
        core.ContinuityError,
        subprocess.TimeoutExpired,
    ) as error:
        print(f"continuity meter: {error}", file=sys.stderr)
    original = core.read(args.command_file)
    if not original.get("command"):
        return 0
    # 사용자가 이미 설정한 셸 명령만 그대로 실행한다.
    return subprocess.run(
        original["command"], shell=True, input=raw, text=True, check=False
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
