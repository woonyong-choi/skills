"""입력 JSON에서 설명(explain)·비교(decision, result) HTML 한 장을 만든다.

사용: python3 build_report.py <입력.json> [출력.html] [--thinkflow 경로] [--static]
출력 기본값은 입력 파일 옆의 index.html. 그림 경로는 입력 파일 폴더 기준.

인자: 입력 JSON, 입력과 같은 폴더의 선택 출력 HTML, --thinkflow 경로, --static
출력: 입력 옆 index.html 또는 지정 HTML(explain은 같은 폴더 theme/·figures/ 포함), stdout 출력 경로, stderr 실패, 종료 0 성공·1 실패·2 인자 오류
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
:root{--report-ink:var(--color-ink);--report-sub:var(--color-ui-muted);--report-line:var(--color-ui-line);--report-pane:var(--color-figure-canvas);--report-page:var(--color-ui-card);--report-active:var(--color-state-active);--report-active-fill:var(--color-help-bg);--report-active-ink:var(--color-state-active-text);--report-chip-ink:var(--color-ink);--report-chip-fill:var(--color-ui-card);--report-chip-border:var(--color-ui-line);--report-chip-hover-fill:var(--color-help-hover);--report-chip-active-ink:var(--color-state-on-active);--report-chip-active-fill:var(--color-state-active-fill);--report-chip-active-border:var(--color-state-active);--report-chip-focus:var(--color-ui-focus);--report-radius:var(--radius-md);--report-small:var(--text-small-text);--nav-offset:calc(4 * var(--spacing-gap))}
section{scroll-margin-top:var(--nav-offset);margin-block:var(--spacing-gap-lg)}h2{border-bottom:var(--border-width-strong) solid var(--report-active);padding-bottom:var(--spacing-gap-xs)}
.cols{display:grid;gap:var(--spacing-gap);align-items:start;margin-block:var(--spacing-gap-sm)}.c1{grid-template-columns:1fr}.c2{grid-template-columns:repeat(2,minmax(0,1fr))}.c3{grid-template-columns:repeat(3,minmax(0,1fr))}.c4{grid-template-columns:repeat(4,minmax(0,1fr))}.col{padding:0;min-width:0}.col.mock{border:var(--border-width-strong) dashed var(--color-data-compare);padding:var(--spacing-gap-sm)}
.frame{display:flex;align-items:center;justify-content:center;background:var(--report-pane);border-radius:var(--radius-lg);padding:var(--spacing-gap-xs)}.frame img{display:block;width:100%;height:auto;max-height:var(--max-h,360px);object-fit:contain}.frame.diagram-frame{padding:0;align-items:stretch;overflow:hidden}.frame.diagram-frame iframe{display:block;width:100%;height:var(--max-h,240px);border:0;background:transparent}
figure{margin:0 0 var(--spacing-gap-sm)}figure:last-child{margin-bottom:0}figcaption{font-size:var(--report-small);color:var(--report-sub);margin-top:var(--spacing-gap-xs)}pre.msg{white-space:pre-wrap;word-break:break-all;background:var(--report-pane);padding:var(--spacing-gap-sm);border-radius:var(--report-radius);font-size:var(--report-small);margin:var(--spacing-gap-sm) 0 0}figure+pre.msg{margin-top:0}
table{border-collapse:collapse;width:100%;table-layout:fixed}th,td{border:var(--border-width-thin) solid var(--report-line);padding:var(--spacing-gap-xs) var(--spacing-gap-sm);vertical-align:middle;text-align:left;overflow-wrap:anywhere}thead th{background:var(--report-pane)}.al-center{text-align:center}.al-right{text-align:right;font-variant-numeric:tabular-nums}.effect{margin-top:var(--spacing-gap-sm)}.effect th:first-child,.effect td:first-child{width:64px;text-align:center}.effect td{vertical-align:top}.rec{background:var(--report-active-fill);border-left:var(--border-width-strong) solid var(--report-active);padding:var(--spacing-gap-sm) var(--spacing-gap);margin:var(--spacing-gap-sm) 0 0}.check{margin:var(--spacing-gap-sm) 0 0}.check ul{margin:var(--spacing-gap-xs) 0 0}.note{font-size:var(--report-small);color:var(--report-sub)}code{font-family:var(--font-mono);white-space:normal}
nav{position:sticky;top:0;z-index:1;display:flex;flex-wrap:nowrap;gap:var(--spacing-gap-xs);margin-block:var(--spacing-gap-sm);padding-block:var(--spacing-gap-sm);overflow-x:auto;overflow-y:hidden;background:var(--report-page);border-bottom:var(--border-width-thin) solid var(--report-line)}nav a{display:inline-flex;flex:0 0 auto;align-items:center;gap:var(--spacing-gap-xs);min-height:24px;max-width:calc(16 * 21px);padding:var(--spacing-gap-xs) var(--spacing-gap-sm);color:var(--report-chip-ink);text-decoration:none;white-space:nowrap;font-size:var(--report-small);background:var(--report-chip-fill);border:var(--border-width-thin) solid var(--report-chip-border);border-radius:var(--report-radius)}nav a:hover{background:var(--report-chip-hover-fill)}nav a.is-active{color:var(--report-chip-active-ink);background:var(--report-chip-active-fill);border-color:var(--report-chip-active-border)}nav a:focus-visible{outline:var(--border-width-strong) solid var(--report-chip-focus);outline-offset:2px}.nav-title{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
@media print{nav,.theme{display:none}}
"""

