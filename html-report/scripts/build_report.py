"""질문 목록 JSON에서 그림 보고서(결정, 결과) index.html 한 장을 만든다.

사용: python3 build_report.py <입력.json> [출력.html]
출력 기본값은 입력 파일 옆의 index.html. 그림 경로는 입력 파일 폴더 기준.
"""
import html
import json
import re
import sys
from pathlib import Path

CSS = """
:root{--ink:#1c2025;--sub:#667;--line:#c9ced6;--tline:#dfe3e8;--pane:#f3f4f6;--blue:#2b78d9;--orange:#eb6834;--bg:#fafbfc;--nav-offset:calc(4 * 24px)}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{font-family:'Inter Variable',Inter,'Noto Sans KR Variable','Noto Sans KR','Apple SD Gothic Neo',sans-serif;font-size:15px;line-height:1.6;max-width:1340px;margin:0 auto;padding:24px;color:var(--ink);background:var(--bg)}
h1{font-size:26px;margin:0 0 8px}
h2{margin:0 0 8px;font-size:21px;border-bottom:2px solid var(--blue);padding-bottom:6px}
h3{font-size:16px;margin:18px 0 6px}
h4{margin:0 0 6px;font-size:15px;line-height:1.4}
section{scroll-margin-top:var(--nav-offset);margin:36px 0}
.cols{display:grid;gap:16px;align-items:start;margin:10px 0}
.c1{grid-template-columns:1fr}.c2{grid-template-columns:repeat(2,minmax(0,1fr))}
.c3{grid-template-columns:repeat(3,minmax(0,1fr))}.c4{grid-template-columns:repeat(4,minmax(0,1fr))}
.col{padding:0;min-width:0}
.col.mock{border:4px dashed var(--orange);padding:9px}
.frame{display:flex;align-items:center;justify-content:center;background:var(--pane);padding:4px}
.frame img{display:block;width:100%;height:auto;max-height:var(--max-h,360px);object-fit:contain}
figure{margin:0 0 10px}figure:last-child{margin-bottom:0}
figcaption{font-size:12px;color:var(--sub);margin-top:4px}
pre.msg{white-space:pre-wrap;word-break:break-all;background:#f3f4f6;padding:8px;border-radius:6px;font-size:12px;margin:8px 0 0}
figure+pre.msg{margin-top:0}
table{border-collapse:collapse;width:100%;table-layout:fixed}
th,td{border:1px solid var(--tline);padding:6px 10px;vertical-align:middle;font-size:14px;text-align:left;overflow-wrap:anywhere}
thead th{background:#f5f7fa}
.al-center{text-align:center}.al-right{text-align:right;font-variant-numeric:tabular-nums}
.effect{margin-top:12px}.effect th:first-child,.effect td:first-child{width:64px;text-align:center}
.effect td{vertical-align:top}
.rec{background:#eef5ff;border-left:4px solid var(--blue);padding:8px 12px;margin:12px 0 0}
.check{margin:12px 0 0}.check ul{margin:4px 0 0;padding-left:20px}
.note{font-size:13px;color:var(--sub);margin:8px 0 0}
.what{margin:6px 0}
code{font-family:'JetBrains Mono Variable','JetBrains Mono',ui-monospace,monospace;font-size:12px;white-space:normal}
nav{position:sticky;top:0;z-index:1;display:flex;flex-wrap:wrap;gap:6px;margin:8px 0;padding:8px 0;background:var(--bg);border-bottom:1px solid var(--line)}
nav a{display:inline-flex;align-items:center;gap:6px;min-height:24px;max-width:calc(16 * 21px);padding:4px 8px;color:var(--ink);text-decoration:none;background:var(--pane);border-radius:6px}
nav a:hover,nav a:focus-visible{background:var(--tline)}nav a.is-active{color:var(--pane);background:var(--ink)}
.nav-title{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
@media print{nav{display:none}}
"""


class ReportError(Exception):
    """입력이 틀렸을 때 던진다. main이 `build_report.py: 메시지`로 바꿔 종료한다."""


ALIGNS = ("left", "center", "right")
MAX_COLUMNS = 4
NAV_TITLE_MAX_LENGTH = 24


# cost: time O(1), heap O(1), stack O(1)
# basis: estimate
def _need(obj, key, where, kind=None):
    if not isinstance(obj, dict) or key not in obj:
        raise ReportError(f"{where} is missing required field {key}")
    value = obj[key]
    if kind is not None and not isinstance(value, kind):
        raise ReportError(f"{where}.{key} must be {kind.__name__}")
    if kind in (str, list) and not value:
        raise ReportError(f"{where}.{key} must not be empty")
    return value


