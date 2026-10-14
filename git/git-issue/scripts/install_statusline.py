"""Claude status line에 사용량 기록 연결. 기존 명령 보존.
인자: install|remove, --home 홈 경로 (기본 사용자 홈)
출력: 변경 여부, 실패 stderr·2
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shlex
import sys

import continuity as core


# cost: time O(n), heap O(n), stack O(1), io 5
# vars: n = 설정 파일 바이트
# basis: estimate
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["install", "remove"])
    parser.add_argument("--home", type=Path, default=Path.home())
    args = parser.parse_args()
    settings_path = args.home / ".claude/settings.json"
    saved_path = (
        args.home
        / "workspace/woon/.local/orchestration/issue-continuity/statusline-original.json"
    )
    script = Path(__file__).with_name("continuity_statusline.py").resolve()
    wrapper = {
        "type": "command",
        "command": f"python3 {shlex.quote(str(script))} --command-file {shlex.quote(str(saved_path))}",
    }
    try:
        with core.locked(saved_path.parent):
            settings = core.read(settings_path)
            original = settings.get("statusLine")
            if args.action == "install":
                if original == wrapper:
                    print("already installed")
                    return 0
                if saved_path.exists():
                    raise core.ContinuityError(
                        "saved status line exists; inspect changed settings before installing"
                    )
                if original and original.get("type") != "command":
                    raise core.ContinuityError("unsupported existing status line type")
                core.save(saved_path, original or {})
                settings["statusLine"] = wrapper
            else:
                if original != wrapper:
                    raise core.ContinuityError(
                        "status line changed; refusing to overwrite"
                    )
                restored = core.read(saved_path)
                if restored:
                    settings["statusLine"] = restored
                else:
                    settings.pop("statusLine", None)
            core.save(settings_path, settings)
        print(args.action + " complete; existing hooks preserved")
        return 0
    except (core.ContinuityError, OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
