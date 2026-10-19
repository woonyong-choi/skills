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


def source_record(skill: Path, dist: Path) -> dict[str, str]:
    content = (skill / "SKILL.md").read_bytes()
    description = re.search(r'^description: "(.*)"$', content.decode(), re.M)
    if description is None:
        raise ValueError(f"invalid description: {skill.name}")
    escapes = {
        "0": "\0", "a": "\a", "b": "\b", "t": "\t", "\t": "\t", "n": "\n", "v": "\v",
        "f": "\f", "r": "\r", "e": "\x1b", " ": " ", '"': '"', "/": "/", "\\": "\\",
        "N": "\x85", "_": "\xa0", "L": "\u2028", "P": "\u2029",
    }
    hex_widths = {"x": 2, "u": 4, "U": 8}
    encoded = description[1]
    decoded = []
    index = 0
    while index < len(encoded):
        char = encoded[index]
        index += 1
        if char == '"':
            raise ValueError(f"invalid description: {skill.name}: unescaped quote")
        if char != "\\":
            decoded.append(char)
            continue
        if index == len(encoded):
            raise ValueError(f"invalid description: {skill.name}: truncated escape")
        escape = encoded[index]
        index += 1
        if escape in escapes:
            decoded.append(escapes[escape])
            continue
        if escape not in hex_widths:
            raise ValueError(f"invalid description: {skill.name}: unknown escape {escape!r}")
        width = hex_widths[escape]
        digits = encoded[index:index + width]
        if len(digits) != width or re.fullmatch(r"[0-9a-fA-F]+", digits) is None:
            raise ValueError(f"invalid description: {skill.name}: invalid hex escape")
        codepoint = int(digits, 16)
        index += width
        if escape == "u" and 0xD800 <= codepoint <= 0xDBFF:
            pair = encoded[index:index + 6]
            if re.fullmatch(r"\\u[dD][c-fC-F][0-9a-fA-F]{2}", pair) is None:
                raise ValueError(f"invalid description: {skill.name}: invalid surrogate pair")
            codepoint = 0x10000 + (codepoint - 0xD800) * 0x400 + int(pair[2:], 16) - 0xDC00
            index += 6
        if codepoint > 0x10FFFF or 0xD800 <= codepoint <= 0xDFFF:
            raise ValueError(f"invalid description: {skill.name}: invalid Unicode escape")
        decoded.append(chr(codepoint))
    return {"name": skill.name, "description": "".join(decoded), "sourceHash": install.tree_hash(skill),
            "skillHash": hashlib.sha256(content).hexdigest(), "path": str(dist / f"{skill.name}.zip")}


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
