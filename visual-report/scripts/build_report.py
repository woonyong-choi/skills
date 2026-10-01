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
:root{--ink:#1c2025;--sub:#667;--line:#c9ced6;--line-strong:#9aa3af;--pane:#f3f4f6;--blue:#2b78d9;--orange:#eb6834}
*{box-sizing:border-box}
body{font:15px/1.6 -apple-system,'Pretendard',sans-serif;max-width:1340px;margin:0 auto;padding:24px;color:var(--ink);background:#fafbfc}
h1{font-size:26px;margin:0 0 8px}
h2{margin:0 0 8px;font-size:21px;border-bottom:2px solid var(--blue);padding-bottom:6px}
h3{font-size:16px;margin:18px 0 6px}
h4{margin:0 0 6px;font-size:15px;line-height:1.4}
section{background:#fff;border:1px solid var(--line);border-radius:10px;padding:20px 24px;margin:28px 0}
.cols{display:grid;gap:16px;align-items:start;margin:10px 0}
.c1{grid-template-columns:1fr}.c2{grid-template-columns:repeat(2,minmax(0,1fr))}
.c3{grid-template-columns:repeat(3,minmax(0,1fr))}.c4{grid-template-columns:repeat(4,minmax(0,1fr))}
.col{border:1px solid var(--line);border-radius:8px;padding:12px;min-width:0}
.col.mock{border:4px dashed var(--orange);padding:9px}
.frame{display:flex;align-items:center;justify-content:center;background:var(--pane);border:1px solid var(--line);padding:4px}
.frame img{display:block;width:100%;height:auto;max-height:var(--max-h,360px);object-fit:contain}
figure{margin:0 0 10px}figure:last-child{margin-bottom:0}
figcaption{font-size:12px;color:var(--sub);margin-top:4px}
pre.msg{white-space:pre-wrap;word-break:break-all;background:#f3f4f6;padding:8px;border-radius:6px;font-size:12px;margin:8px 0 0}
figure+pre.msg{margin-top:0}
table{border-collapse:collapse;width:100%;table-layout:fixed}
th,td{border:1px solid var(--line);padding:6px 10px;vertical-align:middle;font-size:14px;text-align:left;overflow-wrap:anywhere}
thead th{background:#f5f7fa;border-bottom:2px solid var(--line-strong)}
.al-center{text-align:center}.al-right{text-align:right;font-variant-numeric:tabular-nums}
.effect{margin-top:12px}.effect th:first-child,.effect td:first-child{width:64px;text-align:center}
.effect td{vertical-align:top}
.rec{background:#eef5ff;border-left:4px solid var(--blue);padding:8px 12px;margin:12px 0 0}
.check{margin:12px 0 0}.check ul{margin:4px 0 0;padding-left:20px}
.note{font-size:13px;color:var(--sub);margin:8px 0 0}
.what{margin:6px 0}
code{font-size:12px;white-space:normal}
.bad{color:#b3261e}.ok{color:#1b7a3a}
nav{margin:8px 0}nav a{display:inline-block;min-width:22px;margin-right:6px;text-align:center}
"""


def _inline(text):
    """이스케이프 뒤 `코드`만 code 태그로 바꾼다."""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(text))


def _picture(img, base):
    src = img["src"]
    if not (base / src).is_file():
        raise FileNotFoundError(f"image not found: {base / src}")
    alt = html.escape(img.get("alt", ""))
    style = f' style="--max-h:{int(img["max_height"])}px"' if "max_height" in img else ""
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


def _options(opts, base):
    inner = "".join(_option(o, base) for o in opts)
    return f'<div class="cols c{min(max(len(opts), 1), 4)}">{inner}</div>'


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
    kind = spec.get("kind", "decision")
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {sorted(KINDS)}: {kind}")
    questions = spec["questions"]
    sections = "".join(_question(i, q, base, kind) for i, q in enumerate(questions, 1))
    nav = "".join(f'<a href="#q{i}">{i}</a>' for i in range(1, len(questions) + 1))
    title = html.escape(spec["title"])
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{title}</title>'
            f"<style>{CSS}</style></head><body><h1>{title} ({len(questions)}개)</h1>"
            f'<p>{_inline(spec["intro"])}</p><nav>{nav}</nav>{sections}</body></html>')


def main():
    if len(sys.argv) not in (2, 3):
        sys.exit("usage: build_report.py <input.json> [output.html]")
    src = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]).resolve() if len(sys.argv) == 3 else src.parent / "index.html"
    if out.parent != src.parent:
        sys.exit("output must be in the same folder as the input (image paths are relative)")
    out.write_text(build(json.loads(src.read_text(encoding="utf-8")), src.parent), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
