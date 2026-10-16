"""공고 폴더의 이력서·포트폴리오 작업 파일 확정, 변경 표시 개수, 폴더 구조 검사.

사용: python3 versions.py root [--set <폴더>] | place <공고 폴더> | confirm <문서 폴더> | marks <작업 파일> | check <공고 폴더>
인자: root는 산출물 폴더 확인, --set은 <설정 폴더>/career.json의 root에 저장. place는 만들 공고 폴더(없어도 됨), confirm은 이력서/ 또는 포트폴리오/ 폴더, marks는 작업 .typ, check는 공고 폴더. confirm --no-compile은 PDF 생성 생략
출력: root는 stdout 산출물 폴더 절대 경로(미설정이면 종료 1), place는 stdout 검사한 절대 경로, confirm은 stdout 확정 .typ·.pdf 경로, marks는 stdout `추가 N 바뀜 N 삭제 N`, check는 stdout `ok`. stderr 실패 이유, 종료 0 성공·1 실패·2 인자 오류
산출물 폴더: 환경 변수 CAREER_ROOT, 없으면 <설정 폴더>/career.json의 root. 설정 폴더는 SKILLS_CONFIG_DIR, 없으면 ~/.config/skills
실행 조건: Python 3.9 이상. PDF 생성은 PATH의 typst 또는 Python typst 패키지
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


DOCUMENTS = ("이력서", "포트폴리오")
SECTIONS = ("# 공고 분석", "# 구성 계획", "# 작성", "# 확인")
TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "typst" / "career.typ"
MARK = re.compile(r"(#?)\b(added|changed|removed)\[")
LEGEND = re.compile(r"^[ \t]*#changes-legend\(.*\)[ \t]*\n?", re.MULTILINE)


class CareerError(Exception):
    """검사·확정 실패. 메시지가 사용자에게 보일 이유"""


def bracket_end(text: str, start: int) -> int:
    """text[start] == '['인 내용 블록의 닫는 괄호 다음 위치. 역슬래시로 막은 괄호는 건너뜀"""
    depth = 0
    at = start
    while at < len(text):
        char = text[at]
        if char == "\\":
            at += 2
            continue
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return at + 1
        at += 1
    raise CareerError(f"닫히지 않은 괄호: {text[start:start + 30]!r}")


def resolve(text: str) -> str:
    """변경 표시를 반영한 깨끗한 원문: added→본문, changed→새 문장, removed→삭제(코드 안은 none), 범례 줄 삭제"""
    text = LEGEND.sub("", text)
    out = []
    at = 0
    while (match := MARK.search(text, at)) is not None:
        out.append(text[at:match.start()])
        markup = match.group(1) == "#"
        first_end = bracket_end(text, match.end() - 1)
        first = text[match.end():first_end - 1]
        kind = match.group(2)
        if kind == "changed":
            if first_end >= len(text) or text[first_end] != "[":
                raise CareerError("changed는 [이전][새 문장] 두 블록 필요")
            second_end = bracket_end(text, first_end)
            body = resolve(text[first_end + 1:second_end - 1])
            out.append(body if markup else f"[{body}]")
            at = second_end
            continue
        if kind == "added":
            body = resolve(first)
            out.append(body if markup else f"[{body}]")
        elif not markup:
            out.append("none")
        at = first_end
    out.append(text[at:])
    return "".join(out)


def count_marks(text: str) -> dict[str, int]:
    names = {"added": "추가", "changed": "바뀜", "removed": "삭제"}
    counts = {label: 0 for label in names.values()}
    for match in MARK.finditer(text):
        counts[names[match.group(2)]] += 1
    return counts


def numbered(folder: Path) -> list[int]:
    pattern = re.compile(rf"^{re.escape(folder.name)}-(\d{{4}})\.typ$")
    return sorted(int(m.group(1)) for path in folder.iterdir() if (m := pattern.match(path.name)))


def compile_pdf(source: Path, root: Path) -> Path:
    """표시 끈 PDF. 공고 폴더를 root로 두어 /career.typ, /figures 참조 허용"""
    pdf = source.with_suffix(".pdf")
    if shutil.which("typst"):
        subprocess.run(["typst", "compile", "--root", str(root), "--input", "changes=off", str(source), str(pdf)], check=True)
        return pdf
    try:
        import typst  # PATH에 typst가 없을 때만 Python 패키지 사용
    except ImportError as error:
        raise CareerError("typst 없음: PATH의 typst 또는 pip install typst 필요") from error
    typst.compile(str(source), output=str(pdf), root=str(root), sys_inputs={"changes": "off"})
    return pdf


def config_path() -> Path:
    return Path(os.environ.get("SKILLS_CONFIG_DIR") or Path.home() / ".config/skills").expanduser() / "career.json"


def read_config(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as error:
        raise CareerError(f"설정 형식 오류: {path}: {error}") from error
    if not isinstance(config, dict):
        raise CareerError(f"설정 형식 오류: {path}: 객체가 아님")
    return config


def career_root() -> Path:
    """산출물 폴더(공고 폴더·교정 기록): CAREER_ROOT, 없으면 career.json의 root"""
    value = os.environ.get("CAREER_ROOT") or read_config(config_path()).get("root")
    if not value:
        raise CareerError("산출물 폴더 미설정: 사용자에게 위치를 묻고 versions.py root --set <폴더>로 저장")
    return Path(value).expanduser().resolve()


def save_root(folder: Path) -> Path:
    """career.json의 root만 바꾸고 다른 키는 보존. 임시 파일과 rename으로 한 번에 교체"""
    path = config_path()
    config = read_config(path)
    config["root"] = str(folder.expanduser().resolve())
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_name(path.name + ".pending")
    try:
        staged.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(staged, path)
    finally:
        staged.unlink(missing_ok=True)
    return Path(config["root"])


def inside_root(folder: Path) -> None:
    """쓰기 전 산출물 폴더 아래인지 확인. 아니면 파일을 쓰지 않고 CareerError"""
    if not folder.resolve().is_relative_to(career_root()):
        raise CareerError(f"산출물 폴더 밖: {folder}")


def confirm(folder: Path, build: bool = True) -> list[Path]:
    """작업 파일을 깨끗하게 정리해 다음 번호로 저장하고 작업 파일도 같은 상태로 갱신"""
    inside_root(folder)
    if folder.name not in DOCUMENTS:
        raise CareerError(f"문서 폴더는 {', '.join(DOCUMENTS)} 중 하나: {folder}")
    work = folder / f"{folder.name}.typ"
    if not work.is_file():
        raise CareerError(f"작업 파일 없음: {work}")
    clean = resolve(work.read_text(encoding="utf-8"))
    number = (numbered(folder) or [0])[-1] + 1
    if number > 9999:
        raise CareerError("확정 번호 9999 초과")
    target = folder / f"{folder.name}-{number:04d}.typ"
    target.write_text(clean, encoding="utf-8")
    work.write_text(clean, encoding="utf-8")
    written = [target]
    if build:
        written.append(compile_pdf(target, folder.parent))
        compile_pdf(work, folder.parent)
    return written


def check(posting: Path) -> list[str]:
    """공고 폴더 구조·양식 해시·전략.md 절·문서 폴더 파일 이름 검사. 문제 목록 반환"""
    problems = []
    for name in ("jd.md", "전략.md", "career.typ"):
        if not (posting / name).is_file():
            problems.append(f"{name} 없음")
    template = posting / "career.typ"
    if template.is_file() and hashlib.sha256(template.read_bytes()).digest() != hashlib.sha256(TEMPLATE.read_bytes()).digest():
        problems.append("career.typ가 스킬 양식과 다름: 스킬의 assets/typst/career.typ 다시 복사")
    strategy = posting / "전략.md"
    if strategy.is_file():
        headings = [line.strip() for line in strategy.read_text(encoding="utf-8").splitlines() if re.match(r"^# \S", line)]
        if [h for h in headings if h in SECTIONS] != list(SECTIONS):
            problems.append(f"전략.md 절: {', '.join(SECTIONS)} 순서 필요")
        old = [h for h in headings if h in ("# SPEC", "# PLAN", "# IMPLEMENT", "# VERIFY")]
        if old:
            problems.append(f"전략.md 옛 절 이름: {', '.join(old)}")
    for stray in sorted(posting.glob("*.typ")):
        if stray.name != "career.typ":
            problems.append(f"문서 파일은 문서 폴더 안에: {stray.name}")
    for document in DOCUMENTS:
        folder = posting / document
        if not folder.is_dir():
            continue
        allowed = re.compile(rf"^{document}(?:-\d{{4}})?\.(?:typ|pdf)$")
        for path in sorted(folder.iterdir()):
            if not allowed.match(path.name):
                problems.append(f"{document}/{path.name}: 이름은 {document}.typ·{document}-NNNN.typ(4자리)와 같은 이름의 pdf만")
        work = folder / f"{document}.typ"
        if not work.is_file():
            problems.append(f"{document}/{document}.typ 작업 파일 없음")
        else:
            text = work.read_text(encoding="utf-8")
            if '#import "/career.typ"' not in text:
                problems.append(f'{document}/{document}.typ: #import "/career.typ": * 필요')
        for number in numbered(folder):
            text = (folder / f"{document}-{number:04d}.typ").read_text(encoding="utf-8")
            if MARK.search(text) or "changes-legend" in text:
                problems.append(f"{document}/{document}-{number:04d}.typ: 확정 버전에 변경 표시 남음")
    return problems


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("root", "place", "confirm", "marks", "check"))
    parser.add_argument("path", type=Path, nargs="?")
    parser.add_argument("--no-compile", action="store_true")
    parser.add_argument("--set", type=Path, dest="root")
    args = parser.parse_args(argv)
    if (args.action == "root") != (args.path is None) or (args.root is not None and args.action != "root"):
        parser.error("root만 경로 없이, 나머지는 경로 하나와 함께 실행")
    try:
        if args.action == "root":
            if args.root is not None:
                save_root(args.root)
                if os.environ.get("CAREER_ROOT"):
                    print("CAREER_ROOT 환경 변수가 저장한 값보다 우선", file=sys.stderr)
            print(career_root())
        elif args.action == "place":
            inside_root(args.path)
            print(args.path.resolve())
        elif args.action == "confirm":
            for path in confirm(args.path.resolve(), build=not args.no_compile):
                print(path)
        elif args.action == "marks":
            counts = count_marks(args.path.read_text(encoding="utf-8"))
            print(" ".join(f"{label} {count}" for label, count in counts.items()))
        else:
            problems = check(args.path.resolve())
            if problems:
                print("\n".join(problems), file=sys.stderr)
                return 1
            print("ok")
    except (CareerError, OSError, subprocess.CalledProcessError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
