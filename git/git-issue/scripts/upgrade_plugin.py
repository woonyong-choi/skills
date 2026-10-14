"""기존 훅 진입점을 유지하면서 공식 CLI로 플러그인을 갱신한다.

인자: codex|claude
출력: 공식 설치 결과와 보존한 호환 경로 JSON, 실패 stderr와 종료 2
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


# cost: time O(n), heap O(n), stack O(1), io O(v)
# vars: n = hook definitions bytes, v = retained versions
# basis: estimate
def upgrade(host: str) -> dict:
    if host not in {"claude", "codex"}:
        raise ValueError("expected claude or codex")
    home = Path.home()
    launcher = home / ".config/skills/work-continuity.py"
    if not launcher.is_file():
        raise ValueError("install the canonical git-issue skill and stable launcher first")
    cache = home / (".claude" if host == "claude" else ".codex") / "plugins/cache/woon-skills/work-continuity"
    definitions = {path: path.read_bytes() for path in cache.glob("*/hooks/*.json")}
    command = ["codex", "plugin", "add", "work-continuity@woon-skills", "--json"] if host == "codex" else ["claude", "plugin", "update", "work-continuity@woon-skills", "--scope", "user", "--json"]
    result = None
    retained = []
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    finally:
        for path, data in definitions.items():
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            entry = path.parent.parent / "scripts/continuity_hook.py"
            if not entry.exists():
                entry.parent.mkdir(parents=True, exist_ok=True)
                entry.symlink_to(launcher)
                retained.append(str(entry))
    if result.returncode:
        raise ValueError(result.stderr or result.stdout)
    return {"install": json.loads(result.stdout), "retained_entrypoints": retained, "hook_trust": "review new definitions in the host; never bypass trust"}


# cost: time O(n), heap O(n), stack O(1), io O(v)
# vars: n = hook definitions bytes, v = retained versions
# basis: estimate
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", choices=("claude", "codex"))
    args = parser.parse_args()
    try:
        print(json.dumps(upgrade(args.host), ensure_ascii=False))
        return 0
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
