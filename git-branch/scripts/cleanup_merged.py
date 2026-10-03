"""머지된 지정 PR 작업 브랜치의 worktree, 로컬 브랜치, 원격 브랜치 정리.

사용: python3 cleanup_merged.py <PR 번호 또는 브랜치> [--apply] (저장소 안에서 실행)
기본은 미리보기. --apply면 실제로 정리한다. PR의 마지막 head SHA와 로컬·원격 브랜치 head가 모두 같고,
연결된 worktree에 커밋 안 된 변경이 없을 때만 정리한다.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROTECTED = {"main", "master"}


# cost: time O(1), heap O(o), stack O(1), io 1
# vars: o = 명령 출력 크기
# basis: estimate
def run(args: list[str], check: bool = True) -> str:
    result = subprocess.run(args, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise SystemExit(f"command failed: {' '.join(args)}\n{result.stderr.strip()}")
    return result.stdout.strip()


# cost: time O(w), heap O(w), stack O(1), io 1
# vars: w = worktree 수
# basis: estimate
def worktrees() -> dict[str, Path]:
    entries: dict[str, Path] = {}
    path: Path | None = None
    for line in run(["git", "worktree", "list", "--porcelain"]).splitlines():
        if line.startswith("worktree "):
            path = Path(line.split(" ", 1)[1])
        elif line.startswith("branch refs/heads/") and path:
            entries[line.removeprefix("branch refs/heads/")] = path
    return entries


# cost: time O(1), heap O(1), stack O(1), io 1
# basis: estimate
def is_clean(path: Path) -> bool:
    return run(["git", "-C", str(path), "status", "--porcelain"]) == ""


# cost: time O(1), heap O(o), stack O(1), io 1
# vars: o = GitHub API 응답 크기
# basis: estimate
def resolve_pr(target: str) -> dict[str, object] | None:
    fields = "number,state,headRefName,headRefOid"
    if target.isdecimal():
        output = run(["gh", "pr", "view", target, "--json", fields], check=False)
        if not output:
            return None
        return json.loads(output)
    output = run(["gh", "pr", "list", "--state", "merged", "--head", target, "--json", fields], check=False)
    matches = json.loads(output) if output else []
    if len(matches) != 1:
        print(f"skip: {target}: 머지된 PR을 하나로 정할 수 없음 ({len(matches)}개)")
        return None
    return matches[0]


# cost: time O(1), heap O(1), stack O(1), io 2
# basis: estimate
def branch_heads_match(branch: str, expected_sha: str) -> bool:
    local = run(["git", "rev-parse", "--verify", f"refs/heads/{branch}"], check=False)
    remote = run(["git", "rev-parse", "--verify", f"refs/remotes/origin/{branch}"], check=False)
    if not local:
        print(f"skip: {branch}: 로컬 브랜치 없음")
        return False
    if not remote:
        print(f"skip: {branch}: 원격 브랜치 없음")
        return False
    if local != expected_sha or remote != expected_sha:
        print(f"skip: {branch}: PR head {expected_sha}, local {local}, remote {remote}")
        return False
    return True


# cost: time O(1), heap O(1), stack O(1), io 4
# basis: estimate
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help="머지된 PR 번호 또는 브랜치")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    run(["git", "fetch", "origin", "--prune"])
    pr = resolve_pr(args.target)
    if pr is None:
        return 1
    if pr["state"] != "MERGED":
        print(f"skip: PR #{pr['number']}: 머지되지 않음 ({pr['state']})")
        return 0
    branch = str(pr["headRefName"])
    if branch in PROTECTED:
        print(f"skip: {branch}: 보호 브랜치")
        return 0
    expected_sha = str(pr["headRefOid"])
    if not branch_heads_match(branch, expected_sha):
        return 0
    path = worktrees().get(branch)
    if path and not is_clean(path):
        print(f"skip: {branch}: 커밋 안 된 변경이 있는 worktree {path}")
        return 0
    actions: list[list[str]] = []
    if path:
        actions.append(["git", "worktree", "remove", str(path)])
    actions.extend(
        [
            ["git", "branch", "-D", branch],
            ["git", "push", "origin", "--delete", branch],
        ]
    )
    for action in actions:
        print(("run: " if args.apply else "plan: ") + " ".join(action))
        if args.apply:
            run(action)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
