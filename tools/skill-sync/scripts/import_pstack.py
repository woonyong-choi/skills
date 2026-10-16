"""cursor/plugins의 pstack을 이 저장소 pstack/ 아래로 원문 그대로 가져온다.

사용: python3 import_pstack.py --source <cursor/plugins 작업본> [--dest <이 저장소>]
인자: --source cursor/plugins git 작업본(pstack/ 포함), --dest 가져올 저장소 루트(기본 이 저장소)
출력: stdout 가져온 스킬 수와 원본 commit, 종료 0 성공·1 원본 형식 오류·2 인자 오류
가져오는 방식: pstack/skills/<이름>/ → pstack/<이름>/, 그 밖 파일 → pstack/_upstream/.
원문 수정은 형식 호환에 필요한 name 정규화뿐(SOURCE.json patches에 기록). Codex 자동 호출 차단 파일(agents/openai.yaml)을 덧붙인다
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

UPSTREAM = "_upstream"
# 스킬 폴더마다 두는 원본 표시. 설치본처럼 폴더가 평탄해져도 검사기가 가져온 스킬을 구분
MARKER = "UPSTREAM.json"
REPOSITORY = "https://github.com/cursor/plugins"
MANUAL = "disable-model-invocation: true"


class UpstreamError(Exception):
    """원본 형식이 기대와 다름"""


# cost: time O(1), heap O(1), stack O(1), io 1
# basis: estimate
def commit_of(source: Path) -> str:
    done = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    if done.returncode:
        raise UpstreamError(f"git 작업본 아님: {source}")
    return done.stdout.strip()


# cost: time O(b), heap O(b), stack O(1), io 1
# vars: b = SKILL.md 바이트
# basis: estimate
def sidecar(skill: Path) -> str | None:
    """사람이 부를 때만 켜지는 스킬이면 Codex용 agents/openai.yaml 내용, 아니면 None"""
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    if MANUAL not in text.split("---", 2)[1]:
        return None
    return f'interface:\n  display_name: "{skill.name}"\n  default_prompt: "${skill.name} [요청]"\npolicy:\n  allow_implicit_invocation: false\n'


# cost: time O(b), heap O(b), stack O(1), io 2
# vars: b = SKILL.md 바이트
# basis: estimate
def normalize_name(skill: Path) -> bool:
    """frontmatter name이 폴더 이름과 다르면(예: `Poteto Mode`) 폴더 이름으로 바꾼다. Agent Skills 형식은 소문자·하이픈 이름이 폴더와 같아야 OpenCode·Codex가 읽는다"""
    path = skill / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    head, sep, body = text[4:].partition("\n---")
    fixed = re.sub(r"^name: .*$", f"name: {skill.name}", head, count=1, flags=re.M)
    if fixed == head:
        return False
    path.write_text("---\n" + fixed + sep + body, encoding="utf-8")
    return True


# cost: time O(f), heap O(f), stack O(d), io O(f)
# vars: f = 원본 파일 수, d = 폴더 깊이
# basis: estimate
def import_pstack(source: Path, dest: Path) -> dict:
    root = source / "pstack"
    manifest = json.loads((root / "plugin.json").read_text(encoding="utf-8"))
    skills = sorted(path for path in (root / "skills").iterdir() if (path / "SKILL.md").is_file())
    if not skills:
        raise UpstreamError("pstack/skills 아래 스킬 없음")
    for skill in skills:
        if not re.fullmatch(r"[a-z0-9-]+", skill.name):
            raise UpstreamError(f"스킬 이름 형식: {skill.name}")
    target = dest / "pstack"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir()
    ignore = shutil.ignore_patterns("node_modules", ".DS_Store")
    patches: list[str] = []
    commit = commit_of(source)
    for skill in skills:
        shutil.copytree(skill, target / skill.name, ignore=ignore)
        marker = {"repository": REPOSITORY, "path": f"pstack/skills/{skill.name}", "commit": commit}
        (target / skill.name / MARKER).write_text(json.dumps(marker, ensure_ascii=False) + "\n", encoding="utf-8")
        if normalize_name(target / skill.name):
            patches.append(f"{skill.name}/SKILL.md: name을 폴더 이름으로")
        extra = sidecar(skill)
        if extra is not None:
            (target / skill.name / "agents").mkdir(exist_ok=True)
            (target / skill.name / "agents/openai.yaml").write_text(extra, encoding="utf-8")
    upstream = target / UPSTREAM
    upstream.mkdir()
    for item in sorted(root.iterdir()):
        if item.name == "skills":
            continue
        copy = shutil.copytree if item.is_dir() else shutil.copy2
        copy(item, upstream / item.name, **({"ignore": ignore} if item.is_dir() else {}))
    record = {"repository": REPOSITORY, "path": "pstack", "commit": commit, "version": manifest.get("version"), "skills": len(skills), "patches": patches}
    (upstream / "SOURCE.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record


# cost: time O(f), heap O(f), stack O(d), io O(f)
# vars: f = 원본 파일 수, d = 폴더 깊이
# basis: estimate
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--dest", type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args(argv)
    try:
        record = import_pstack(args.source.resolve(), args.dest.resolve())
    except (UpstreamError, OSError, ValueError, KeyError) as error:
        print(error, file=sys.stderr)
        return 1
    print(f"pstack {record['version']} {record['commit'][:7]}: 스킬 {record['skills']}개")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
