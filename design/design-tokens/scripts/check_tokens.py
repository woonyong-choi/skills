"""토큰 대신 직접 적은 화면 값(하드코딩)을 찾는다.

사용: python3 check_tokens.py <폴더나 파일 ...> [--tokens tokens.json]

출력: `{경로}:{줄}: {규칙}: {찾은 글자}` 줄들과 마지막 `total {개수}`. 개수가 0이 아니면 종료 코드 1.
- CSS 계열: 주석을 뺀 전체
- 마크업 계열: `<style>` 블록, `style` 속성, 색·크기 표현 속성만. 본문 글자는 보지 않는다
- JavaScript 계열: 모든 문자열의 색, CSS·마크업으로 보이는 문자열과 값 하나뿐인 문자열(`'12px'`)의 나머지 규칙,
  코드의 기본 토큰 경로(`tokens.color.blue['600']`)와 스타일 객체 숫자(`{ fontWeight: 600 }`)
- 모든 계열: 색·그림자 기본 토큰 직접 참조(`var(--color-blue-600)`), 토큰 파일 밖 테마 분기(`prefers-color-scheme`, `[data-theme`)

인자: 폴더나 파일 하나 이상, --tokens 토큰 정본
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Iterator

CSS_EXTS = {".css", ".scss"}
MARKUP_EXTS = {".html", ".svg", ".vue", ".svelte"}
SCRIPT_EXTS = {".js", ".mjs", ".cjs", ".ts", ".jsx", ".tsx"}
SKIP_DIRS = {"node_modules", "dist", "build", "coverage", ".git"}
TOKEN_FILES = {"tokens.json", "tokens.dark.json"}
GENERATED_MARK = "생성물, 손으로 고치지 않음"
ALLOW_MARK = "tokens-allow:"
# design-tokens 원칙의 허용 값
FREE_LENGTHS = {"0", "100%", "50%", "100vh", "100vw"}
FREE_NUMBERS = {"0", "1"}
FONT_KEYWORDS = r"(?:inherit|initial|unset|var\()"

HEX_COLOR = re.compile(r"(?<![\w&/])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b")
COLOR_FUNCTION = re.compile(r"\b(?:rgba?|hsla?|oklch|oklab|lab|lch|hwb|color)\(")
FONT_FAMILY = re.compile(rf"font-family\s*:(?!\s*{FONT_KEYWORDS})[^;}}\n]+|\bfont\s*:(?!\s*{FONT_KEYWORDS})[^;}}\n]*(?:serif|monospace|system-ui)")
LENGTH = re.compile(r"(?<![\w.#-])-?\d*\.?\d+(?:px|rem|em|ms|s|vh|vw|pt)\b")
UNITLESS_PROPERTY = re.compile(r"\b(font-weight|line-height|opacity|z-index|letter-spacing)\s*:\s*(-?[\d.]+)\b")
UNITLESS_ATTRIBUTE = re.compile(
    r"\b(rx|ry|stroke-width|font-size|font-weight|opacity|fill-opacity|stroke-opacity|letter-spacing)\s*=\s*"
    r"(?P<quote>['\"])\s*(?P<value>-?[\d.]+)\s*(?P=quote)"
)
CUSTOM_PROPERTY = re.compile(r"(--[\w-]+)\s*:\s*(?!var\()([^;}\n]+)")
AT_CONDITION = re.compile(r"@(?:media|container)[^{]*")
COMMENT = re.compile(r"/\*.*?\*/|<!--.*?-->", re.S)
STRING = re.compile(r"'(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\"|`(?:[^`\\]|\\.)*`", re.S)
STYLE_BLOCK = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)
STYLED_ATTRIBUTE = re.compile(
    r"\b(?:style|fill|stroke|color|stop-color|flood-color|rx|ry|stroke-width|font-size|font-weight|font-family|opacity|fill-opacity|stroke-opacity|letter-spacing)\s*=\s*"
    r"(?P<quote>['\"])[\s\S]*?(?P=quote)",
    re.I,
)
# CSS 선언(`속성: 값;`)이나 마크업 속성(`이름="값"`)이 든 문자열
LOOKS_STYLED = re.compile(r"[\w-]+\s*:\s*[^;]+;|<\w[^>]*=|[\w-]+\s*=\s*['\"]")
# 값 하나뿐인 문자열: `'12px'`, `'1.5rem'`, `'200ms'`
BARE_VALUE = re.compile(r"^['\"`]\s*-?\d*\.?\d+(?:px|rem|em|ms|s|pt)\s*['\"`]$")

VAR_REFERENCE = re.compile(r"var\(\s*(--[\w-]+)")
THEME_BRANCH = re.compile(r"prefers-color-scheme|\[data-theme(?![\w-])")
JS_TOKEN_PATH = re.compile(r"\b(?:tokens|values)((?:\.[A-Za-z_$][\w$]*|\[\s*(?:['\"`][^'\"`]+['\"`]|\d+)\s*\])+)")
JS_PATH_PART = re.compile(r"\.([A-Za-z_$][\w$]*)|\[\s*['\"`]?([^'\"`\]\s]+)['\"`]?\s*\]")
JS_COMMENT_OR_STRING = re.compile(r"(\"(?:[^\"\\\n]|\\.)*\"|'(?:[^'\\\n]|\\.)*'|`(?:[^`\\]|\\.)*`)|//[^\n]*|/\*[\s\S]*?\*/")
# 스타일 객체: `style={{`, `style: {`, `sx: {`, `css: {`, `styles = {` 뒤 중괄호 안만 숫자를 본다.
STYLE_OBJECT_START = re.compile(r"\b(?:style|styles|sx|css)\s*[:=]\s*\{\{?")
STYLE_OBJECT_NUMBER = re.compile(
    r"\b(fontSize|fontWeight|lineHeight|letterSpacing|opacity|zIndex|borderRadius|borderWidth|gap|rowGap|columnGap"
    r"|strokeWidth|top|right|bottom|left|(?:padding|margin|inset)(?:Top|Right|Bottom|Left|Inline|Block)?|(?:min|max)?(?:Width|Height)|width|height)"
    r"\s*:\s*(-?\d+(?:\.\d+)?)\b"
)

# 테마에 따라 바뀌어 의미 토큰으로만 써야 하는 타입
THEMED_TYPES = {"color", "shadow"}

Finding = tuple[str, int, str, str]


class TokenInfo:
    """정본에서 읽은 검사 기준: breakpoint px 숫자, 테마 기본 토큰(색, 그림자)의 CSS 이름과 경로."""

    def __init__(self, breakpoints: set[str], primitive_names: set[str], primitive_paths: set[tuple[str, ...]]) -> None:
        self.breakpoints = breakpoints
        self.primitive_names = primitive_names
        self.primitive_paths = primitive_paths


# cost: time O(t), heap O(t), stack O(1), io 1
# vars: t = 토큰 수
# basis: estimate
def load_token_info(path: str | None) -> TokenInfo:
    """정본에서 breakpoint 숫자와 테마 기본 토큰을 읽는다.

    테마 기본 토큰: 값이 다른 토큰 참조가 아니고 타입이 색이나 그림자인 토큰. 코드는 이 토큰 대신 의미 토큰을 쓴다.
    """
    info = TokenInfo(set(), set(), set())
    if not path:
        return info
    with open(path, encoding="utf-8") as f:
        root = json.load(f)
    stack: list[tuple[tuple[str, ...], dict, str | None]] = [((), root, root.get("$type"))]
    while stack:
        prefix, node, group_type = stack.pop()
        for key, child in node.items():
            if key.startswith("$") or not isinstance(child, dict):
                continue
            token_path = prefix + (key,)
            token_type = child.get("$type", group_type)
            if "$value" not in child:
                stack.append((token_path, child, token_type))
                continue
            value = child["$value"]
            if token_path[0] == "breakpoint":
                raw = value.get("value") if isinstance(value, dict) else value
                info.breakpoints.add(re.sub(r"px$", "", str(raw)))
            is_reference = bool(re.search(r"\{[\w.-]+\}", json.dumps(value)))
            if not is_reference and token_type in THEMED_TYPES:
                info.primitive_names.add("--" + "-".join(token_path))
                info.primitive_paths.add(token_path)
    return info


# cost: time O(n), heap O(n), stack O(1)
# vars: n = 글자 수
# basis: estimate
def find_segments(text: str, ext: str) -> list[tuple[int, str, bool]]:
    """검사할 조각. (시작 위치, 글자, 모든 규칙 적용 여부) 목록. False면 색 규칙만 적용한다."""
    text = COMMENT.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)
    if ext in CSS_EXTS:
        return [(0, text, True)]
    if ext in MARKUP_EXTS:
        segments = [(m.start(1), m.group(1), True) for m in STYLE_BLOCK.finditer(text)]
        segments += [(m.start(), m.group(0), True) for m in STYLED_ATTRIBUTE.finditer(text)]
        return segments
    return [(m.start(), m.group(0), is_styled_string(m.group(0))) for m in STRING.finditer(text)]


def is_styled_string(literal: str) -> bool:
    """CSS나 마크업으로 보이거나 값 하나뿐인 문자열인지 본다."""
    return bool(LOOKS_STYLED.search(literal) or BARE_VALUE.match(literal))


# cost: time O(n), heap O(f), stack O(1)
# vars: n = 조각 글자 수, f = 찾은 수
# basis: estimate
def find_hardcoded(segment: str, info: TokenInfo, is_styled: bool) -> list[tuple[int, str, str]]:
    """조각 안 하드코딩. (조각 안 위치, 규칙, 글자) 목록. 한 자리는 한 번만 보고한다."""
    found = [(m.start(), "hex color", m.group(0)) for m in HEX_COLOR.finditer(segment)]
    found += [(m.start(), "color function", m.group(0)) for m in COLOR_FUNCTION.finditer(segment)]
    found += [(m.start(), "primitive token reference", m.group(1)) for m in VAR_REFERENCE.finditer(segment) if m.group(1) in info.primitive_names]
    found += [(m.start(), "theme branch outside tokens", m.group(0)) for m in THEME_BRANCH.finditer(segment)]
    if not is_styled:
        return found
    conditions = [(m.start(), m.end()) for m in AT_CONDITION.finditer(segment) if "prefers-color-scheme" not in m.group(0)]
    for start, end in conditions:
        found += find_condition_values(segment[start:end], start, info.breakpoints)
    reported = [(m.start(), m.end()) for m in CUSTOM_PROPERTY.finditer(segment) if is_raw_custom_value(m.group(2))]
    skip = conditions + reported
    found = [f for f in found if not is_inside(f[0], reported)]
    found += [(start, "custom property outside tokens", segment[start:end].strip()) for start, end in reported]
    found += [(m.start(), "font family", m.group(0).strip()) for m in FONT_FAMILY.finditer(segment) if not is_inside(m.start(), skip)]
    found += [(m.start(), "length or time", m.group(0)) for m in LENGTH.finditer(segment) if m.group(0) not in FREE_LENGTHS and not is_inside(m.start(), skip)]
    for pattern in (UNITLESS_PROPERTY, UNITLESS_ATTRIBUTE):
        for match in pattern.finditer(segment):
            number = match.group("value") if "value" in pattern.groupindex else match.group(2)
            if number not in FREE_NUMBERS and not is_inside(match.start(), reported):
                found.append((match.start(), f"{match.group(1)} number", match.group(0)))
    return found


# cost: time O(n), heap O(f), stack O(1)
# vars: n = 조건 글자 수, f = 찾은 수
# basis: estimate
def find_condition_values(condition: str, offset: int, breakpoints: set[str]) -> list[tuple[int, str, str]]:
    """`@media`, `@container` 조건의 숫자. px가 아닌 단위와 breakpoint 토큰에 없는 px를 찾는다."""
    found = []
    for m in re.finditer(r"(\d+(?:\.\d+)?)(px|em|rem)\b", condition):
        if m.group(2) != "px" or m.group(1) not in breakpoints:
            found.append((offset + m.start(), "condition not breakpoint token", m.group(0)))
    return found


# cost: time O(n), heap O(n), stack O(1)
# vars: n = 값 글자 수
# basis: estimate
def is_raw_custom_value(value: str) -> bool:
    """토큰 참조만으로 만든 값이 아닌지 본다. `calc(var(--a) * 2)`의 계수 2는 허용한다."""
    rest = re.sub(r"var\([^()]*\)", "", value)
    return bool(re.search(r"#|['\"]|\d+(?:px|rem|em|ms|s|%)", rest))


# cost: time O(k), heap O(1), stack O(1)
# vars: k = 구간 수
# basis: estimate
def is_inside(position: int, spans: list[tuple[int, int]]) -> bool:
    """위치가 구간 중 하나 안에 있는지 본다."""
    return any(start <= position < end for start, end in spans)


def has_allow_reason(line: str) -> bool:
    match = re.search(r"(?:/\*|//|<!--)[^\n]*tokens-allow:\s*(.*?)\s*(?:\*/|-->|$)", line)
    return bool(match and match.group(1).strip())


# cost: time O(n + f log l), heap O(n), stack O(1), io 1
# vars: n = 파일 글자 수, f = 찾은 수, l = 줄 수
# basis: estimate
def check_file(path: str, info: TokenInfo) -> list[Finding]:
    """파일 하나의 하드코딩. 생성물과 `tokens-allow:` 줄은 건너뛴다."""
    ext = os.path.splitext(path)[1].lower()
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    if GENERATED_MARK in text.split("\n", 1)[0]:
        return []
    lines = text.split("\n")
    line_starts = [0]
    for line in lines[:-1]:
        line_starts.append(line_starts[-1] + len(line) + 1)
    if ext in SCRIPT_EXTS:
        text = strip_js_comments(text)
    found = [(offset + pos, rule, snippet) for offset, segment, is_styled in find_segments(text, ext) for pos, rule, snippet in find_hardcoded(segment, info, is_styled)]
    if ext in SCRIPT_EXTS:
        found += find_script_values(text, info)
    results = [(path, number, "empty tokens-allow reason", ALLOW_MARK)
               for number, line in enumerate(lines, 1)
               if re.search(r"(?:/\*|//|<!--)[^\n]*tokens-allow:", line) and not has_allow_reason(line)]
    for pos, rule, snippet in found:
        line_number = find_line_number(line_starts, pos)
        if not has_allow_reason(lines[line_number - 1]):
            results.append((path, line_number, rule, snippet[:80]))
    return results


# cost: time O(n), heap O(n), stack O(1)
# vars: n = 파일 글자 수
# basis: estimate
def strip_js_comments(text: str) -> str:
    """문자열은 두고 `//`, `/* */` 주석만 같은 길이의 공백으로 바꾼다. 줄 번호를 지키기 위해서다."""
    return JS_COMMENT_OR_STRING.sub(lambda m: m.group(1) or re.sub(r"[^\n]", " ", m.group(0)), text)


# cost: time O(n), heap O(n), stack O(1)
# vars: n = 파일 글자 수
# basis: estimate
def find_script_values(text: str, info: TokenInfo) -> list[tuple[int, str, str]]:
    """JavaScript 코드의 색·그림자 기본 토큰 경로 참조와 스타일 객체 숫자. 주석은 이미 지운 글자를 받는다."""
    found = []
    # 일반 문자열 안 글자는 코드가 아니다. `['600']` 같은 경로 키와 템플릿 문자열은 남긴다.
    code_and_templates = re.sub(r"(?<!\[)\s*('(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\")", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)
    for m in JS_TOKEN_PATH.finditer(code_and_templates):
        token_path = tuple(a or b for a, b in JS_PATH_PART.findall(m.group(1)))
        if token_path in info.primitive_paths:
            found.append((m.start(), "primitive token reference", m.group(0)))
    code = STRING.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)
    for start, end in find_style_objects(code):
        found += [(start + m.start(), f"{m.group(1)} number", m.group(0)) for m in STYLE_OBJECT_NUMBER.finditer(code[start:end]) if m.group(2) not in FREE_NUMBERS]
    return found


# cost: time O(n), heap O(s), stack O(1)
# vars: n = 코드 글자 수, s = 스타일 객체 수
# basis: estimate
def find_style_objects(code: str) -> list[tuple[int, int]]:
    """스타일 객체 중괄호 구간. 여는 중괄호부터 짝이 맞는 닫는 중괄호까지."""
    spans = []
    for m in STYLE_OBJECT_START.finditer(code):
        depth = 0
        for position in range(m.end() - 1, len(code)):
            depth += {"{": 1, "}": -1}.get(code[position], 0)
            if depth == 0:
                spans.append((m.end(), position))
                break
    return spans


# cost: time O(log l), heap O(1), stack O(1)
# vars: l = 줄 수
# basis: estimate
def find_line_number(line_starts: list[int], position: int) -> int:
    """글자 위치의 줄 번호(1부터). 줄 시작 위치 목록에서 이분 탐색한다."""
    low, high = 0, len(line_starts) - 1
    while low < high:
        mid = (low + high + 1) // 2
        if line_starts[mid] <= position:
            low = mid
        else:
            high = mid - 1
    return low + 1


# cost: time O(f), heap O(d), stack O(d), io f
# vars: f = 파일 수, d = 폴더 깊이
# basis: estimate
def iter_files(targets: list[str]) -> Iterator[str]:
    """검사할 파일 경로. 폴더는 정렬 순서로 내려간다."""
    for target in targets:
        if os.path.isfile(target):
            yield target
            continue
        for root, dirs, files in os.walk(target):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for name in sorted(files):
                ext = os.path.splitext(name)[1].lower()
                if name not in TOKEN_FILES and ext in CSS_EXTS | MARKUP_EXTS | SCRIPT_EXTS:
                    yield os.path.join(root, name)


# cost: time O(f + h), heap O(1), stack O(1), io f + h
# vars: f = 대상 아래 파일 수, h = 저장소 루트까지 상위 폴더 수
# basis: estimate
def find_tokens_file(targets: list[str]) -> str | None:
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
def main() -> int:
    """찾은 하드코딩을 출력한다. 하나라도 있으면 1을 돌려준다."""
    parser = argparse.ArgumentParser(description="토큰 대신 직접 적은 화면 값을 찾는다")
    parser.add_argument("targets", nargs="+")
    parser.add_argument("--tokens", default=None, help="breakpoint를 읽을 tokens.json. 없으면 대상 폴더와 상위 폴더에서 찾는다")
    args = parser.parse_args()
    tokens_path = args.tokens or find_tokens_file(args.targets)
    if not tokens_path:
        print("tokens.json not found: every @media and @container number is reported, primitive references are not checked", file=sys.stderr)
    info = load_token_info(tokens_path)
    results = [finding for path in iter_files(args.targets) for finding in check_file(path, info)]
    results.sort(key=lambda r: (r[0], r[1]))
    for path, line, rule, snippet in results:
        print(f"{path}:{line}: {rule}: {snippet}")
    print(f"total {len(results)}")
    return 1 if results else 0


if __name__ == "__main__":
    sys.exit(main())