THEME_SCRIPT = """
const THEME_KEY = 'thinkflow-theme';
function applyTheme(mode) {
  const root = document.documentElement;
  if (mode === 'light' || mode === 'dark') {
    root.setAttribute('data-theme', mode);
    root.style.colorScheme = mode;
  } else {
    root.removeAttribute('data-theme');
    root.style.colorScheme = 'light dark';
  }
  for (const frame of document.querySelectorAll('iframe[data-diagram]')) frame.contentWindow?.postMessage({ theme: mode }, '*');
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
  const frame = [...document.querySelectorAll('iframe[data-diagram]')].find((item) => item.contentWindow === event.source);
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

REVIEW_CSS = """
:root{--review-unit:var(--spacing-gap);--review-radius:var(--radius-lg);--review-small:var(--text-small-text);--review-border:color-mix(in srgb,var(--report-ink) 14%,var(--report-page));--review-muted:color-mix(in srgb,var(--report-ink) 65%,var(--report-page));--review-surface:color-mix(in srgb,var(--report-ink) 3%,var(--report-page))}
.review{border-block:1px solid var(--review-border);padding:var(--review-unit) 0;margin-bottom:calc(var(--review-unit)*2)}
.review-toolbar{display:flex;align-items:center;gap:var(--review-unit);flex-wrap:wrap}.review-toolbar output{color:var(--review-muted);font-size:var(--review-small);margin-right:auto}
.review button,.review select,.review-page .decision-actions label{font:inherit;font-size:var(--review-small);padding:calc(var(--review-unit)/2) var(--review-unit);border:1px solid var(--review-border);border-radius:var(--report-radius);color:var(--report-ink);background:var(--report-page);cursor:pointer}
.review .copy-button{color:var(--report-page);background:var(--report-ink);border-color:var(--report-ink)}
.review details{margin-top:var(--review-unit);font-size:var(--review-small);color:var(--review-muted)}
.review [data-review-notice]:empty{display:none}.review [data-review-notice]{font-size:var(--review-small);margin-bottom:0}
.review-page section{margin:calc(var(--review-unit)*3) 0}.review-page h2{font-size:1.125rem;border:0;padding:0;margin:0}.review-page .what{color:var(--review-muted);font-size:var(--review-small);margin:calc(var(--review-unit)/2) 0 var(--review-unit)}
.review-page .cols{gap:var(--review-unit);align-items:stretch}.review-page .col{display:flex;flex-direction:column;overflow:hidden;border:1px solid var(--review-border);border-radius:var(--review-radius);background:var(--report-page);padding:var(--review-unit)}
.review-page .col:has(input:checked){border-color:var(--report-ink);box-shadow:inset 0 0 0 1px var(--report-ink)}
.review-page .col.mock{border-style:dashed}.review-page h4{font-size:var(--review-small);margin-bottom:var(--review-unit)}
.review-page .frame{border-radius:var(--report-radius);background:var(--review-surface);padding:0;overflow:hidden}.review-page .frame img{max-height:420px}.review-page figcaption{font-size:var(--review-small);color:var(--review-muted)}
.option-feedback{margin-top:auto;padding-top:var(--review-unit)}.option-select{display:flex;align-items:center;gap:calc(var(--review-unit)/2);min-height:calc(var(--review-unit)*2);cursor:pointer;font-size:var(--review-small);font-weight:600}
.review-page input[type=radio]{accent-color:var(--report-ink);margin:0}.review-page textarea{display:block;width:100%;resize:vertical;min-height:calc(var(--review-unit)*3);margin-top:calc(var(--review-unit)/2);padding:calc(var(--review-unit)*.75);border:1px solid var(--review-border);border-radius:var(--report-radius);background:var(--review-surface);color:var(--report-ink);font:inherit;font-size:var(--review-small);line-height:1.5}
.review-page textarea::placeholder{color:var(--review-muted)}.review-page :is(button,select,textarea,input,summary):focus-visible{outline:2px solid var(--report-ink);outline-offset:3px}
.decision-actions{display:flex;align-items:center;gap:calc(var(--review-unit)/2);flex-wrap:wrap;margin-top:var(--review-unit)}.review-page .decision-actions label{display:flex;align-items:center;gap:calc(var(--review-unit)/2)}
.review-reasons{margin-top:var(--review-unit);font-size:var(--review-small);color:var(--review-muted)}.review-reasons summary{cursor:pointer}.review-reasons .rec{background:var(--review-surface);border-left-color:var(--review-border);color:var(--report-ink)}
@media(max-width:700px){.review-page .cols{grid-template-columns:1fr}.review-toolbar{gap:calc(var(--review-unit)/2)}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
"""

REVIEW_SCRIPT = """
const review = document.querySelector('[data-review]');
const sections = [...document.querySelectorAll('section[data-question]')];
const output = document.querySelector('[data-review-output]');
const notice = document.querySelector('[data-review-notice]');
const filter = document.querySelector('[data-review-filter]');
const key = 'visual-review:' + review.dataset.review;
function decisions() {
  return sections.map(section => {
    const selected = section.querySelector('[data-choice]:checked');
    return {id: section.id, title: section.querySelector('h2').textContent,
      choice: selected.value, label: selected.dataset.label,
      options: [...section.querySelectorAll('[data-option-note]')].map(input => ({
        id: input.dataset.optionNote, label: input.dataset.label, note: input.value
      }))};
  });
}
function updateReview() {
  const rows = decisions();
  output.value = JSON.stringify({title: document.title, version: review.dataset.version,
    report: review.dataset.review, decisions: rows}, null, 2);
  sections.forEach((section, index) => {
    const value = rows[index].choice;
    const state = value.startsWith('option-') ? 'selected' : value || 'pending';
    section.hidden = filter.value !== 'all' && filter.value !== state;
  });
  const visible = sections.filter(section => !section.hidden).length;
  document.querySelector('[data-review-count]').textContent =
    `${rows.filter(row => row.choice).length} / ${rows.length}개 검토`;
  document.querySelector('[data-review-empty]').hidden = visible !== 0;
  try { localStorage.setItem(key, JSON.stringify(rows)); }
  catch { notice.textContent = '저장할 수 없습니다. 닫기 전에 결과를 복사하세요.'; }
}
try {
  const saved = JSON.parse(localStorage.getItem(key) || '[]');
  if (!Array.isArray(saved)) throw new Error('invalid review');
  sections.forEach(section => {
    const row = saved.find(item => item?.id === section.id);
    if (!row) return;
    const selected = [...section.querySelectorAll('[data-choice]')].find(input => input.value === row.choice);
    if (selected) selected.checked = true;
    section.querySelectorAll('[data-option-note]').forEach(input => {
      const option = Array.isArray(row.options) && row.options.find(item => item?.id === input.dataset.optionNote);
      if (typeof option?.note === 'string') input.value = option.note;
    });
  });
} catch { notice.textContent = '이전 판정을 읽지 못했습니다. 기존 복사본을 확인하세요.'; }
document.addEventListener('input', event => {
  if (event.target.matches('[data-choice], [data-option-note]')) updateReview();
});
filter.addEventListener('change', updateReview);
document.querySelector('[data-review-copy]').addEventListener('click', async () => {
  try { await navigator.clipboard.writeText(output.value); notice.textContent = '복사했습니다. 대화에 붙여넣어 주세요.'; }
  catch {
    output.closest('details').open = true; output.focus(); output.select();
    notice.textContent = '자동 복사 불가. 선택된 결과를 직접 복사하세요.';
  }
});
updateReview();
"""


class ReportError(Exception):
    """입력이 틀렸을 때 던진다. main이 `build_report.py: 메시지`로 바꿔 종료한다."""


@dataclass(frozen=True)
class Thinkflow:
    """ThinkFlow 체크아웃의 렌더 CLI와 공통 테마 폴더."""

    cli: Path
    theme: Path


@dataclass
class FigureRenderer:
    """ThinkFlow 원본을 재생기 HTML 또는 정지 SVG로 바꾼다."""

    base: Path
    thinkflow: Thinkflow | None
    static: bool
    rendered: dict[Path, str] = field(default_factory=dict)

    # cost: time O(render), heap O(output), stack O(1), io 3
    # vars: render = 원본 하나의 렌더 비용, output = HTML 결과 크기
    # basis: estimate
    def render(self, source: Path, output_dir: Path | None = None, static: bool | None = None) -> str:
        static = self.static if static is None else static
        if self.thinkflow is None:
            raise ReportError("thinkflow figure needs --thinkflow or THINKFLOW_PATH")
        if source in self.rendered and output_dir is None:
            return self.rendered[source]
        digest = hashlib.sha256(str(source).encode()).hexdigest()[:16]
        output_dir = output_dir or self.base / ".thinkflow-rendered" / digest
        command = [
            "node",
            str(self.thinkflow.cli),
            "render",
            str(source),
            "--out",
            str(output_dir),
            "--strict",
        ]
        if static:
            command.append("--static")
        else:
            command.append("--html")
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode:
            detail = (result.stderr or result.stdout).strip()
            raise ReportError(f"thinkflow render failed: {source}: {detail}")
        output = output_dir / f"{source.stem}.{'svg' if static else 'html'}"
        if not output.is_file():
            raise ReportError(f"thinkflow did not create figure: {output}")
        document = output.read_text(encoding="utf-8")
        if static:
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
            sources = [key for key in ("src", "thinkflow", "inline") if key in figure]
            if len(sources) != 1:
                raise ReportError(f"{figure_at} needs exactly one of src, thinkflow, inline")
            _need(figure, sources[0], figure_at, str)
            if sources[0] == "thinkflow":
                _thinkflow_source(figure["thinkflow"], f"{figure_at}.thinkflow")
            if sources[0] == "inline" and Path(figure["inline"]).suffix not in (
                ".svg",
                ".html",
            ):
                raise ReportError(f"{figure_at}.inline must be a .svg or .html file")
        if "table" in option:
            _check_table(option["table"], f"{at}.table")


# cost: time O(options + rows), heap O(1), stack O(1)
# vars: options = 선택지 수, rows = 효과 표 행 수
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
# vars: questions = 질문 수, options = 질문당 최대 선택지·효과 행 수
# basis: estimate
def _validate(spec: dict[str, Any]) -> None:
    kind = spec.get("kind", "decision") if isinstance(spec, dict) else None
    if kind not in KINDS:
        raise ReportError(f"kind must be one of {sorted(KINDS)}: {kind}")
    _need(spec, "title", "input", str)
    _need(spec, "intro", "input", str)
    if "review" in spec:
        if not _need(spec, "review", "input", str).strip():
            raise ReportError("review version must not be empty")
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
    title = html.escape(alt, quote=True) or "figure"
    source = html.escape(document, quote=True)
    caption = f"<figcaption>{html.escape(alt)}</figcaption>" if alt else ""
    return (
        f'<figure><div class="frame diagram-frame"{style}>'
        f'<iframe data-diagram sandbox="allow-scripts" title="{title}" srcdoc="{source}"></iframe></div>{caption}</figure>'
    )


# cost: time O(n + r), heap O(o), stack O(1), io 3
# vars: n = 인라인 입력 바이트 수, r = 외부 렌더 시간, o = 렌더 결과 바이트 수
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
    if "thinkflow" in image:
        source = _existing_file(renderer.base, image["thinkflow"], "thinkflow figure")
        return _inline_frame(renderer.render(source), alt, style)
    source = _existing_file(renderer.base, image["inline"], "inline figure")
    if source.suffix == ".svg":
        return _inline_frame(
            _svg_document(source.read_text(encoding="utf-8")), alt, style
        )
    return _inline_frame(source.read_text(encoding="utf-8"), alt, style)


# cost: time O(n), heap O(n), stack O(1)
# vars: n = 표 셀·정렬·너비 설정의 전체 글자 수
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


# cost: time O(n + r), heap O(n + o), stack O(1), io O(f)
# vars: n = 이 호출의 전체 입력 글자 수, r = 하위 외부 렌더 시간 합, o = 그림 포함 출력 바이트 수, f = 그림 수
# basis: estimate
def _option(
    option: dict[str, Any], renderer: FigureRenderer, controls: str = ""
) -> str:
    body = "".join(_picture(image, renderer) for image in option.get("images", []))
    if "text" in option:
        body += f'<pre class="msg">{html.escape(option["text"])}</pre>'
    if "table" in option:
        body += _table(option["table"])
    class_name = "col mock" if option.get("mock") else "col"
    return f'<div class="{class_name}"><h4>{_inline(option["label"])}</h4>{body}{controls}</div>'


# cost: time O(n + r), heap O(n + o), stack O(1), io O(f)
# vars: n = 이 호출의 전체 입력 글자 수, r = 하위 외부 렌더 시간 합, o = 그림 포함 출력 바이트 수, f = 그림 수
# basis: estimate
def _options(
    options: list[dict[str, Any]], renderer: FigureRenderer, question_number: int = 0
) -> str:
    cards = []
    for index, option in enumerate(options, 1):
        label = html.escape(option["label"])
        controls = (
            (
                f'<div class="option-feedback"><label class="option-select"><input type="radio" '
                f'name="q{question_number}" value="option-{index}" data-choice data-label="{label}">이 안 선택</label>'
                f'<textarea data-option-note="option-{index}" data-label="{label}" aria-label="{label} 수정 의견" '
                'rows="2" placeholder="좋은 점이나 바꿀 점을 적어 주세요"></textarea></div>'
            )
            if question_number
            else ""
        )
        cards.append(_option(option, renderer, controls))
    return f'<div class="cols c{min(max(len(options), 1), MAX_COLUMNS)}">{"".join(cards)}</div>'


KINDS = {
    "decision": {"what": "무슨 질문인가", "bad": "나쁜 점", "rec": "추천"},
    "result": {"what": "무엇이 바뀌었나", "bad": "남은 문제", "rec": "판단"},
}


# cost: time O(n + r), heap O(n + o), stack O(1), io O(f)
# vars: n = 이 호출의 전체 입력 글자 수, r = 하위 외부 렌더 시간 합, o = 그림 포함 출력 바이트 수, f = 그림 수
# basis: estimate
def _question(
    number: int,
    question: dict[str, Any],
    renderer: FigureRenderer,
    kind: str,
    *,
    review: bool = False,
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
    evidence = (
        '<table class="effect"><thead><tr><th></th><th>좋은 점</th>'
        f"<th>{words['bad']}</th></tr></thead><tbody>{effect}</tbody></table>"
        f'{checks}<p class="rec"><b>{words["rec"]} {_inline(recommendation)}</b> {_inline(reason)}</p>'
    )
    actions = ""
    if review:
        evidence = f'<details class="review-reasons"><summary>비교 근거 보기</summary>{evidence}</details>'
        actions = (
            '<div class="decision-actions">'
            + "".join(
                f'<label><input type="radio" name="q{number}" value="{value}" data-choice data-label="{label}"'
                f"{' checked' if not value else ''}>{label}</label>"
                for value, label in [
                    ("", "미선택"),
                    ("hold", "보류"),
                    ("revise", "다시 제안"),
                ]
            )
            + "</div>"
        )
    marker = " data-question" if review else ""
    prefix = "" if review else f"<b>{words['what']}</b> "
    return (
        f'<section id="q{number}"{marker}><h2>{number:02d}. {_inline(question["title"])}</h2>'
        f'<p class="what">{prefix}{_inline(question["what"])}</p>'
        f"{_options(question['options'], renderer, number if review else 0)}{actions}{extra}{note}{evidence}</section>"
    )


IMAGE_SUFFIXES = {".png", ".gif", ".jpg", ".jpeg", ".webp", ".svg"}
EXPLAIN_FONTS = ("pretendard-variable.woff2", "jetbrains-mono-regular.woff2")
THEME_BUTTONS = (
    '<div class="theme app-tablist is-segmented" role="group" aria-label="테마">'
    '<button type="button" data-mode="system" aria-pressed="true">시스템</button>'
    '<button type="button" data-mode="light" aria-pressed="false">라이트</button>'
    '<button type="button" data-mode="dark" aria-pressed="false">다크</button></div>'
)


def _thinkflow_source(value: str, where: str) -> None:
    if not value.endswith(".thinkflow"):
        raise ReportError(f"{where} must end with .thinkflow")


# cost: time O(s + p), heap O(s), stack O(1)
# vars: s = 절 수, p = 문단 수
# basis: estimate
def _check_explain(spec: dict[str, Any]) -> None:
    _need(spec, "title", "input", str)
    _need(spec, "lead", "input", str)
    sections = _need(spec, "sections", "input", list)
    if not sections:
        raise ReportError("sections must not be empty")
    stems: dict[str, str] = {}
    for number, section in enumerate(sections, 1):
        at = f"sections[{number}]"
        _need(section, "title", at, str)
        text = _need(section, "text", at, list)
        if not text or not all(isinstance(line, str) and line.strip() for line in text):
            raise ReportError(f"{at}.text needs non-empty paragraphs")
        if "figure" in section:
            _thinkflow_source(_need(section, "figure", at, str), f"{at}.figure")
            stem = Path(section["figure"]).stem
            if stem in stems:
                raise ReportError(f"{at}.figure file name repeats {stems[stem]}")
            stems[stem] = at
        if "image" in section and Path(_need(section, "image", at, str)).suffix.lower() not in IMAGE_SUFFIXES:
            raise ReportError(f"{at}.image must be one of {sorted(IMAGE_SUFFIXES)}")
        for item in section.get("files", []):
            if not isinstance(item, str) or not item:
                raise ReportError(f"{at}.files must list file paths")


# cost: time O(n + r), heap O(n + o), stack O(1), io O(f + t)
# vars: n = 입력 글자 수, r = 렌더 시간 합, o = 출력 바이트 수, f = 그림 수, t = 복사하는 테마 파일 수
# basis: estimate
def build_explain(spec: dict[str, Any], renderer: FigureRenderer, output: Path, head: str) -> str:
    """블로그 테마 글 한 편: 절마다 짧은 글과 ThinkFlow 재생기 iframe."""
    _check_explain(spec)
    parts = []
    for number, section in enumerate(spec["sections"], 1):
        body = "".join(f"<p>{_inline(line)}</p>" for line in section["text"])
        if "figure" in section:
            source = _existing_file(renderer.base, section["figure"], "thinkflow figure")
            renderer.render(source, output.parent / "figures", static=False)
            svg = (output.parent / "figures" / f"{source.stem}.svg").read_text(encoding="utf-8")
            box = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
            size = f' width="{round(float(box[1]))}" height="{round(float(box[2]))}"' if box else ""
            # 그림은 자기 캔버스 폭까지 본문 밖으로 넓히고 화면이 좁으면 화면 폭에 맞춘다.
            fit = f' style="--component-width-wide:min({round(float(box[1]))}px, calc(100vw - 2 * var(--primitive-gutter)))"' if box else ""
            caption = section.get("caption", "")
            body += (
                f'<figure class="app-diagram app-figure app-width-wide"{fit}><iframe data-diagram src="figures/{html.escape(source.stem)}.html"'
                f' title="{html.escape(caption or section["title"], quote=True)}"{size} loading="lazy" allow="fullscreen; clipboard-write" allowfullscreen></iframe>'
                f'{f"<figcaption>{_inline(caption)}</figcaption>" if caption else ""}</figure>'
            )
        if "image" in section:
            name = _attach(renderer.base, section["image"], output.parent)
            alt = html.escape(section.get("caption", section["title"]), quote=True)
            body += f'<figure class="app-figure"><img src="attachments/{html.escape(name)}" alt="{alt}" loading="lazy"><figcaption>{_inline(section.get("caption", ""))}</figcaption></figure>'
        if section.get("files"):
            links = "".join(
                f'<li><a href="attachments/{html.escape(name)}" download><code>{html.escape(name)}</code></a></li>'
                for name in (_attach(renderer.base, item, output.parent) for item in section["files"])
            )
            body += f"<ul>{links}</ul>"
        parts.append(f'<section id="s{number}"><h2>{_inline(section["title"])}</h2>{body}</section>')
    return _page(spec["title"], spec["lead"], f'<article class="app-prose">{"".join(parts)}</article>', head=head)


# cost: time O(b), heap O(1), stack O(1), io 2
# vars: b = 첨부 파일 바이트
# basis: estimate
def _attach(base: Path, relative: str, folder: Path) -> str:
    """설명 페이지가 혼자 열리도록 첨부를 `attachments/`에 복사하고 이름을 돌려준다. 이름이 겹치면 실패한다."""
    source = _existing_file(base, relative, "attachment")
    target = folder / "attachments" / source.name
    target.parent.mkdir(exist_ok=True)
    if target.exists() and target.read_bytes() != source.read_bytes():
        raise ReportError(f"attachment name repeats: {source.name}")
    shutil.copyfile(source, target)
    return source.name


# cost: time O(t), heap O(1), stack O(1), io O(t)
# vars: t = 복사하는 테마 파일 수
# basis: estimate
def theme_head(thinkflow: Thinkflow, folder: Path) -> str:
    """두 종류가 함께 쓰는 공통 테마를 출력 폴더에 복사하고 head 링크를 돌려준다."""
    target = folder / "theme"
    (target / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    for name in ("tokens.css", "styles.css"):
        shutil.copyfile(thinkflow.theme / name, target / name)
    for name in EXPLAIN_FONTS:
        shutil.copyfile(thinkflow.theme / "assets" / "fonts" / name, target / "assets" / "fonts" / name)
    host = (thinkflow.theme / "ui" / "runtime" / "diagram-host.js").read_text(encoding="utf-8")
    host = host.replace("export function", "function", 1) + "\nbindDiagramHost();"
    (target / "diagram-host.js").write_text(host, encoding="utf-8")
    return (
        '<link rel="stylesheet" href="theme/tokens.css"><link rel="stylesheet" href="theme/styles.css">'
        '<script src="theme/diagram-host.js" defer></script>'
    )


# cost: time O(n), heap O(n), stack O(1)
# vars: n = 본문 글자 수
# basis: estimate
def _page(title: str, lead: str, content: str, *, head: str, styles: str = "", script: str = "", wide: bool = False, body_class: str = "") -> str:
    """설명·비교가 같은 블로그 틀(제목, 요약, 테마 전환, 본문 폭)을 쓴다."""
    width = ' style="max-width:var(--spacing-figure-figure-canvas-wide)"' if wide else ""
    style = f"<style>{styles}</style>" if styles else ""
    tail = f"<script>{script}</script>" if script else ""
    return (
        f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{html.escape(title)}</title>{head}{style}<script>{THEME_SCRIPT}</script></head><body{body_class}>"
        f'<main style="padding-inline:var(--primitive-gutter)"><div class="app-blog-post"{width}>{THEME_BUTTONS}'
        f'<div class="app-prose"><h1 class="app-article-title">{html.escape(title)}</h1><p class="app-article-lead">{_inline(lead)}</p></div>'
        f"{content}</div></main>{tail}</body></html>"
    )


# cost: time O(n + r), heap O(n + o), stack O(1), io O(f)
# vars: n = 이 호출의 전체 입력 글자 수, r = 하위 외부 렌더 시간 합, o = 그림 포함 출력 바이트 수, f = 그림 수
# basis: estimate
def build(spec: dict[str, Any], renderer: FigureRenderer, head: str) -> str:
    _validate(spec)
    kind = spec.get("kind", "decision")
    questions = spec["questions"]
    sections = "".join(
        _question(number, question, renderer, kind, review="review" in spec)
        for number, question in enumerate(questions, 1)
    )
    review = ""
    if "review" in spec:
        sections, review = _review(
            spec, sections, renderer.base, head + CSS + REVIEW_CSS
        )
    navigation = "".join(
        f'<a href="#q{number}" title="{html.escape(question["title"])}"><span>{number}</span>'
        f'<span class="nav-title">{_inline(_nav_title(question["title"]))}</span></a>'
        for number, question in enumerate(questions, 1)
    )
    styles = CSS + REVIEW_CSS if review else CSS
    body_class = ' class="review-page"' if review else ""
    script = REVIEW_SCRIPT if review else NAVIGATION_SCRIPT
    nav = "" if review else f'<nav aria-label="보고서 섹션">{navigation}</nav>'
    return _page(spec["title"], spec["intro"], f"{nav}{review}{sections}", head=head, styles=styles, script=script, wide=True, body_class=body_class)


# cost: time O(n + b), heap O(n + b), stack O(1), io O(f)
# vars: n = 보고서 길이, b = 외부 그림 바이트, f = 외부 그림 수
# basis: estimate
def _review(
    spec: dict[str, Any], sections: str, base: Path, styles: str
) -> tuple[str, str]:
    digest = hashlib.sha256(
        (json.dumps(spec, ensure_ascii=False) + sections + styles).encode()
    )
    for source in re.findall(r'<img src="([^"]+)"', sections):
        digest.update((base / html.unescape(source)).read_bytes())
    panel = (
        f'<div class="review" data-review="{digest.hexdigest()}" data-version="{html.escape(spec["review"])}">'
        '<div class="review-toolbar"><label><select aria-label="보기" data-review-filter><option value="all">전체 보기</option>'
        '<option value="pending">미선택</option><option value="selected">선택 완료</option>'
        '<option value="revise">다시 제안</option><option value="hold">보류</option></select></label>'
        '<output data-review-count aria-live="polite"></output>'
        '<button class="copy-button" type="button" data-review-copy>선택 결과 복사</button></div>'
        '<details><summary>전달할 내용 확인</summary><textarea data-review-output aria-label="선택 결과 JSON" rows="8" readonly></textarea></details>'
        '<p data-review-notice role="status"></p><p data-review-empty hidden>해당 항목이 없습니다. 전체 보기로 돌아가세요.</p></div>'
    )
    return sections, panel


# cost: time O(p), heap O(p), stack O(1), io O(p)
# vars: p = PATH의 탐색 항목 수와 경로 길이
# basis: estimate
def _thinkflow(value: str | None) -> Thinkflow | None:
    configured = value or os.environ.get("THINKFLOW_PATH") or shutil.which("thinkflow")
    if not configured:
        return None
    path = Path(configured).expanduser().resolve()
    root = path if path.is_dir() else next((p for p in path.parents if (p / "src" / "cli.js").is_file()), path)
    cli, theme = root / "src" / "cli.js", root / "src" / "vendor" / "theme"
    if not cli.is_file() or not (theme / "tokens.css").is_file():
        raise ReportError(f"invalid thinkflow path: {path}")
    return Thinkflow(cli=cli, theme=theme)


# cost: time O(1), heap O(1), stack O(1)
# basis: estimate
def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "output", type=Path, nargs="?", help="output HTML in the same folder as input"
    )
    parser.add_argument("--thinkflow", help="thinkflow checkout or src/cli.js path")
    parser.add_argument(
        "--static",
        action="store_true",
        help="embed a static SVG in the report iframe",
    )
    return parser.parse_args()


# cost: time O(n + r), heap O(n + o), stack O(1), io O(f + p)
# vars: n = JSON·토큰 입력 바이트 수, r = 외부 렌더 시간 합, o = 출력 바이트 수, f = 그림 수, p = PATH 탐색 항목 수
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
        thinkflow = _thinkflow(arguments.thinkflow)
        renderer = FigureRenderer(
            base=source.parent, thinkflow=thinkflow, static=arguments.static
        )
        if thinkflow is None:
            raise ReportError("report needs --thinkflow or THINKFLOW_PATH for the shared theme")
        head = theme_head(thinkflow, output.parent)
        if isinstance(spec, dict) and spec.get("kind") == "explain":
            page = build_explain(spec, renderer, output, head)
        else:
            page = build(spec, renderer, head)
        output.write_text(page, encoding="utf-8")
    except (OSError, ValueError, ReportError) as error:
        sys.exit(f"build_report.py: {error}")
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
