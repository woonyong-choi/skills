"""질문 목록 JSON에서 그림 보고서(결정, 결과) index.html 한 장을 만든다.

사용: python3 build_report.py <입력.json> [출력.html] [--daphnis 경로] [--static]
출력 기본값은 입력 파일 옆의 index.html. 그림 경로는 입력 파일 폴더 기준.

인자: 입력 JSON, 입력과 같은 폴더의 선택 출력 HTML, --daphnis 경로(--mutoscope 호환 별칭), --static
출력: 입력 옆 index.html 또는 지정 HTML, stdout 출력 경로, stderr 실패·폐기 안내, 종료 0 성공·1 실패·2 인자 오류
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CSS = """
:root{color-scheme:light dark;--report-ink:var(--color-fg,CanvasText);--report-sub:var(--color-muted,GrayText);--report-line:var(--color-border,GrayText);--report-pane:var(--color-bg,Canvas);--report-page:var(--color-page,Canvas);--report-active:var(--color-state-active,Highlight);--report-active-fill:var(--color-card-on,Highlight);--report-active-ink:var(--color-state-active-text,LinkText);--report-chip-ink:var(--color-fg,CanvasText);--report-chip-fill:var(--color-bg,Canvas);--report-chip-border:var(--color-border,GrayText);--report-chip-hover-fill:var(--color-surface,ButtonFace);--report-chip-active-ink:var(--color-state-on-active,HighlightText);--report-chip-active-fill:var(--color-state-active-fill,Highlight);--report-chip-active-border:var(--color-state-active,Highlight);--report-chip-focus:var(--color-ui-focus,Highlight);--report-radius:var(--radius-md,6px);--nav-offset:calc(4 * 24px)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{font-family:var(--font-sans,system-ui,sans-serif);font-size:15px;line-height:1.6;max-width:1340px;margin:0 auto;padding:24px;color:var(--report-ink);background:var(--report-page)}
h1{font-size:26px;margin:0 0 8px}h2{margin:0 0 8px;font-size:21px;border-bottom:2px solid var(--report-active);padding-bottom:6px}h3{font-size:16px;margin:18px 0 6px}h4{margin:0 0 6px;font-size:15px;line-height:1.4}section{scroll-margin-top:var(--nav-offset);margin:36px 0}
.theme{display:flex;align-items:center;gap:6px;margin:0 0 12px}.theme strong{font-size:13px}.theme button{font:inherit;color:var(--report-ink);background:var(--report-pane);border:var(--border-thin,1px) solid var(--report-line);border-radius:var(--radius-full,999px);padding:3px 9px;cursor:pointer}.theme button[aria-pressed="true"]{color:var(--report-active-ink);background:var(--report-active-fill);border-color:var(--report-active)}.theme button:focus-visible,nav a:focus-visible{outline:var(--border-strong,2px) solid var(--report-active);outline-offset:2px}
.cols{display:grid;gap:16px;align-items:start;margin:10px 0}.c1{grid-template-columns:1fr}.c2{grid-template-columns:repeat(2,minmax(0,1fr))}.c3{grid-template-columns:repeat(3,minmax(0,1fr))}.c4{grid-template-columns:repeat(4,minmax(0,1fr))}.col{padding:0;min-width:0}.col.mock{border:4px dashed var(--color-data-compare,GrayText);padding:9px}
.frame{display:flex;align-items:center;justify-content:center;background:var(--report-pane);padding:4px}.frame img{display:block;width:100%;height:auto;max-height:var(--max-h,360px);object-fit:contain}.frame.dap-frame{padding:0;align-items:stretch;overflow:hidden}.frame.dap-frame iframe{display:block;width:100%;min-height:320px;height:var(--max-h,560px);border:0;background:transparent}
figure{margin:0 0 10px}figure:last-child{margin-bottom:0}figcaption{font-size:12px;color:var(--report-sub);margin-top:4px}pre.msg{white-space:pre-wrap;word-break:break-all;background:var(--report-pane);padding:8px;border-radius:var(--report-radius);font-size:12px;margin:8px 0 0}figure+pre.msg{margin-top:0}
table{border-collapse:collapse;width:100%;table-layout:fixed}th,td{border:var(--border-thin,1px) solid var(--report-line);padding:6px 10px;vertical-align:middle;font-size:14px;text-align:left;overflow-wrap:anywhere}thead th{background:var(--report-pane)}.al-center{text-align:center}.al-right{text-align:right;font-variant-numeric:tabular-nums}.effect{margin-top:12px}.effect th:first-child,.effect td:first-child{width:64px;text-align:center}.effect td{vertical-align:top}.rec{background:var(--report-active-fill);border-left:4px solid var(--report-active);padding:8px 12px;margin:12px 0 0}.check{margin:12px 0 0}.check ul{margin:4px 0 0;padding-left:20px}.note{font-size:13px;color:var(--report-sub);margin:8px 0}.what{margin:6px 0}code{font-family:var(--font-mono,ui-monospace,monospace);font-size:12px;white-space:normal}
nav{position:sticky;top:0;z-index:1;display:flex;flex-wrap:nowrap;gap:6px;margin:8px 0;padding:8px 0;overflow-x:auto;overflow-y:hidden;background:var(--report-page);border-bottom:var(--border-thin,1px) solid var(--report-line)}nav a{display:inline-flex;flex:0 0 auto;align-items:center;gap:6px;min-height:24px;max-width:calc(16 * 21px);padding:4px 8px;color:var(--report-chip-ink);text-decoration:none;white-space:nowrap;background:var(--report-chip-fill);border:var(--border-thin,1px) solid var(--report-chip-border);border-radius:var(--report-radius)}nav a:hover{background:var(--report-chip-hover-fill)}nav a.is-active{color:var(--report-chip-active-ink);background:var(--report-chip-active-fill);border-color:var(--report-chip-active-border)}nav a:focus-visible{outline:var(--border-strong,2px) solid var(--report-chip-focus);outline-offset:2px}.nav-title{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
@media print{nav,.theme{display:none}}
"""

THEME_SCRIPT = """
const THEME_KEY = 'daphnis-theme';
function applyTheme(mode) {
  const root = document.documentElement;
  if (mode === 'light' || mode === 'dark') {
    root.setAttribute('data-theme', mode);
    root.style.colorScheme = mode;
  } else {
    root.removeAttribute('data-theme');
    root.style.colorScheme = 'light dark';
  }
  for (const frame of document.querySelectorAll('iframe[data-daphnis]')) frame.contentWindow?.postMessage({ theme: mode }, '*');
  for (const button of document.querySelectorAll('.theme button')) button.setAttribute('aria-pressed', String(button.dataset.mode === mode));
}
function savedTheme() {
  try { return localStorage.getItem(THEME_KEY) || 'system'; } catch { return 'system'; }
}
applyTheme(savedTheme());
addEventListener('DOMContentLoaded', () => {
  applyTheme(savedTheme());
  document.querySelector('.theme').addEventListener('click', (event) => {
    const mode = event.target.dataset?.mode;
    if (!mode) return;
    try { localStorage.setItem(THEME_KEY, mode); } catch {}
    applyTheme(mode);
  });
});
addEventListener('message', (event) => {
  if (!event.data) return;
  const frame = [...document.querySelectorAll('iframe[data-daphnis]')].find((item) => item.contentWindow === event.source);
  if (event.data.themeRequest && frame) event.source.postMessage({ theme: savedTheme() }, '*');
  if (event.data.figureHeight && frame) frame.style.height = `${Math.ceil(event.data.figureHeight)}px`;
});
"""

SVG_THEME_BRIDGE = """
<script>
addEventListener('message', (event) => {
  if (event.source !== parent || !event.data || !('theme' in event.data)) return;
  const root = document.documentElement;
  if (event.data.theme === 'light' || event.data.theme === 'dark') {
    root.setAttribute('data-theme', event.data.theme);
    root.style.colorScheme = event.data.theme;
  } else {
    root.removeAttribute('data-theme');
    root.style.colorScheme = '';
  }
});
parent.postMessage({ themeRequest: true }, '*');
</script>
"""

NAVIGATION_SCRIPT = """
const nav=document.querySelector("nav"),links=[...nav.querySelectorAll("a")],sections=[...document.querySelectorAll("section")];
const setActive=()=>{const current=sections.find(section=>section.getBoundingClientRect().bottom>nav.getBoundingClientRect().bottom);if(!current)return;const activeLink=links.find(link=>link.hash==="#"+current.id);if(!activeLink)return;links.forEach(link=>{const active=link===activeLink;link.classList.toggle("is-active",active);link.setAttribute("aria-current",active?"true":"false")});activeLink.scrollIntoView({block:"nearest",inline:"nearest"})};
const observer=new IntersectionObserver(setActive);sections.forEach(section=>observer.observe(section));addEventListener("scroll",setActive,{passive:true});setActive();
"""


class ReportError(Exception):
    """입력이 틀렸을 때 던진다. main이 `build_report.py: 메시지`로 바꿔 종료한다."""


@dataclass(frozen=True)
class Daphnis:
    """렌더 CLI와 토큰 CSS의 확인된 위치."""

    cli: Path
    tokens_css: Path


@dataclass
class FigureRenderer:
    """Daphnis 입력을 페이지 안 독립 문서로 바꾼다."""

    base: Path
    daphnis: Daphnis | None
    static: bool
    rendered: dict[Path, str] = field(default_factory=dict)

    # cost: time O(render), heap O(output), stack O(1), io 3
    # vars: render = daphnis 원본 하나의 렌더 비용, output = HTML 결과 크기
    # basis: estimate
    def render_dap(self, source: Path) -> str:
        if self.daphnis is None:
            raise ReportError("dap figure needs --daphnis or DAPHNIS_PATH")
        if source in self.rendered:
            return self.rendered[source]
        digest = hashlib.sha256(str(source).encode()).hexdigest()[:16]
        output_dir = self.base / ".dap-rendered" / digest
        command = [
            "node",
            str(self.daphnis.cli),
            "render",
            str(source),
            "--out",
            str(output_dir),
            "--strict",
        ]
        if self.static:
            command.append("--static")
        else:
            command.append("--html")
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode:
            detail = (result.stderr or result.stdout).strip()
            raise ReportError(f"daphnis render failed: {source}: {detail}")
        output = output_dir / f"{source.stem}.{'svg' if self.static else 'html'}"
        if not output.is_file():
            raise ReportError(f"daphnis did not create inline figure: {output}")
        document = output.read_text(encoding="utf-8")
        if self.static:
            document = _svg_document(document)
        self.rendered[source] = document
        return document


ALIGNS = ("left", "center", "right")
MAX_COLUMNS = 4
NAV_TITLE_MAX_LENGTH = 24


# cost: time O(1), heap O(1), stack O(1)
# basis: estimate
def _need(obj: Any, key: str, where: str, kind: type[Any] | None = None) -> Any:
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
def _check_table(spec: dict[str, Any], where: str) -> None:
    _need(spec, "head", where, list)
    for row_number, row in enumerate(_need(spec, "rows", where, list)):
        if not isinstance(row, list):
            raise ReportError(f"{where}.rows[{row_number}] must be list")
    for align in spec.get("align", []):
        if align not in ALIGNS:
            raise ReportError(f"{where}.align must be one of {list(ALIGNS)}: {align}")


# cost: time O(options), heap O(1), stack O(1)
# vars: options = options in one row of columns
# basis: estimate
def _check_options(options: list[dict[str, Any]], where: str) -> None:
    if len(options) > MAX_COLUMNS:
        raise ReportError(
            f"{where} has {len(options)} options, at most {MAX_COLUMNS} allowed"
        )
    for option_number, option in enumerate(options):
        at = f"{where}[{option_number}]"
        _need(option, "label", at, str)
        for figure_number, figure in enumerate(option.get("images", [])):
            figure_at = f"{at}.images[{figure_number}]"
            sources = [key for key in ("src", "dap", "inline") if key in figure]
            if len(sources) != 1:
                raise ReportError(f"{figure_at} needs exactly one of src, dap, inline")
            _need(figure, sources[0], figure_at, str)
            if sources[0] == "dap" and not figure["dap"].endswith(".dap"):
                raise ReportError(f"{figure_at}.dap must end with .dap")
            if sources[0] == "inline" and Path(figure["inline"]).suffix not in (
                ".svg",
                ".html",
            ):
                raise ReportError(f"{figure_at}.inline must be a .svg or .html file")
        if "table" in option:
            _check_table(option["table"], f"{at}.table")


# cost: time O(options + effect rows), heap O(1), stack O(1)
# basis: estimate
def _check_question(question: dict[str, Any], where: str) -> None:
    _need(question, "title", where, str)
    _need(question, "what", where, str)
    _check_options(_need(question, "options", where, list), f"{where}.options")
    for row_number, row in enumerate(_need(question, "effect", where, list)):
        if not isinstance(row, list) or len(row) != 3:
            raise ReportError(f"{where}.effect[{row_number}] must have 3 cells")
    if len(_need(question, "rec", where, list)) != 2:
        raise ReportError(f"{where}.rec must have 2 items")
    for extra_number, extra in enumerate(question.get("extra", [])):
        _need(extra, "title", f"{where}.extra[{extra_number}]", str)
        _check_options(
            _need(extra, "options", f"{where}.extra[{extra_number}]", list),
            f"{where}.extra[{extra_number}].options",
        )


# cost: time O(questions * options), heap O(1), stack O(1)
# basis: estimate
def _validate(spec: dict[str, Any]) -> None:
    kind = spec.get("kind", "decision") if isinstance(spec, dict) else None
    if kind not in KINDS:
        raise ReportError(f"kind must be one of {sorted(KINDS)}: {kind}")
    _need(spec, "title", "input", str)
    _need(spec, "intro", "input", str)
    for number, question in enumerate(_need(spec, "questions", "input", list), 1):
        _check_question(question, f"questions[{number}]")


# cost: time O(n), heap O(n), stack O(1)
# vars: n = len(text)
# basis: estimate
def _inline(text: str) -> str:
    """이스케이프 뒤 `코드`만 code 태그로 바꾼다."""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(text))


# cost: time O(n), heap O(n), stack O(1)
# vars: n = len(title)
# basis: estimate
def _nav_title(title: str) -> str:
    if len(title) <= NAV_TITLE_MAX_LENGTH:
        return title
    return title[: NAV_TITLE_MAX_LENGTH - 1] + "…"


# cost: time O(1), heap O(1), stack O(1), io 1
# basis: estimate
def _existing_file(base: Path, relative: str, label: str) -> Path:
    path = base / relative
    if not path.is_file():
        raise ReportError(f"{label} not found: {path}")
    return path


# cost: time O(n), heap O(n), stack O(1)
# vars: n = SVG bytes
# basis: estimate
def _svg_document(svg: str) -> str:
    return f'<!doctype html><html><head><meta charset="utf-8">{SVG_THEME_BRIDGE}</head><body>{svg}</body></html>'


# cost: time O(n), heap O(n), stack O(1)
# vars: n = rendered document bytes
# basis: estimate
def _inline_frame(document: str, alt: str, style: str) -> str:
    title = html.escape(alt, quote=True) or "daphnis figure"
    source = html.escape(document, quote=True)
    caption = f"<figcaption>{html.escape(alt)}</figcaption>" if alt else ""
    return (
        f'<figure><div class="frame dap-frame"{style}>'
        f'<iframe data-daphnis sandbox="allow-scripts" title="{title}" srcdoc="{source}"></iframe></div>{caption}</figure>'
    )


# cost: time O(render or input bytes), heap O(output), stack O(1), io 1 or 3
# basis: estimate
def _picture(image: dict[str, Any], renderer: FigureRenderer) -> str:
    try:
        style = (
            f' style="--max-h:{int(image["max_height"])}px"'
            if "max_height" in image
            else ""
        )
    except (TypeError, ValueError):
        raise ReportError(
            f"max_height must be a number: {image['max_height']}"
        ) from None
    alt = image.get("alt", "")
    if "src" in image:
        _existing_file(renderer.base, image["src"], "image")
        escaped_alt = html.escape(alt)
        caption = f"<figcaption>{escaped_alt}</figcaption>" if alt else ""
        return (
            f'<figure><div class="frame"{style}><img src="{html.escape(image["src"])}" alt="{escaped_alt}"></div>'
            f"{caption}</figure>"
        )
    if "dap" in image:
        source = _existing_file(renderer.base, image["dap"], "dap figure")
        return _inline_frame(renderer.render_dap(source), alt, style)
    source = _existing_file(renderer.base, image["inline"], "inline figure")
    if source.suffix == ".svg":
        return _inline_frame(
            _svg_document(source.read_text(encoding="utf-8")), alt, style
        )
    return _inline_frame(source.read_text(encoding="utf-8"), alt, style)


# cost: time O(rows * cols), heap O(rows * cols), stack O(1)
# basis: estimate
def _table(spec: dict[str, Any]) -> str:
    aligns = spec.get("align", [])
    widths = spec.get("widths", [])

    def class_name(index: int, extra: str = "") -> str:
        names = (
            [f"al-{aligns[index]}"]
            if index < len(aligns) and aligns[index] != "left"
            else []
        )
        names += [extra] if extra else []
        return f' class="{" ".join(names)}"' if names else ""

    columns = "".join(f'<col style="width:{html.escape(width)}">' for width in widths)
    column_group = f"<colgroup>{columns}</colgroup>" if widths else ""
    head = "".join(
        f"<th{class_name(index)}>{_inline(cell)}</th>"
        for index, cell in enumerate(spec["head"])
    )
    rows = "".join(
        f"<tr>{''.join(f'<td{class_name(index)}>{_inline(cell)}</td>' for index, cell in enumerate(row))}</tr>"
        for row in spec["rows"]
    )
    return f"<table>{column_group}<thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>"


# cost: time O(figures + rows), heap O(output), stack O(1)
# basis: estimate
def _option(option: dict[str, Any], renderer: FigureRenderer) -> str:
    body = "".join(_picture(image, renderer) for image in option.get("images", []))
    if "text" in option:
        body += f'<pre class="msg">{html.escape(option["text"])}</pre>'
    if "table" in option:
        body += _table(option["table"])
    class_name = "col mock" if option.get("mock") else "col"
    return f'<div class="{class_name}"><h4>{_inline(option["label"])}</h4>{body}</div>'


# cost: time O(options * figures), heap O(output), stack O(1)
# basis: estimate
def _options(options: list[dict[str, Any]], renderer: FigureRenderer) -> str:
    inner = "".join(_option(option, renderer) for option in options)
    return f'<div class="cols c{min(max(len(options), 1), MAX_COLUMNS)}">{inner}</div>'


KINDS = {
    "decision": {"what": "무슨 질문인가", "bad": "나쁜 점", "rec": "추천"},
    "result": {"what": "무엇이 바뀌었나", "bad": "남은 문제", "rec": "판단"},
}


# cost: time O(options + figures + effect rows), heap O(output), stack O(1)
# basis: estimate
def _question(
    number: int, question: dict[str, Any], renderer: FigureRenderer, kind: str
) -> str:
    words = KINDS[kind]
    effect = "".join(
        f"<tr><th>{_inline(key)}</th><td>{_inline(good)}</td><td>{_inline(bad)}</td></tr>"
        for key, good, bad in question["effect"]
    )
    extra = "".join(
        f"<h3>{_inline(item['title'])}</h3>{_options(item['options'], renderer)}"
        for item in question.get("extra", [])
    )
    note = (
        f'<p class="note">{_inline(question["note"])}</p>'
        if question.get("note")
        else ""
    )
    items = "".join(f"<li>{_inline(check)}</li>" for check in question.get("check", []))
    checks = (
        f'<div class="check"><b>확인할 점</b><ul>{items}</ul></div>' if items else ""
    )
    recommendation, reason = question["rec"]
    return (
        f'<section id="q{number}"><h2>{number}. {_inline(question["title"])}</h2>'
        f'<p class="what"><b>{words["what"]}</b> {_inline(question["what"])}</p>'
        f"{_options(question['options'], renderer)}{extra}{note}"
        '<table class="effect"><colgroup><col><col style="width:50%"><col style="width:50%"></colgroup>'
        f"<thead><tr><th></th><th>좋은 점</th><th>{words['bad']}</th></tr></thead><tbody>{effect}</tbody></table>"
        f'{checks}<p class="rec"><b>{words["rec"]} {_inline(recommendation)}</b> {_inline(reason)}</p></section>'
    )


# cost: time O(questions * options * figures), heap O(output), stack O(1)
# basis: estimate
def build(spec: dict[str, Any], renderer: FigureRenderer, tokens_css: str) -> str:
    _validate(spec)
    kind = spec.get("kind", "decision")
    questions = spec["questions"]
    sections = "".join(
        _question(number, question, renderer, kind)
        for number, question in enumerate(questions, 1)
    )
    navigation = "".join(
        f'<a href="#q{number}" title="{html.escape(question["title"])}"><span>{number}</span>'
        f'<span class="nav-title">{_inline(_nav_title(question["title"]))}</span></a>'
        for number, question in enumerate(questions, 1)
    )
    theme = (
        '<div class="theme" role="group" aria-label="보고서 테마"><strong>테마</strong>'
        '<button type="button" data-mode="system" aria-pressed="true">시스템</button>'
        '<button type="button" data-mode="light" aria-pressed="false">라이트</button>'
        '<button type="button" data-mode="dark" aria-pressed="false">다크</button></div>'
    )
    title = html.escape(spec["title"])
    return (
        f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{title}</title><style>{tokens_css}{CSS}</style><script>{THEME_SCRIPT}</script></head><body>"
        f"<h1>{title} ({len(questions)}개)</h1>{theme}<p>{_inline(spec['intro'])}</p>"
        f'<nav aria-label="보고서 섹션">{navigation}</nav>{sections}'
        f"<script>{NAVIGATION_SCRIPT}</script></body></html>"
    )


# cost: time O(p), heap O(p), stack O(1), io O(p)
# vars: p = PATH의 탐색 항목 수와 경로 길이
# basis: estimate
def _daphnis(value: str | None) -> Daphnis | None:
    if "MUTOSCOPE_PATH" in os.environ:
        print(
            "deprecated: MUTOSCOPE_PATH will be removed after this release; use DAPHNIS_PATH",
            file=sys.stderr,
        )
    configured = (
        value
        or os.environ.get("DAPHNIS_PATH")
        or os.environ.get("MUTOSCOPE_PATH")
        or shutil.which("daphnis")
    )
    if not configured:
        return None
    path = Path(configured).expanduser().resolve()
    cli = path / "src" / "cli.js" if path.is_dir() else path
    tokens_css = cli.parent / "tokens.css"
    if not cli.is_file() or not tokens_css.is_file():
        raise ReportError(f"invalid daphnis path: {path}")
    return Daphnis(cli=cli, tokens_css=tokens_css)


# cost: time O(1), heap O(1), stack O(1)
# basis: estimate
def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "output", type=Path, nargs="?", help="output HTML in the same folder as input"
    )
    parser.add_argument("--daphnis", help="daphnis checkout or src/cli.js path")
    parser.add_argument("--mutoscope", help="deprecated alias for --daphnis")
    parser.add_argument(
        "--static",
        action="store_true",
        help="embed a static SVG in the report iframe",
    )
    arguments = parser.parse_args()
    if arguments.mutoscope is not None:
        print(
            "deprecated: --mutoscope will be removed after this release; use --daphnis",
            file=sys.stderr,
        )
    arguments.daphnis = arguments.daphnis or arguments.mutoscope
    return arguments


# cost: time O(size of input + render), heap O(size of output), stack O(1), io 3+
# vars: render = dap input count times daphnis render cost
# basis: estimate
def main() -> None:
    arguments = _arguments()
    source = arguments.input.resolve()
    output = (
        arguments.output.resolve() if arguments.output else source.parent / "index.html"
    )
    try:
        if output.parent != source.parent:
            raise ReportError("output must be in the same folder as the input")
        spec = json.loads(source.read_text(encoding="utf-8"))
        daphnis = _daphnis(arguments.daphnis)
        renderer = FigureRenderer(
            base=source.parent, daphnis=daphnis, static=arguments.static
        )
        tokens_css = daphnis.tokens_css.read_text(encoding="utf-8") if daphnis else ""
        output.write_text(build(spec, renderer, tokens_css), encoding="utf-8")
    except (OSError, ValueError, ReportError) as error:
        sys.exit(f"build_report.py: {error}")
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
