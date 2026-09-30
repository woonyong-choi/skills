"""토큰 대신 직접 적은 화면 값(하드코딩)을 찾는다.

사용: python3 check_tokens.py <폴더나 파일 ...> [--tokens tokens.json]

출력: `{경로}:{줄}: {규칙}: {찾은 글자}` 줄들과 마지막 `total {개수}`. 개수가 0이 아니면 종료 코드 1.
JavaScript 계열 파일은 CSS나 마크업으로 보이는 문자열 안만 본다. 일반 문장 속 `2s` 같은 글자를 잘못 잡지 않기 위해서다.
"""
import argparse
import json
import os
import re
import sys

STYLE_EXTS = {".css", ".scss", ".html", ".svg", ".vue", ".svelte"}
SCRIPT_EXTS = {".js", ".mjs", ".cjs", ".ts", ".jsx", ".tsx"}
SKIP_DIRS = {"node_modules", "dist", "build", ".git", "coverage"}
TOKEN_FILES = {"tokens.json", "tokens.dark.json"}
GENERATED_MARK = "생성물, 손으로 고치지 않음"
ALLOW_MARK = "tokens-allow:"

# 토큰 없이 써도 되는 길이
FREE_LENGTHS = {"0", "100%", "50%", "100vh", "100vw"}
# 토큰 없이 써도 되는 단위 없는 숫자(flex 비율, 불투명)
FREE_NUMBERS = {"0", "1"}

RULES = [
    ("hex color", re.compile(r"(?<![\w&/])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b")),
    ("color function", re.compile(r"\b(?:rgba?|hsla?|oklch|oklab|lab|lch|hwb)\(")),
    ("font family", re.compile(r"font-family\s*:(?!\s*var\()[^;}\n]+|\bfont\s*:(?!\s*var\()[^;}\n]*(?:serif|monospace|system-ui)")),
]
LENGTH = re.compile(r"(?<![\w.#-])-?\d*\.?\d+(?:px|rem|em|ms|s|vh|vw|pt)\b")
UNITLESS_PROPERTY = re.compile(r"\b(font-weight|line-height|opacity|z-index|letter-spacing)\s*:\s*(-?[\d.]+)\b")
UNITLESS_ATTRIBUTE = re.compile(r"\b(rx|ry|stroke-width|font-size|font-weight|opacity|fill-opacity|stroke-opacity|letter-spacing)=\"\s*(-?[\d.]+)\s*\"")
CUSTOM_PROPERTY = re.compile(r"(--[\w-]+)\s*:\s*(?!var\()([^;}\n]+)")
MEDIA = re.compile(r"@media[^{]*")
STRING = re.compile(r"'(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\"|`(?:[^`\\]|\\.)*`", re.S)
COMMENT = re.compile(r"/\*.*?\*/", re.S)
# CSS 선언(`속성: 값`)이나 마크업 속성(`이름="값"`)이 들어 있는 문자열만 본다.
LOOKS_STYLED = re.compile(r"[\w-]+\s*:\s*[^;]+;|<\w[^>]*=|[\w-]+=\"")


# cost: time O(t), heap O(b), stack O(d), io 1
# vars: t = 토큰 수, b = breakpoint 토큰 수, d = 묶음 깊이
# basis: estimate
def load_breakpoints(path):
    """breakpoint 토큰의 px 숫자. `@media` 조건에 이 숫자만 허용한다."""
    if not path or not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        root = json.load(f)
    numbers = set()

    def walk(node):
        for key, child in node.items():
            if key.startswith("$") or not isinstance(child, dict):
                continue
            if "$value" in child:
                value = child["$value"]
                raw = value.get("value") if isinstance(value, dict) else value
                numbers.add(re.sub(r"px$", "", str(raw)))
            else:
                walk(child)

    if isinstance(root.get("breakpoint"), dict):
        walk(root["breakpoint"])
    return numbers


# cost: time O(n), heap O(n), stack O(1)
# vars: n = 글자 수
# basis: estimate
def styled_segments(text, ext):
    """검사할 글자 조각과 시작 위치. JavaScript 계열은 CSS나 마크업으로 보이는 문자열만 돌려준다."""
    text = COMMENT.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)
    if ext in STYLE_EXTS:
        return [(0, text)]
    return [(m.start(), m.group(0)) for m in STRING.finditer(text) if LOOKS_STYLED.search(m.group(0))]


