"""Claude status line에 문맥 사용량 기록(statusline.py)을 연결하거나 떼어 낸다. 기존 명령은 보존한다.

인자: install|remove, --home 홈 경로(기본 사용자 홈)
출력: 변경 결과 한 줄과 종료 0, 실패는 stderr와 종료 2
원래 명령 보관: `~/.config/skills/statusline-original.json`
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import shlex
import sys
from typing import Iterator


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def save(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    draft = path.with_name(path.name + ".pending")
    draft.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(draft, path)


@contextlib.contextmanager
def locked(folder: Path) -> Iterator[None]:
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "statusline.lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=["install", "remove"])
    parser.add_argument("--home", type=Path, default=Path.home())
    args = parser.parse_args()
    settings_path = args.home / ".claude/settings.json"
    configuration = args.home / ".config/skills"
    saved_path = configuration / "statusline-original.json"
    script = Path(__file__).with_name("statusline.py").resolve()
    wrapper = {"type": "command", "command": f"python3 {shlex.quote(str(script))} --command-file {shlex.quote(str(saved_path))}"}
    try:
        with locked(configuration):
            settings = read(settings_path)
            original = settings.get("statusLine")
            if args.action == "install":
                if original == wrapper:
                    print("already installed")
                    return 0
                if saved_path.exists():
                    raise ValueError("saved status line exists; inspect changed settings before installing")
                if original and original.get("type") != "command":
                    raise ValueError("unsupported existing status line type")
                save(saved_path, original or {})
                settings["statusLine"] = wrapper
            else:
                if original != wrapper:
                    raise ValueError("status line changed; refusing to overwrite")
                previous = read(saved_path)
                if previous:
                    settings["statusLine"] = previous
                else:
                    settings.pop("statusLine", None)
                saved_path.unlink(missing_ok=True)
            save(settings_path, settings)
        print(args.action + " complete; existing hooks preserved")
        return 0
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