# cost: time O(rows * cols), heap O(1), stack O(1)
# vars: rows = table rows, cols = table columns
# basis: estimate
def _check_table(spec, where):
    _need(spec, "head", where, list)
    for r, row in enumerate(_need(spec, "rows", where, list)):
        if not isinstance(row, list):
            raise ReportError(f"{where}.rows[{r}] must be list")
    for a in spec.get("align", []):
        if a not in ALIGNS:
            raise ReportError(f"{where}.align must be one of {list(ALIGNS)}: {a}")


# cost: time O(options), heap O(1), stack O(1)
# vars: options = options in one row of columns
# basis: estimate
def _check_options(opts, where):
    if len(opts) > MAX_COLUMNS:
        raise ReportError(f"{where} has {len(opts)} options, at most {MAX_COLUMNS} allowed")
    for k, opt in enumerate(opts):
        at = f"{where}[{k}]"
        _need(opt, "label", at, str)
        for m, img in enumerate(opt.get("images", [])):
            _need(img, "src", f"{at}.images[{m}]", str)
        if "table" in opt:
            _check_table(opt["table"], f"{at}.table")


# cost: time O(options + effect rows), heap O(1), stack O(1)
# basis: estimate
def _check_question(q, where):
    _need(q, "title", where, str)
    _need(q, "what", where, str)
    _check_options(_need(q, "options", where, list), f"{where}.options")
    for r, row in enumerate(_need(q, "effect", where, list)):
        if not isinstance(row, list) or len(row) != 3:
            raise ReportError(f"{where}.effect[{r}] must have 3 cells")
    if len(_need(q, "rec", where, list)) != 2:
        raise ReportError(f"{where}.rec must have 2 items")
    for e, extra in enumerate(q.get("extra", [])):
        _need(extra, "title", f"{where}.extra[{e}]", str)
        _check_options(_need(extra, "options", f"{where}.extra[{e}]", list), f"{where}.extra[{e}].options")


# cost: time O(questions * options), heap O(1), stack O(1)
# basis: estimate
def _validate(spec):
    kind = spec.get("kind", "decision") if isinstance(spec, dict) else None
    if kind not in KINDS:
        raise ReportError(f"kind must be one of {sorted(KINDS)}: {kind}")
    _need(spec, "title", "input", str)
    _need(spec, "intro", "input", str)
    for n, q in enumerate(_need(spec, "questions", "input", list), 1):
        _check_question(q, f"questions[{n}]")


# cost: time O(n), heap O(n), stack O(1)
# vars: n = len(text)
# basis: estimate
def _inline(text):
    """이스케이프 뒤 `코드`만 code 태그로 바꾼다."""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(text))


# cost: time O(n), heap O(n), stack O(1)
# vars: n = len(title)
# basis: estimate
def _nav_title(title: str) -> str:
    if len(title) <= NAV_TITLE_MAX_LENGTH:
        return title
    return title[:NAV_TITLE_MAX_LENGTH - 1] + "…"


# cost: time O(1), heap O(1), stack O(1), io 1
# basis: estimate
def _picture(img, base):
    src = img["src"]
    if not (base / src).is_file():
        raise ReportError(f"image not found: {base / src}")
    alt = html.escape(img.get("alt", ""))
    try:
        style = f' style="--max-h:{int(img["max_height"])}px"' if "max_height" in img else ""
    except (TypeError, ValueError):
        raise ReportError(f"max_height must be a number: {img['max_height']}") from None
    cap = f"<figcaption>{alt}</figcaption>" if alt else ""
    return (f'<figure><div class="frame"{style}><img src="{html.escape(src)}" alt="{alt}"></div>'
            f"{cap}</figure>")


# cost: time O(rows * cols), heap O(rows * cols)
def _table(spec):
    aligns = spec.get("align", [])
    widths = spec.get("widths", [])

    def cls(i, extra=""):
        names = [f"al-{aligns[i]}"] if i < len(aligns) and aligns[i] != "left" else []
        names += [extra] if extra else []
        return f' class="{" ".join(names)}"' if names else ""

    cols = "".join(f'<col style="width:{html.escape(w)}">' for w in widths)
    colgroup = f"<colgroup>{cols}</colgroup>" if widths else ""
    head = "".join(f"<th{cls(i)}>{_inline(h)}</th>" for i, h in enumerate(spec["head"]))
    rows = ""
    for row in spec["rows"]:
        cells = "".join(f"<td{cls(i)}>{_inline(c)}</td>" for i, c in enumerate(row))
        rows += f"<tr>{cells}</tr>"
    return f"<table>{colgroup}<thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>"