# cost: time O(n), heap O(f), stack O(1)
# vars: n = 조각 글자 수, f = 찾은 수
# basis: estimate
def find_in_segment(segment, breakpoints):
    """조각 안 하드코딩. (조각 안 위치, 규칙, 글자) 목록."""
    found = []
    media_spans = []
    for m in MEDIA.finditer(segment):
        media_spans.append((m.start(), m.end()))
        for number in re.findall(r"(\d+(?:\.\d+)?)px", m.group(0)):
            if number not in breakpoints:
                found.append((m.start(), "media not breakpoint token", f"{number}px"))
    in_media = lambda pos: any(start <= pos < end for start, end in media_spans)
    for name, pattern in RULES:
        found += [(m.start(), name, m.group(0).strip()) for m in pattern.finditer(segment)]
    for m in LENGTH.finditer(segment):
        if m.group(0) not in FREE_LENGTHS and not in_media(m.start()):
            found.append((m.start(), "length or time", m.group(0)))
    for pattern in (UNITLESS_PROPERTY, UNITLESS_ATTRIBUTE):
        for m in pattern.finditer(segment):
            if m.group(2) not in FREE_NUMBERS:
                found.append((m.start(), f"{m.group(1)} number", m.group(0)))
    for m in CUSTOM_PROPERTY.finditer(segment):
        # 토큰만으로 만든 값(`calc(var(--a) * 2)`의 배수 2 같은 순수 숫자 계수 포함)은 허용한다.
        rest = re.sub(r"var\([^()]*\)", "", m.group(2))
        if re.search(r"#|['\"]|\d+(?:px|rem|em|ms|s|%)", rest):
            found.append((m.start(), "custom property outside tokens", f"{m.group(1)}: {m.group(2).strip()}"))
    return found


# cost: time O(n), heap O(n), stack O(1), io 1
# vars: n = 파일 글자 수
# basis: estimate
def check_file(path, breakpoints):
    ext = os.path.splitext(path)[1].lower()
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    if GENERATED_MARK in text.split("\n", 1)[0]:
        return []
    lines = text.split("\n")
    line_starts = [0]
    for line in lines[:-1]:
        line_starts.append(line_starts[-1] + len(line) + 1)
    results = []
    for offset, segment in styled_segments(text, ext):
        for pos, rule, snippet in find_in_segment(segment, breakpoints):
            line_no = line_of(line_starts, offset + pos)
            if ALLOW_MARK in lines[line_no - 1]:
                continue
            results.append((path, line_no, rule, snippet[:80]))
    return results


def line_of(line_starts, pos):
    low, high = 0, len(line_starts) - 1
    while low < high:
        mid = (low + high + 1) // 2
        if line_starts[mid] <= pos:
            low = mid
        else:
            high = mid - 1
    return low + 1


# cost: time O(f), heap O(f), stack O(d), io f
# vars: f = 파일 수, d = 폴더 깊이
# basis: estimate
def iter_files(targets):
    for target in targets:
        if os.path.isfile(target):
            yield target
            continue
        for root, dirs, files in os.walk(target):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for name in sorted(files):
                ext = os.path.splitext(name)[1].lower()
                if name not in TOKEN_FILES and (ext in STYLE_EXTS or ext in SCRIPT_EXTS):
                    yield os.path.join(root, name)


# cost: time O(f + h), heap O(1), stack O(1), io f + h
# vars: f = 대상 아래 파일 수, h = 저장소 루트까지 상위 폴더 수
# basis: estimate
def find_tokens_file(targets):
    """대상 폴더 아래, 없으면 저장소 루트(.git이 있는 폴더)까지 위로 올라가며 tokens.json을 찾는다."""
    for target in targets:
        folder = os.path.abspath(target if os.path.isdir(target) else os.path.dirname(target) or ".")
        for root, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            if "tokens.json" in files:
                return os.path.join(root, "tokens.json")
        while True:
            candidate = os.path.join(folder, "tokens.json")
            if os.path.exists(candidate):
                return candidate
            parent = os.path.dirname(folder)
            if os.path.isdir(os.path.join(folder, ".git")) or parent == folder:
                break
            folder = parent
    return None


# cost: time O(N), heap O(r), stack O(d), io f
# vars: N = 전체 글자 수, r = 찾은 수, f = 파일 수, d = 폴더 깊이
# basis: estimate
def main():
    parser = argparse.ArgumentParser(description="토큰 대신 직접 적은 화면 값을 찾는다")
    parser.add_argument("targets", nargs="+")
    parser.add_argument("--tokens", default=None, help="breakpoint를 읽을 tokens.json. 없으면 대상 폴더에서 찾는다")
    args = parser.parse_args()
    breakpoints = load_breakpoints(args.tokens or find_tokens_file(args.targets))
    results = []
    for path in iter_files(args.targets):
        results += check_file(path, breakpoints)
    results.sort(key=lambda r: (r[0], r[1]))
    for path, line, rule, snippet in results:
        print(f"{path}:{line}: {rule}: {snippet}")
    print(f"total {len(results)}")
    return 1 if results else 0


if __name__ == "__main__":
    sys.exit(main())
