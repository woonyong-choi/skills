"""토큰 정본(tokens.json, 선택으로 tokens.dark.json)에서 tokens.css와 tokens.js를 만든다.

사용: python3 build_tokens.py tokens.json [--out 폴더]

정본 형식: W3C Design Tokens. 토큰은 `$value`가 있는 객체, 묶음의 `$type`은 안쪽 토큰에 이어진다.
참조 `{color.blue.600}`는 CSS에서 `var(--color-blue-600)`로 남겨 테마를 바꿀 때 따라 바뀌게 한다.
"""
import argparse
import json
import os
import re
import sys

REFERENCE = re.compile(r"^\{([^{}]+)\}$")
HEADER = "생성물, 손으로 고치지 않음"


# cost: time O(t), heap O(t), stack O(d), alloc t
# vars: t = 토큰 수, d = 묶음 깊이
# basis: estimate
def flatten(node, path=(), inherited_type=None):
    """정본을 (경로, 값, 타입) 목록으로 편다."""
    tokens = []
    group_type = node.get("$type", inherited_type)
    for key, child in node.items():
        if key.startswith("$") or not isinstance(child, dict):
            continue
        if "$value" in child:
            tokens.append((path + (key,), child["$value"], child.get("$type", group_type)))
        else:
            tokens.extend(flatten(child, path + (key,), group_type))
    return tokens


def css_name(path):
    return "--" + "-".join(path)


# cost: time O(1), heap O(1), stack O(1)
# basis: estimate
def format_value(value, token_type):
    """참조가 아닌 값을 CSS 값으로 바꾼다. 숫자는 타입에 맞는 단위를 붙인다."""
    if isinstance(value, dict) and "value" in value and "unit" in value:
        return f"{value['value']}{value['unit']}"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if token_type == "dimension":
            return f"{value}px"
        if token_type == "duration":
            return f"{value}ms"
        return str(value)
    if isinstance(value, list) and token_type == "fontFamily":
        return ", ".join(f"'{name}'" if " " in name else name for name in value)
    if isinstance(value, list) and token_type == "cubicBezier":
        return "cubic-bezier(" + ", ".join(str(v) for v in value) + ")"
    if isinstance(value, dict) and token_type == "shadow":
        parts = [value.get(k, 0) for k in ("offsetX", "offsetY", "blur", "spread")]
        return " ".join(format_value(p, "dimension") for p in parts) + f" {value.get('color', 'transparent')}"
    return str(value)


# cost: time O(t·d), heap O(t), stack O(d)
# vars: t = 토큰 수, d = 참조 사슬 길이
# basis: estimate
def resolve(path, table, seen=()):
    """참조를 끝까지 따라가 실제 값과 타입을 얻는다."""
    if path in seen:
        raise ValueError("token reference cycle: " + " -> ".join(".".join(p) for p in seen + (path,)))
    value, token_type = table[path]
    match = REFERENCE.match(value) if isinstance(value, str) else None
    if not match:
        return value, token_type
    target = tuple(match.group(1).split("."))
    if target not in table:
        raise ValueError(f"unknown token reference: {'.'.join(path)} -> {match.group(1)}")
    return resolve(target, table, seen + (path,))


def css_value(value, token_type):
    match = REFERENCE.match(value) if isinstance(value, str) else None
    return f"var({css_name(tuple(match.group(1).split('.')))})" if match else format_value(value, token_type)


# cost: time O(t), heap O(t), stack O(1)
# vars: t = 토큰 수
# basis: estimate
def build_css(source, tokens, dark_tokens):
    lines = [f"/* {source}: {HEADER} */", ":root {"]
    lines += [f"  {css_name(p)}: {css_value(v, t)};" for p, v, t in tokens]
    lines.append("}")
    if dark_tokens:
        body = [f"    {css_name(p)}: {css_value(v, t)};" for p, v, t in dark_tokens]
        lines += ["@media (prefers-color-scheme: dark) {", "  :root:not([data-theme='light']) {", *body, "  }", "}"]
        lines += ["[data-theme='dark'] {", *[line[2:] for line in body], "}"]
    return "\n".join(lines) + "\n"


# cost: time O(t·d), heap O(t), stack O(g)
# vars: t = 토큰 수, d = 참조 사슬 길이, g = 묶음 깊이
# basis: estimate
def build_js(source, tokens, table):
    refs = {}
    values = {}
    for path, _, _ in tokens:
        value, token_type = resolve(path, table)
        set_path(refs, path, f"var({css_name(path)})")
        set_path(values, path, value if isinstance(value, (int, float)) and token_type in ("dimension", "number", "fontWeight", "duration") else format_value(value, token_type))
    return (
        f"// {source}: {HEADER}\n"
        "const freeze = (node) => (typeof node === 'object' ? Object.freeze(Object.fromEntries(Object.entries(node).map(([k, v]) => [k, freeze(v)]))) : node);\n\n"
        "/** CSS에 넣을 토큰 참조. 값은 `var(--…)` 문자열이다. */\n"
        f"export const tokens = freeze({json.dumps(refs, ensure_ascii=False, indent=2)});\n\n"
        "/** 배치 계산에 쓸 밝은 테마의 실제 값. 크기는 px 숫자다. */\n"
        f"export const values = freeze({json.dumps(values, ensure_ascii=False, indent=2)});\n"
    )


def set_path(tree, path, value):
    for key in path[:-1]:
        tree = tree.setdefault(key, {})
    tree[path[-1]] = value


# cost: time O(t·d), heap O(t), stack O(g), io 4
# vars: t = 토큰 수, d = 참조 사슬 길이, g = 묶음 깊이
# basis: estimate
def main():
    parser = argparse.ArgumentParser(description="tokens.json에서 tokens.css와 tokens.js를 만든다")
    parser.add_argument("source")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    out = args.out or os.path.dirname(os.path.abspath(args.source))
    with open(args.source, encoding="utf-8") as f:
        tokens = flatten(json.load(f))
    dark_path = os.path.join(os.path.dirname(args.source), "tokens.dark.json")
    dark_tokens = []
    if os.path.exists(dark_path):
        with open(dark_path, encoding="utf-8") as f:
            dark_tokens = flatten(json.load(f))
    table = {p: (v, t) for p, v, t in tokens}
    unknown = [".".join(p) for p, _, _ in dark_tokens if p not in table]
    if unknown:
        print("tokens.dark.json has tokens missing from tokens.json: " + ", ".join(unknown), file=sys.stderr)
        return 1
    try:
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


if __name__ == "__main__":
    sys.exit(main())