# cost: time O(images + rows), heap O(size of output)
def _option(opt, base):
    body = "".join(_picture(i, base) for i in opt.get("images", []))
    if "text" in opt:
        body += f'<pre class="msg">{html.escape(opt["text"])}</pre>'
    if "table" in opt:
        body += _table(opt["table"])
    cls = "col mock" if opt.get("mock") else "col"
    return f'<div class="{cls}"><h4>{_inline(opt["label"])}</h4>{body}</div>'


# cost: time O(options * images), heap O(size of output)
# vars: options = len(opts)
# basis: estimate
def _options(opts, base):
    inner = "".join(_option(o, base) for o in opts)
    return f'<div class="cols c{min(max(len(opts), 1), MAX_COLUMNS)}">{inner}</div>'


KINDS = {
    "decision": {"what": "무슨 질문인가", "bad": "나쁜 점", "rec": "추천"},
    "result": {"what": "무엇이 바뀌었나", "bad": "남은 문제", "rec": "판단"},
}


# cost: time O(options + images), heap O(size of output)
def _question(n, q, base, kind):
    words = KINDS[kind]
    effect = "".join(
        f"<tr><th>{_inline(k)}</th><td>{_inline(good)}</td><td>{_inline(bad)}</td></tr>"
        for k, good, bad in q["effect"])
    extra = "".join(
        f'<h3>{_inline(e["title"])}</h3>{_options(e["options"], base)}' for e in q.get("extra", []))
    note = f'<p class="note">{_inline(q["note"])}</p>' if q.get("note") else ""
    items = "".join(f"<li>{_inline(c)}</li>" for c in q.get("check", []))
    check = f'<div class="check"><b>확인할 점</b><ul>{items}</ul></div>' if items else ""
    rec_key, rec_why = q["rec"]
    return (f'<section id="q{n}"><h2>{n}. {_inline(q["title"])}</h2>'
            f'<p class="what"><b>{words["what"]}</b> {_inline(q["what"])}</p>'
            f'{_options(q["options"], base)}{extra}{note}'
            '<table class="effect"><colgroup><col><col style="width:50%"><col style="width:50%"></colgroup>'
            f'<thead><tr><th></th><th>좋은 점</th><th>{words["bad"]}</th></tr></thead><tbody>{effect}</tbody></table>'
            f'{check}<p class="rec"><b>{words["rec"]} {_inline(rec_key)}</b> {_inline(rec_why)}</p></section>')


# cost: time O(questions * options), heap O(size of output)
def build(spec, base):
    _validate(spec)
    kind = spec.get("kind", "decision")
    questions = spec["questions"]
    sections = "".join(_question(i, q, base, kind) for i, q in enumerate(questions, 1))
    nav = "".join(
        f'<a href="#q{i}" title="{html.escape(q["title"])}"><span>{i}</span>'
        f'<span class="nav-title">{_inline(_nav_title(q["title"]))}</span></a>'
        for i, q in enumerate(questions, 1))
    title = html.escape(spec["title"])
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{title}</title>'
            f"<style>{CSS}</style></head><body><h1>{title} ({len(questions)}개)</h1>"
            f'<p>{_inline(spec["intro"])}</p><nav aria-label="보고서 섹션">{nav}</nav>{sections}'
            '<script>const nav=document.querySelector("nav"),links=[...nav.querySelectorAll("a")],sections=[...document.querySelectorAll("section")];'
            'const setActive=()=>{const current=sections.find(section=>section.getBoundingClientRect().bottom>nav.getBoundingClientRect().bottom);if(!current)return;'
            'links.forEach(link=>{const active=link.hash==="#"+current.id;link.classList.toggle("is-active",active);link.setAttribute("aria-current",active?"true":"false")})};'
            'const observer=new IntersectionObserver(setActive);sections.forEach(section=>observer.observe(section));setActive();</script></body></html>')


# cost: time O(size of input), heap O(size of input), io 3
# vars: size of input = JSON bytes plus image count
# basis: estimate
def main():
    if len(sys.argv) not in (2, 3):
        sys.exit("usage: build_report.py <input.json> [output.html]")
    src = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]).resolve() if len(sys.argv) == 3 else src.parent / "index.html"
    try:
        if out.parent != src.parent:
            raise ReportError("output must be in the same folder as the input")
        spec = json.loads(src.read_text(encoding="utf-8"))
        out.write_text(build(spec, src.parent), encoding="utf-8")
    except (OSError, ValueError, ReportError) as err:
        sys.exit(f"build_report.py: {err}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
