"""비용 주석(`cost:`)이 있어야 하는데 없는 함수를 찾는다.

사용: python3 check_cost_comments.py <폴더나 파일 ...>

출력: `{경로}:{줄}: {함수 이름}: {이유}` 줄들과 마지막 `total {개수}`. 개수가 0이 아니면 종료 코드 1.
code-style은 비용이 드러나지 않는 알고리즘, 병목, 외부 호출 경계에만 비용 주석을 요구한다.
스크립트는 정적으로 식별 가능한 파일·네트워크·프로세스·모델 호출 경계만 검사한다.
대상: Python(`def`), JavaScript·TypeScript(`function`, 블록 본문 화살표 함수), Rust(`fn`), Kotlin(`fun`).

인자: 폴더나 파일 하나 이상
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Iterator

# 생성 파일 첫 줄 표시. design-tokens 생성물과 일반적인 `@generated` 표시
GENERATED_MARKS = ("생성물, 손으로 고치지 않음", "@generated")
SKIP_DIRS = {"node_modules", "dist", "build", "coverage", "target", ".git", ".venv", "venv", "__pycache__"}
LANGUAGES = {
    ".py": "python",
    ".js": "js",
    ".mjs": "js",
    ".cjs": "js",
    ".ts": "js",
    ".jsx": "js",
    ".tsx": "js",
    ".rs": "rust",
    ".kt": "kotlin",
    ".kts": "kotlin",
}
# 각 패턴의 이름 그룹은 `name`
DECLARATION = {
    "python": [re.compile(r"^\s*(?:async\s+)?def\s+(?P<name>\w+)\s*\(")],
    "js": [
        re.compile(r"^\s*(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s*\*?\s*(?P<name>\w+)\s*\("),
        re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+(?P<name>\w+)\s*(?::[^=]+)?=\s*(?:async\s+)?(?:\([^)]*\)|\w+)\s*(?::[^=]+)?=>\s*\{"),
        re.compile(r"^\s*(?:(?:static|async|get|set|public|private|protected|readonly)\s+|\*\s*)*(?P<name>#?\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|\w+)\s*=>\s*\{"),
        re.compile(r"^\s*(?:(?:static|async|get|set|public|private|protected)\s+|\*\s*)*(?P<name>#?(?!(?:if|for|while|switch|catch|return|function)\b)\w+)\s*\([^)]*\)\s*(?::[^{]+)?\{"),
    ],
    "rust": [re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:const\s+)?(?:async\s+)?(?:unsafe\s+)?(?:extern\s+\"[^\"]*\"\s+)?fn\s+(?P<name>\w+)")],
    "kotlin": [
        re.compile(
            r"^\s*(?:(?:public|private|internal|protected|override|open|final|abstract|actual|expect|external|suspend|inline|tailrec|operator|infix)\s+)*"
            r"fun\s+(?:<[^>]*>\s*)?(?:[\w.<>?, ]+\.)?(?P<name>\w+)\s*\("
        )
    ],
}
# 문서 주석·attribute·데코레이터·애노테이션 줄. 비용 주석은 이 줄들보다 위에 둔다(code-style 비용 주석).
DOC_OR_ATTRIBUTE = re.compile(r"^\s*(?:@|#\[|///|//!|/\*\*|\*|\*/)")
COMMENT_MARK = {"python": "#", "js": "//", "rust": "//", "kotlin": "//"}
STRING = re.compile(r"\"\"\"[\s\S]*?\"\"\"|\'\'\'[\s\S]*?\'\'\'|'(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\"|`(?:[^`\\]|\\.)*`")
IO = {
    "python": re.compile(r"\bopen\(|\bsubprocess\.|\bos\.(?:walk|listdir|remove|makedirs)\(|\brequests\.|\burllib\.|\bprint\("),
    # `.exec(`는 정규식 메서드라 제외한다(앞에 점이 없는 호출만 프로세스 실행으로 본다).
    "js": re.compile(r"\bfetch\(|(?<![.\w])(?:readFile|writeFile|readdir|mkdir|rm|spawn|exec|execFile)(?:Sync)?\(|\bconsole\."),
    "rust": re.compile(r"\bstd::fs::|\bfs::|\bFile::|\bCommand::|\breqwest::|\bprintln!|\beprintln!"),
    "kotlin": re.compile(r"\bFile\(|\breadText\(|\bwriteText\(|\bProcessBuilder\(|\bprintln\("),
}


# cost: time O(n), heap O(n), stack O(1), io 1
# vars: n = 파일 줄 수
# basis: estimate
def check_file(path: str) -> list[tuple[str, int, str, str]]:
    """파일 하나에서 비용 주석이 빠진 함수를 찾는다."""
    language = LANGUAGES[os.path.splitext(path)[1].lower()]
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().split("\n")
    if any(mark in lines[0] for mark in GENERATED_MARKS):
        return []
    findings = []
    for index, line in enumerate(lines):
        match = next((m for pattern in DECLARATION[language] if (m := pattern.match(line))), None)
        if not match:
            continue
        name = match.group("name").lstrip("#")
        placement = find_cost_placement(lines, index, language)
        if placement == "below":
            findings.append((path, index + 1, name, "cost comment below doc comment or attribute"))
            continue
        reason = find_cost_reason(find_body(lines, index, language), language)
        if reason and placement == "missing":
            findings.append((path, index + 1, name, reason))
    return findings


# cost: time O(b), heap O(b), stack O(1)
# vars: b = 함수 본문 줄 수
# basis: estimate
def find_body(lines: list[str], start: int, language: str) -> list[str]:
    """선언 다음 본문 줄. Python은 들여쓰기로, 나머지는 중괄호 짝으로 끝을 찾는다."""
    if language == "python":
        indent = len(lines[start]) - len(lines[start].lstrip())
        body = []
        for line in lines[start + 1 :]:
            if line.strip() and len(line) - len(line.lstrip()) <= indent and not line.lstrip().startswith(")"):
                break
            body.append(line)
        return body
    expression = re.search(r"\)\s*(?::[^={]+)?=(?![=>])", strip_strings(lines[start]))
    if expression:
        # `fun f() = xs.map { … }`처럼 식 본문은 `=` 뒤와, 선언보다 깊게 들여 쓴 다음 줄들이다.
        indent = len(lines[start]) - len(lines[start].lstrip())
        body = [strip_strings(lines[start])[expression.end() :]]
        for line in lines[start + 1 :]:
            if not line.strip() or len(line) - len(line.lstrip()) <= indent:
                break
            body.append(line)
        return body
    first = strip_strings(lines[start]).rstrip()
    if language == "kotlin" and "{" not in first and not first.endswith(("(", ",")):
        # 본문 없는 선언(abstract, interface 메서드)
        return []
    depth = 0
    has_opened = False
    body = []
    for offset, line in enumerate(lines[start:]):
        code = strip_strings(line)
        if not has_opened and "{" in code:
            # 여는 괄호 앞(선언부)은 본문이 아니다. 한 줄 함수도 괄호 뒤만 본다.
            line = line[line.index("{") + 1 :] if "{" in line else line
            code = code[code.index("{") + 1 :]
            depth, has_opened = 1, True
        elif not has_opened:
            if code.rstrip().endswith(";"):
                return []
            continue
        depth += code.count("{") - code.count("}")
        body.append(line)
        if depth <= 0:
            break
    return body


def strip_strings(line: str) -> str:
    """중괄호를 셀 때 문자열과 줄 주석 안의 괄호를 빼려고 지운다."""
    line = re.sub(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|`(?:[^`\\]|\\.)*`", "''", line)
    return line.split("//")[0]


# cost: time O(b), heap O(b), stack O(1)
# vars: b = 함수 본문 글자 수
# basis: estimate
def find_cost_reason(body: list[str], language: str) -> str | None:
    """비용 주석이 필요한 외부 호출 경계, 없으면 None."""
    marker = COMMENT_MARK[language]
    text = STRING.sub("''", "\n".join(body))
    text = "\n".join(line.split(marker)[0] if marker != "#" else re.sub(r"#.*$", "", line) for line in text.split("\n"))
    if IO[language].search(text):
        return "external call without cost comment"
    return None


# cost: time O(k), heap O(1), stack O(1)
# vars: k = 선언 위 주석·attribute 줄 수
# basis: estimate
def find_cost_placement(lines: list[str], index: int, language: str) -> str:
    """선언 위 `cost:` 줄의 자리. `above`(맞는 자리), `below`(문서 주석·attribute 아래), `missing`.

    선언에서 위로 문서 주석·attribute·주석 줄을 따라 올라간다. Kotlin은 ktlint 때문에
    비용 주석과 KDoc 사이 빈 줄 하나를 허용한다(code-style 비용 주석).
    """
    marker = COMMENT_MARK[language]
    has_doc_below = False
    has_blank = False
    for position in range(index - 1, -1, -1):
        line = lines[position]
        stripped = line.strip()
        if stripped.startswith(f"{marker} cost:"):
            return "below" if has_doc_above(lines, position, marker) else "above"
        if not stripped:
            if language == "kotlin" and has_doc_below and not has_blank:
                has_blank = True
                continue
            return "missing"
        if DOC_OR_ATTRIBUTE.match(line):
            has_doc_below = True
        elif not stripped.startswith(marker):
            return "missing"
    return "missing"


# cost: time O(k), heap O(1), stack O(1)
# vars: k = 비용 주석 위 주석 줄 수
# basis: estimate
def has_doc_above(lines: list[str], cost_index: int, marker: str) -> bool:
    """`cost:` 줄 위로 이어지는 주석 묶음에 문서 주석·attribute가 있는지 본다. 있으면 자리가 틀렸다."""
    for line in reversed(lines[:cost_index]):
        stripped = line.strip()
        if not stripped:
            return False
        if DOC_OR_ATTRIBUTE.match(line):
            return True
        if not stripped.startswith(marker):
            return False
    return False


# cost: time O(f), heap O(d), stack O(d), io f
# vars: f = 파일 수, d = 폴더 깊이
# basis: estimate
def iter_files(targets: list[str]) -> Iterator[str]:
    """검사할 파일 경로. 폴더는 정렬 순서로 내려간다."""
    for target in targets:
        if os.path.isfile(target):
            if os.path.splitext(target)[1].lower() in LANGUAGES:
                yield target
            continue
        for root, dirs, files in os.walk(target):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for name in sorted(files):
                if os.path.splitext(name)[1].lower() in LANGUAGES:
                    yield os.path.join(root, name)


# cost: time O(N), heap O(r), stack O(d), io f
# vars: N = 전체 줄 수, r = 찾은 수, f = 파일 수, d = 폴더 깊이
# basis: estimate
def main() -> int:
    """찾은 함수를 출력한다. 하나라도 있으면 1을 돌려준다."""
    parser = argparse.ArgumentParser(description="비용 주석이 빠진 함수를 찾는다")
    parser.add_argument("targets", nargs="+")
    args = parser.parse_args()
    results = [finding for path in iter_files(args.targets) for finding in check_file(path)]
    for path, line, name, reason in results:
        print(f"{path}:{line}: {name}: {reason}")
    print(f"total {len(results)}")
    return 1 if results else 0


if __name__ == "__main__":
    sys.exit(main())
