"""그림 원본을 DiagramPlay SVG와 VHS GIF로 변환.
인자: 선택 원본 경로(생략 시 현재 위치가 속한 저장소 루트의 docs/assets/ 아래 git 추적 원본), --diagramplay 경로, --static
출력: SVG·GIF와 도구 출력, stderr 실패(원본 없음, git 오류, 변환 실패), 종료 0 성공·비영 종료 실패
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

SOURCE_SUFFIXES = (".diagramplay", ".tape")


class SourceError(Exception):
    """원본 탐색 실패. 원인은 이미 stderr에 출력됨."""


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="*")
    parser.add_argument(
        "--diagramplay",
        help="checkout or src/cli.js; default: DIAGRAMPLAY_PATH or diagramplay on PATH",
    )
    parser.add_argument("--static", action="store_true")
    args = parser.parse_args(argv)
    try:
        sources = args.sources or _tracked_sources()
        if not sources:
            print("no tracked sources under docs/assets/", file=sys.stderr)
            return 1
        invalid = [p for p in sources if not p.endswith(SOURCE_SUFFIXES)]
        if invalid:
            for source in invalid:
                print(f"{source}: unsupported source; use .diagramplay or .tape", file=sys.stderr)
            return 1
        figures = [p for p in sources if p.endswith(".diagramplay")]
        tapes = [p for p in sources if p.endswith(".tape")]
        if tapes and args.static:
            print("figure options cannot be applied to .tape files", file=sys.stderr)
            return 1
        if tapes and shutil.which("vhs") is None:
            print("vhs not found on PATH; nothing rendered", file=sys.stderr)
            return 1
        configured = args.diagramplay or os.environ.get("DIAGRAMPLAY_PATH")
        command = ["diagramplay"]
        if configured:
            path = Path(configured).expanduser()
            cli = path / "src" / "cli.js" if path.is_dir() else path
            command = ["node", str(cli)]
        if figures:
            subprocess.run(command + ["check", *figures, "--strict", "--docs"], check=True)
            render_flags = ["--strict", "--docs"] + (["--static"] if args.static else [])
            subprocess.run(command + ["render", *figures, *render_flags], check=True)
        for source in tapes:
            # 찾은 녹화의 Output은 저장소 루트 기준이라 루트에서 실행. 경로 지정 녹화는 현재 위치 유지
            if args.sources:
                subprocess.run(["vhs", source], check=True)
            else:
                root = _repository_root()
                subprocess.run(["vhs", os.path.relpath(source, root)], check=True, cwd=root)
        return 0
    except SourceError:
        return 1
    except subprocess.CalledProcessError as error:
        return error.returncode if error.returncode > 0 else 1
    except OSError as error:
        print(f"failed to render figures: {error}", file=sys.stderr)
        return 1


def _tracked_sources() -> list[str]:
    """저장소 루트의 docs/assets/ 아래 추적 원본.
    하위 폴더에서 실행해도 루트 기준으로 찾고, 경로는 현재 위치 기준으로 돌려준다."""
    root = _repository_root()
    patterns = [f"docs/assets/*{suffix}" for suffix in SOURCE_SUFFIXES]
    listed = _git("-C", str(root), "ls-files", "-z", "--", *patterns)
    return [
        os.path.relpath(root / p.decode("utf-8")) for p in listed.split(b"\0") if p
    ]


def _repository_root() -> Path:
    """현재 위치가 속한 저장소 루트."""
    return Path(_git("rev-parse", "--show-toplevel").decode("utf-8").strip())


def _git(*arguments: str) -> bytes:
    """git 출력. 실패하면 git stderr를 그대로 보여 주고 실패를 올린다."""
    result = subprocess.run(["git", *arguments], capture_output=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr.decode("utf-8", "replace"))
        raise SourceError(f"git exited {result.returncode}")
    return result.stdout


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
