"""기존 Claude status line 명령의 stdin·stdout·종료 코드를 보존하며 문맥 사용량을 세션 상태에 기록한다.

인자: --command-file 기존 statusLine 설정 JSON. stdin: Claude status line JSON
출력: 원래 status line 명령의 출력과 종료 코드. 기록 실패는 stderr 진단만
기록 위치: 작업 저장소 `.local/sessions/<세션 키>.json`의 meter(PostToolUse 훅이 80% 안내에 사용)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

import task as store


def record(payload: dict) -> None:
    cwd = payload.get("cwd") or (payload.get("workspace") or {}).get("current_dir")
    session = payload.get("session_id")
    repo = store.git_root(cwd)
    if repo is None or not isinstance(session, str) or not session:
        return
    percent = (payload.get("context_window") or {}).get("used_percentage")
    path = store.session_path(repo, session)
    with store.locked(repo):
        state = store.read(path)
        state["meter"] = {
            "percent": percent if type(percent) in (int, float) and 0 <= percent <= 100 else None,
            "at": time.time(),
        }
        store.save(path, state)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--command-file", required=True, type=Path)
    args = parser.parse_args()
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
        if isinstance(payload, dict):
            record(payload)
    except (ValueError, OSError, store.TaskError, subprocess.TimeoutExpired) as error:
        print(f"just do meter: {error}", file=sys.stderr)
    original = store.read(args.command_file) if args.command_file.is_file() else {}
    if not original.get("command"):
        return 0
    # 사용자가 이미 설정한 셸 명령만 그대로 실행한다.
    return subprocess.run(original["command"], shell=True, input=raw, text=True, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
