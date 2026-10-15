"""추적 그림 원본을 ThinkFlow SVG와 VHS GIF로 변환.
인자: 선택 원본 경로, --thinkflow 경로, --static, 저장소 루트에서 실행
출력: SVG·GIF와 도구 출력, 종료 0 성공·비영 종료 실패
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


# cost: time O(n + s) + 도구 실행 시간, heap O(n + s), stack O(1), io O(n)
# vars: n = 원본 경로 글자 수, s = 자식 프로세스 출력 크기
# basis: estimate
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="*")
    parser.add_argument(
        "--thinkflow",
        help="checkout or src/cli.js; default: THINKFLOW_PATH or thinkflow on PATH",
    )
    parser.add_argument("--static", action="store_true")
    args = parser.parse_args(argv)
    try:
        sources = args.sources or _tracked_sources()
        invalid = [p for p in sources if not p.endswith((".thinkflow", ".tape"))]
        if invalid:
            for source in invalid:
                print(f"{source}: migrate to .thinkflow before rendering", file=sys.stderr)
            return 1
        figures = [p for p in sources if p.endswith(".thinkflow")]
        tapes = [p for p in sources if p.endswith(".tape")]
        if tapes and args.static:
            print("figure options cannot be applied to .tape files", file=sys.stderr)
            return 1
        configured = args.thinkflow or os.environ.get("THINKFLOW_PATH")
        command = ["thinkflow"]
        if configured:
            path = Path(configured).expanduser()
            cli = path / "src" / "cli.js" if path.is_dir() else path
            command = ["node", str(cli)]
        if figures:
            subprocess.run(command + ["check", *figures, "--strict"], check=True)
            render_flags = ["--strict"] + (["--static"] if args.static else [])
            subprocess.run(command + ["render", *figures, *render_flags], check=True)
        for source in tapes:
            subprocess.run(["vhs", source], check=True)
        return 0
    except subprocess.CalledProcessError as error:
        return error.returncode if error.returncode > 0 else 1
    except OSError as error:
        print(f"failed to render figures: {error}", file=sys.stderr)
        return 1


# cost: time O(n), heap O(n), stack O(1), io 1
# vars: n = git이 출력한 경로 바이트 수
# basis: estimate
def _tracked_sources() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.thinkflow", "*.tape"],
        capture_output=True,
        check=True,
    )
    return [str(Path(p.decode("utf-8"))) for p in result.stdout.split(b"\0") if p]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
