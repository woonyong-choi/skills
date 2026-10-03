"""토큰 정본(tokens.json, 선택으로 tokens.dark.json)에서 tokens.css와 tokens.js를 만든다.

사용: python3 build_tokens.py tokens.json [--out 폴더]

정본 형식: DTCG(Design Tokens Community Group) 2025.10. 토큰은 `$value`가 있는 객체이고,
묶음의 `$type`은 안쪽 토큰에 이어진다. 참조 `{color.blue.600}`는 CSS에서 `var(--color-blue-600)`로 남겨
테마를 바꾸면 따라 바뀌게 한다.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

REFERENCE = re.compile(r"^\{([^{}]+)\}$")
HEADER = "생성물, 손으로 고치지 않음"
# values 객체에 px 숫자로 넣는 타입. 배치 계산에 쓴다.
NUMERIC_TYPES = {"dimension", "number", "fontWeight", "duration"}

Path = tuple[str, ...]
Token = tuple[Path, Any, "str | None"]


# cost: time O(t), heap O(t), stack O(d), alloc t
# vars: t = 토큰 수, d = 묶음 깊이
# basis: estimate
def flatten_tokens(node: dict, path: Path = (), inherited_type: str | None = None) -> list[Token]:
    """정본을 (경로, 값, 타입) 목록으로 편다."""
    tokens: list[Token] = []
    group_type = node.get("$type", inherited_type)
    for key, child in node.items():
        if key.startswith("$") or not isinstance(child, dict):
            continue
        if "$value" in child:
            tokens.append((path + (key,), child["$value"], child.get("$type", group_type)))
        else:
            tokens.extend(flatten_tokens(child, path + (key,), group_type))
    return tokens


# cost: time O(g), heap O(g), stack O(1)
# vars: g = 경로 길이
# basis: estimate
def to_css_name(path: Path) -> str:
    """토큰 경로를 CSS 사용자 정의 속성 이름으로 바꾼다."""
    return "--" + "-".join(path)


def parse_reference(value: Any) -> Path | None:
    """`{a.b}` 참조면 경로, 아니면 None."""
    match = REFERENCE.match(value) if isinstance(value, str) else None
    return tuple(match.group(1).split(".")) if match else None


# cost: time O(k), heap O(k), stack O(1)
# vars: k = 합성 값의 부분 수(그림자 네 값, 글꼴 목록 등)
# basis: estimate
def to_css_value(value: Any, token_type: str | None) -> str:
    """토큰 값을 CSS 값으로 바꾼다. 참조는 `var()`, 숫자는 타입에 맞는 단위를 붙인다."""
    reference = parse_reference(value)
    if reference:
        return f"var({to_css_name(reference)})"
    if isinstance(value, dict) and "unit" in value and "value" in value:
        return f"{value['value']}{value['unit']}"
    if isinstance(value, dict) and "colorSpace" in value:
        return format_color(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        unit = {"dimension": "px", "duration": "ms"}.get(token_type or "", "")
        return f"{value}{unit}"
    if isinstance(value, list) and token_type == "fontFamily":
        return ", ".join(f"'{name}'" if " " in name else name for name in value)
    if isinstance(value, list) and token_type == "cubicBezier":
        return "cubic-bezier(" + ", ".join(str(v) for v in value) + ")"
    if isinstance(value, dict) and token_type == "shadow":
        sizes = [to_css_value(value.get(k, 0), "dimension") for k in ("offsetX", "offsetY", "blur", "spread")]
        return " ".join(sizes) + " " + to_css_value(value.get("color", "transparent"), "color")
    return str(value)


# cost: time O(k), heap O(k), stack O(1)
# vars: k = 색 성분 수
# basis: estimate
def format_color(color: dict) -> str:
    """DTCG 2025.10 색 객체. 불투명하고 `hex`가 있으면 hex, 아니면 CSS 색 함수로 쓴다."""
    alpha = color.get("alpha", 1)
    if color.get("hex") and alpha == 1:
        return color["hex"].lower()
    space = color["colorSpace"]
    parts = " ".join(str(c) for c in color["components"])
    suffix = "" if alpha == 1 else f" / {alpha}"
    if space in ("oklch", "oklab", "lab", "lch", "hsl", "hwb"):
        return f"{space}({parts}{suffix})"
    return f"color({space} {parts}{suffix})"


# cost: time O(c), heap O(c), stack O(c)
# vars: c = 참조 사슬 길이
# basis: estimate
def resolve_token(path: Path, table: dict[Path, tuple[Any, str | None]], seen: tuple[Path, ...] = ()) -> tuple[Any, str | None]:
    """참조를 끝까지 따라가 실제 값과 타입을 얻는다.

    Raises:
        ValueError: 없는 토큰을 참조하거나 참조가 돌 때
    """
    if path in seen:
        raise ValueError("token reference cycle: " + " -> ".join(".".join(p) for p in seen + (path,)))
    value, token_type = table[path]
    target = parse_reference(value)
    if not target:
        return value, token_type
    if target not in table:
        raise ValueError(f"unknown token reference: {'.'.join(path)} -> {'.'.join(target)}")
    return resolve_token(target, table, seen + (path,))


# cost: time O(t·c), heap O(t), stack O(c)
# vars: t = 토큰 수, c = 참조 사슬 길이
# basis: estimate
def check_references(tokens: list[Token], table: dict[Path, tuple[Any, str | None]], source: str) -> None:
    """모든 토큰의 참조가 정본 안에 있는지 확인한다.

    Raises:
        ValueError: 없는 토큰 참조, 도는 참조, 정본에 없는 다크 토큰
    """
    for path, value, _ in tokens:
        if path not in table:
            raise ValueError(f"{source} has a token missing from tokens.json: {'.'.join(path)}")
        target = parse_reference(value)
        if target and target not in table:
            raise ValueError(f"unknown token reference in {source}: {'.'.join(path)} -> {'.'.join(target)}")
        resolve_token(path, table)


# cost: time O(t), heap O(t), stack O(1)
# vars: t = 토큰 수
# basis: estimate
def build_css(source: str, tokens: list[Token], dark_tokens: list[Token]) -> str:
    """`:root` 토큰과 다크 모드 덮어쓰기 CSS를 만든다."""
    lines = [f"/* {source}: {HEADER} */", ":root {"]
    lines += [f"  {to_css_name(p)}: {to_css_value(v, t)};" for p, v, t in tokens]
    lines.append("}")
    if dark_tokens:
        body = [f"{to_css_name(p)}: {to_css_value(v, t)};" for p, v, t in dark_tokens]
        lines += ["@media (prefers-color-scheme: dark) {", "  :root:not([data-theme='light']) {"]
        lines += [f"    {line}" for line in body]
        lines += ["  }", "}", "[data-theme='dark'] {"]
        lines += [f"  {line}" for line in body]
        lines.append("}")
    return "\n".join(lines) + "\n"


# cost: time O(t·c), heap O(t), stack O(g)
# vars: t = 토큰 수, c = 참조 사슬 길이, g = 묶음 깊이
# basis: estimate
def build_js(source: str, tokens: list[Token], table: dict[Path, tuple[Any, str | None]]) -> str:
    """토큰 참조 객체(`var(--…)`)와 계산용 값 객체를 담은 ES 모듈을 만든다."""
    refs: dict = {}
    values: dict = {}
    for path, _, _ in tokens:
        value, token_type = resolve_token(path, table)
        set_path(refs, path, f"var({to_css_name(path)})")
        set_path(values, path, to_number(value, token_type) if token_type in NUMERIC_TYPES else to_css_value(value, token_type))
    return (
        f"// {source}: {HEADER}\n"
        "function freeze(node) {\n"
        "  if (typeof node !== 'object') return node;\n"
        "  return Object.freeze(Object.fromEntries(Object.entries(node).map(([key, value]) => [key, freeze(value)])));\n"
        "}\n\n"
        "/** CSS에 넣을 토큰 참조. 값은 `var(--…)` 문자열이다. */\n"
        f"export const tokens = freeze({json.dumps(refs, ensure_ascii=False, indent=2)});\n\n"
        "/** 배치 계산에 쓸 밝은 테마의 실제 값. px와 s·ms만 단위 없는 숫자로 바꾼다. */\n"
        f"export const values = freeze({json.dumps(values, ensure_ascii=False, indent=2)});\n"
    )


def to_number(value: Any, token_type: str | None) -> Any:
    """계산 가능한 px와 시간만 단위 없는 숫자로 바꾼다. 문맥이 필요한 단위는 CSS 값으로 남긴다."""
    if isinstance(value, dict) and "value" in value:
        unit = value.get("unit")
        number = value["value"]
        if token_type == "dimension" and unit == "px":
            return number
        if token_type == "duration" and unit == "ms":
            return number
        if token_type == "duration" and unit == "s" and isinstance(number, (int, float)):
            return number * 1000
        return to_css_value(value, token_type)
    if isinstance(value, str):
        match = re.fullmatch(r"(-?\d+(?:\.\d+)?)(px|ms|s)?", value)
        if not match:
            return value
        number = float(match.group(1))
        unit = match.group(2)
        if token_type == "dimension" and unit == "px":
            return number
        if token_type == "duration" and unit == "ms":
            return number
        if token_type == "duration" and unit == "s":
            return number * 1000
        if token_type in {"number", "fontWeight"} and unit is None:
            return number
        return value
    return value


# cost: time O(g), heap O(g), stack O(1), alloc g
# vars: g = 경로 길이
# basis: estimate
def set_path(tree: dict, path: Path, value: Any) -> None:
    """중첩 객체의 경로 자리에 값을 둔다."""
    for key in path[:-1]:
        tree = tree.setdefault(key, {})
    tree[path[-1]] = value


# cost: time O(t·c), heap O(t), stack O(g), io 4
# vars: t = 토큰 수, c = 참조 사슬 길이, g = 묶음 깊이
# basis: estimate
def main() -> int:
    """정본을 읽어 생성물 두 개를 쓴다. 참조 오류가 있으면 쓰지 않고 1을 돌려준다."""
    parser = argparse.ArgumentParser(description="tokens.json에서 tokens.css와 tokens.js를 만든다")
    parser.add_argument("source")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    out = args.out or os.path.dirname(os.path.abspath(args.source))
    tokens = flatten_tokens(read_json(args.source))
    dark_path = os.path.join(os.path.dirname(args.source), "tokens.dark.json")
    dark_tokens = flatten_tokens(read_json(dark_path)) if os.path.exists(dark_path) else []
    table = {p: (v, t) for p, v, t in tokens}
    try:
        check_references(tokens, table, "tokens.json")
        for path, _, _ in dark_tokens:
            if path not in table:
                raise ValueError(f"tokens.dark.json has a token missing from tokens.json: {'.'.join(path)}")
        dark_table = dict(table)
        dark_table.update({path: (value, token_type) for path, value, token_type in dark_tokens})
        check_references(dark_tokens, dark_table, "tokens.dark.json")
        css = build_css(os.path.basename(args.source), tokens, dark_tokens)
        js = build_js(os.path.basename(args.source), tokens, table)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    os.makedirs(out, exist_ok=True)
    for name, text in (("tokens.css", css), ("tokens.js", js)):
        path = os.path.join(out, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print(path)
    return 0


# cost: time O(n), heap O(n), stack O(1), io 1
# vars: n = 파일 글자 수
# basis: estimate
def read_json(path: str) -> dict:
    """JSON 파일을 읽는다."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    sys.exit(main())
