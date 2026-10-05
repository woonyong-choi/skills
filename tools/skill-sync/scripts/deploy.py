"""원본 검사·로컬 설치·계정 반영·대조.

인자: --source, --dry-run, --login
출력: 대조 표, 종료 0 성공·1 실패·2 인자 오류
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import install

SCRIPTS = Path(__file__).resolve().parent


# cost: time O(b + f log f), heap O(b + f), stack O(d), io O(f)
# vars: b = 원본 바이트 수, f = 파일 수, d = 폴더 깊이
# basis: estimate
def source_record(skill: Path, dist: Path) -> dict[str, str]:
    content = (skill / "SKILL.md").read_bytes()
    description = re.search(r'^description: "(.*)"$', content.decode(), re.M)
    if description is None:
        raise ValueError(f"invalid description: {skill.name}")
    return {"name": skill.name, "description": description[1], "sourceHash": install.tree_hash(skill),
            "skillHash": hashlib.sha256(content).hexdigest(), "path": str(dist / f"{skill.name}.zip")}


# cost: time O(n·b), heap O(b + n), stack O(1), io O(n·t)
# vars: n = 스킬 수, b = SKILL.md 바이트 수, t = 설치 도구 수
# basis: estimate
def verify_local(records: list[dict[str, str]], roots: dict[str, Path], *, account_verified: bool) -> bool:
    print("| 스킬 | " + " | ".join(roots) + " | zip | 계정 이름·description·영수증 |")
    print("|---|" + "---|" * (len(roots) + 2))
    success = True
    for record in records:
        states = []
        for root in roots.values():
            path = root / record["name"] / "SKILL.md"
            states.append(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == record["skillHash"])
        try:
            with zipfile.ZipFile(record["path"]) as bundle:
                states.append(hashlib.sha256(bundle.read(f'{record["name"]}/SKILL.md')).hexdigest() == record["skillHash"])
        except (OSError, KeyError, zipfile.BadZipFile):
            states.append(False)
        success = success and all(states)
        print("| " + record["name"] + " | " + " | ".join("일치" if state else "실패" for state in states) + (" | 일치 |" if account_verified else " | 미확인 |"))
    return success


# cost: time O(n·b + n·f log f), heap O(n·b + f), stack O(d), io O(n·f + q)
# vars: n = 스킬 수, b = 스킬 바이트 수, f = 파일 수, d = 폴더 깊이, q = 계정 UI 조회 횟수
# basis: estimate
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--login", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.login:
            if args.dry_run:
                parser.error("--login and --dry-run are mutually exclusive")
            return subprocess.run(["node", str(SCRIPTS / "claude_upload.mjs"), "--login"]).returncode
        source = install.resolve_source(args.source)
        checked = subprocess.run([sys.executable, str(SCRIPTS / "skill_check.py"), str(source)], capture_output=True, text=True)
        print(checked.stdout, end="")
        if checked.returncode or checked.stdout.strip() != "total 0":
            print(checked.stderr or "source check failed", file=sys.stderr)
            return 1
        skills = install.source_skills(source)
        dist = source / "dist/claude"
        records = [source_record(skill, dist) for skill in skills]
        if not args.dry_run:
            for tool in ("codex", "claude-code"):
                install.TOOL_HOMES[tool].mkdir(parents=True, exist_ok=True)
        install_args = ["--source", str(source)] + (["--dry-run"] if args.dry_run else [])
        if install.main(install_args):
            return 1
        request = json.dumps({"skills": records, "dryRun": args.dry_run})
        sys.stdout.flush()
        account = subprocess.run(["node", str(SCRIPTS / "claude_upload.mjs")], input=request, text=True)
        if args.dry_run:
            return 0 if account.returncode == 0 else 1
        if records != [source_record(skill, dist) for skill in skills]:
            raise ValueError("source changed during deployment; rerun deploy")
        roots = {tool: root for tool, root in install.TARGETS.items() if install.TOOL_HOMES[tool].is_dir()}
        local_verified = verify_local(records, roots, account_verified=account.returncode == 0)
        return 0 if local_verified and account.returncode == 0 else 1
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"deploy failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
