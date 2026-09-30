"""머지된 작업 브랜치의 worktree, 로컬 브랜치, 원격 브랜치 정리.

사용: python3 cleanup_merged.py [--apply] (저장소 안에서 실행)
기본은 미리보기. --apply면 실제로 정리한다. 커밋 안 된 변경이 있는 worktree는 건드리지 않는다.
squash 머지는 브랜치 커밋이 main의 조상이 아니라서 GitHub PR 상태(gh)로 머지 여부를 판정한다.
"""
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
def worktrees() -> list[tuple[Path, str]]:
    entries, path = [], None
    for line in run(["git", "worktree", "list", "--porcelain"]).splitlines():
        if line.startswith("worktree "):
            path = Path(line.split(" ", 1)[1])
        elif line.startswith("branch refs/heads/") and path:
            entries.append((path, line.removeprefix("branch refs/heads/")))
    return entries[1:]


# cost: time O(1), heap O(1), stack O(1), io 1
# basis: estimate
def merged_pr(branch: str) -> bool:
    output = run(["gh", "pr", "list", "--state", "merged", "--head", branch, "--json", "number"], check=False)
    return bool(output) and bool(json.loads(output))


# cost: time O(1), heap O(1), stack O(1), io 1
# basis: estimate
def is_clean(path: Path) -> bool:
    return run(["git", "-C", str(path), "status", "--porcelain"]) == ""


# cost: time O(b), heap O(b), stack O(1), io 3 + 3b
# vars: b = 로컬 브랜치 수
# basis: estimate
def main(apply: bool) -> int:
    run(["git", "fetch", "origin", "--prune"])
    remote = set(run(["git", "branch", "-r", "--format=%(refname:short)"]).splitlines())
    by_branch = dict((branch, path) for path, branch in worktrees())
    local = run(["git", "branch", "--format=%(refname:short)"]).splitlines()
    actions, kept = [], []
    for branch in [name for name in local if name not in PROTECTED]:
        if not merged_pr(branch):
            continue
        path = by_branch.get(branch)
        if path and not is_clean(path):
            kept.append(f"{branch}: 커밋 안 된 변경이 있는 worktree {path}")
            continue
        if path:
            actions.append(["git", "worktree", "remove", str(path)])
        actions.append(["git", "branch", "-D", branch])
        if f"origin/{branch}" in remote:
            actions.append(["git", "push", "origin", "--delete", branch])
    for action in actions:
        print(("run: " if apply else "plan: ") + " ".join(action))
        if apply:
            run(action)
    for item in kept:
        print("keep: " + item)
    if apply:
        run(["git", "worktree", "prune"])
        for folder in {path.parent for path in by_branch.values()}:
            if folder.name.endswith(".wt") and folder.is_dir() and not any(folder.iterdir()):
                folder.rmdir()
                print(f"run: rmdir {folder}")
    return 0


if __name__ == "__main__":
    sys.exit(main("--apply" in sys.argv[1:]))
