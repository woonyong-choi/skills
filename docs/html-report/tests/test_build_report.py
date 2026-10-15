"""ThinkFlow 그림이 이미지가 아닌 인라인 문서로 들어가는지 검사한다."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "inline-thinkflow"
BUILD = ROOT / "docs" / "html-report" / "scripts" / "build_report.py"
PLAYWRIGHT_ROOTS = (
    Path.home() / ".local" / "lib" / "node_modules",
    ROOT.parent.parent / "oss" / "thinkflow" / "node_modules",
)


class ReportParser(HTMLParser):
    """보고서의 이미지와 ThinkFlow iframe 속성을 모은다."""

    def __init__(self) -> None:
        super().__init__()
        self.images: list[dict[str, str | None]] = []
        self.frames: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "img":
            self.images.append(dict(attrs))
        if tag == "iframe":
            self.frames.append(dict(attrs))


class InlineThinkflowReportTest(unittest.TestCase):
    """두 ThinkFlow 재생기가 독립 iframe 문서로 생성되는지 확인한다."""

    thinkflow: Path | None = None

    @classmethod
    def setUpClass(cls) -> None:
        if cls.thinkflow is not None:
            return
        thinkflow = os.environ.get("THINKFLOW_PATH")
        if not thinkflow:
            raise unittest.SkipTest(
                "thinkflow path is not configured; set THINKFLOW_PATH to the checkout root "
                "or run this script with --thinkflow <path>"
            )
        cls.thinkflow = Path(thinkflow).resolve()

    def _build_navigation_report(self, options: int = 1) -> str:
        module_spec = importlib.util.spec_from_file_location("build_report", BUILD)
        self.assertIsNotNone(module_spec)
        self.assertIsNotNone(module_spec.loader)
        module = importlib.util.module_from_spec(module_spec)
        sys.modules[module_spec.name] = module
        module_spec.loader.exec_module(module)
        questions = [
            {
                "title": f"탐색 칩 {number}: 여러 섹션을 한 줄로 표시",
                "what": "섹션이 많아도 탐색 칩은 한 줄로 남아야 합니다. 활성 섹션은 가로 스크롤로 보입니다.",
                "options": [
                    {"label": f"확인 {index}", "text": "탐색 칩 대비와 스크롤을 확인합니다."}
                    for index in range(1, options + 1)
                ],
                "effect": [["칩", "한 줄 표시", "가로 공간이 더 필요함"]],
                "rec": ["후", "활성 칩이 보이는 위치로 이동합니다."],
            }
            for number in range(1, 17)
        ]
        report = {
            "kind": "result",
            "title": "탐색 칩 검사",
            "intro": "접근성 검사 보고서",
            "questions": questions,
        }
        renderer = module.FigureRenderer(base=FIXTURE, thinkflow=None, static=False)
        theme = module._thinkflow(str(self.thinkflow)).theme
        head = "<style>" + (theme / "tokens.css").read_text(encoding="utf-8") + (theme / "styles.css").read_text(encoding="utf-8") + "</style>"
        return module.build(report, renderer, head)

    def _playwright_root(self) -> Path | None:
        candidates = (*PLAYWRIGHT_ROOTS, self.thinkflow / "node_modules")
        for root in candidates:
            if (root / "playwright-core" / "package.json").is_file():
                return root
        return None

    def test_thinkflow_figures_use_inline_svg_documents_not_images(self) -> None:
        output = FIXTURE / "index.html"
        command = [
            sys.executable,
            str(BUILD),
            str(FIXTURE / "input.json"),
            str(output),
            "--thinkflow",
            str(self.thinkflow),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)

        parser = ReportParser()
        report = output.read_text(encoding="utf-8")
        parser.feed(report)

        self.assertEqual(parser.images, [])
        self.assertEqual(len(parser.frames), 2)
        self.assertIn("thinkflow-theme", report)
        self.assertIn('data-mode="system"', report)
        self.assertIn('data-mode="light"', report)
        self.assertIn('data-mode="dark"', report)
        for frame in parser.frames:
            self.assertIn("data-diagram", frame)
            document = frame.get("srcdoc")
            self.assertIsNotNone(document)
            self.assertIn("<svg", document)
            self.assertIn("fl-figure", document)

    def test_explain_page_uses_theme_and_diagram_host(self) -> None:
        # #62: 설명 페이지는 공통 테마 파일과 재생기 호스트, 그림마다 재생기 iframe을 쓴다.
        folder = FIXTURE / "explain"
        folder.mkdir(exist_ok=True)
        spec = {"kind": "explain", "title": "요청 구조", "lead": "요청이 서버로 간다", "sections": [
            {"title": "흐름", "text": ["클라이언트가 요청한다"], "figure": "../flow-a.thinkflow", "caption": "요청"},
            {"title": "재시도", "text": ["실패하면 다시 보낸다"], "figure": "../flow-b.thinkflow"},
            {"title": "로그", "text": ["실행 화면"], "image": "terminal.svg", "caption": "실행 로그", "files": ["../input.json"]},
        ]}
        (folder / "terminal.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>', encoding="utf-8")
        (folder / "input.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        command = [sys.executable, str(BUILD), str(folder / "input.json"), "--thinkflow", str(self.thinkflow)]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        try:
            self.assertEqual(completed.returncode, 0, completed.stderr)
            page = (folder / "index.html").read_text(encoding="utf-8")
            parser = ReportParser()
            parser.feed(page)
            self.assertEqual([frame["src"] for frame in parser.frames], ["figures/flow-a.html", "figures/flow-b.html"])
            self.assertIn('src="theme/diagram-host.js"', page)
            self.assertIn("bindDiagramHost()", (folder / "theme" / "diagram-host.js").read_text(encoding="utf-8"))
            self.assertIn('class="app-blog-post"', page)
            self.assertIn('src="attachments/terminal.svg"', page)
            self.assertIn('href="attachments/input.json" download', page)
            for name in ("attachments/terminal.svg", "attachments/input.json", "theme/tokens.css", "theme/styles.css", "theme/assets/fonts/pretendard-variable.woff2", "figures/flow-a.html", "figures/flow-b.html"):
                self.assertTrue((folder / name).is_file(), name)
        finally:
            shutil.rmtree(folder)

    def test_capture_step_sets_viewport_to_scroll_height(self) -> None:
        # #64: 전체 페이지 캡처는 화면 밖 srcdoc iframe이 빈칸으로 남아 뷰포트를 문서 높이로 키운 뒤 찍는다.
        skill = (ROOT / "docs" / "html-report" / "SKILL.md").read_text(encoding="utf-8")
        step = next(line for line in skill.splitlines() if line.startswith("5. ") and "index.png" in line)
        self.assertIn("scrollHeight", step)

    def test_explain_rebuild_after_attachment_change(self) -> None:
        # #64: 첨부를 바꾼 뒤 다시 만들면 이전 사본을 덮어쓰고, 한 실행 안의 이름 겹침만 실패한다.
        folder = FIXTURE / "explain-rebuild"
        folder.mkdir(exist_ok=True)
        (folder / "sub").mkdir(exist_ok=True)
        spec = {"kind": "explain", "title": "재생성", "lead": "첨부 변경", "sections": [
            {"title": "로그", "text": ["실행 화면"], "files": ["data.txt"]},
        ]}
        (folder / "input.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        command = [sys.executable, str(BUILD), str(folder / "input.json"), "--thinkflow", str(self.thinkflow)]
        try:
            (folder / "data.txt").write_text("v1", encoding="utf-8")
            first = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(first.returncode, 0, first.stderr)
            (folder / "data.txt").write_text("v2", encoding="utf-8")
            second = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual((folder / "attachments" / "data.txt").read_text(encoding="utf-8"), "v2")
            (folder / "sub" / "data.txt").write_text("other", encoding="utf-8")
            spec["sections"][0]["files"].append("sub/data.txt")
            (folder / "input.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            clash = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertNotEqual(clash.returncode, 0)
            self.assertIn("attachment name repeats", clash.stderr)
        finally:
            shutil.rmtree(folder)

    def test_raster_image_links_to_full_size(self) -> None:
        # 높이 상한으로 줄어든 캡처는 원본 링크로 열 수 있다.
        module_spec = importlib.util.spec_from_file_location("build_report", BUILD)
        module = importlib.util.module_from_spec(module_spec)
        sys.modules[module_spec.name] = module
        module_spec.loader.exec_module(module)
        renderer = module.FigureRenderer(base=FIXTURE, thinkflow=None, static=False)
        figure = module._picture({"src": "flow-a.thinkflow", "alt": "전체 화면"}, renderer)
        self.assertIn('<a href="flow-a.thinkflow" target="_blank"><img src="flow-a.thinkflow"', figure)
        self.assertIn(".frame>a{display:block", module.CSS)

    def test_explain_captions_keep_contrast_in_both_themes(self) -> None:
        # 테마 캡션 색은 다크 값이 없어 생성 CSS가 보조 글자 색으로 덮는다.
        playwright_root = self._playwright_root()
        if playwright_root is None or shutil.which("node") is None:
            self.skipTest("installed Playwright browser is unavailable")
        folder = FIXTURE / "explain-caption"
        folder.mkdir(exist_ok=True)
        spec = {"kind": "explain", "title": "캡션", "lead": "캡션 대비", "sections": [
            {"title": "흐름", "text": ["요청"], "figure": "../flow-a.thinkflow", "caption": "그림 캡션"},
            {"title": "화면", "text": ["화면"], "image": "shot.svg", "caption": "이미지 캡션"},
        ]}
        (folder / "shot.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>', encoding="utf-8")
        (folder / "input.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        script = r"""
const { createRequire } = await import('node:module');
const { chromium } = createRequire(`${process.env.PLAYWRIGHT_REQUIRE_ROOT}/`)('playwright-core');
const browser = await chromium.launch();
const result = {};
for (const mode of ['light', 'dark']) {
  const page = await browser.newPage({ colorScheme: mode });
  await page.goto(process.env.REPORT_URL);
  await page.locator(`.theme button[data-mode="${mode}"]`).click();
  result[mode] = await page.evaluate(() => {
    const rgba = (value) => { const v = value.match(/[\d.]+/g).map(Number); return [v[0], v[1], v[2], v.length > 3 ? v[3] : 1]; };
    const lum = (c) => c.slice(0, 3).map((x) => { x /= 255; return x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }).reduce((s, x, i) => s + x * [0.2126, 0.7152, 0.0722][i], 0);
    return [...document.querySelectorAll('.app-prose .app-figure figcaption')].map((caption) => {
      let node = caption, bg = [0, 0, 0, 0];
      while (node && bg[3] === 0) { bg = rgba(getComputedStyle(node).backgroundColor); node = node.parentElement; }
      const fg = rgba(getComputedStyle(caption).color);
      const mixed = fg.slice(0, 3).map((x, i) => x * fg[3] + bg[i] * (1 - fg[3]));
      const [a, b] = [lum(mixed), lum(bg)].sort((x, y) => y - x);
      return (a + 0.05) / (b + 0.05);
    });
  });
  await page.close();
}
await browser.close();
process.stdout.write(JSON.stringify(result));
"""
        try:
            command = [sys.executable, str(BUILD), str(folder / "input.json"), "--thinkflow", str(self.thinkflow)]
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            completed = subprocess.run(
                ["node", "--input-type=module", "-e", script],
                capture_output=True,
                check=False,
                env=os.environ | {"PLAYWRIGHT_REQUIRE_ROOT": str(playwright_root), "REPORT_URL": (folder / "index.html").as_uri()},
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            ratios = json.loads(completed.stdout)
            for mode in ("light", "dark"):
                self.assertEqual(len(ratios[mode]), 2)
                for ratio in ratios[mode]:
                    self.assertGreaterEqual(ratio, 4.5, mode)
        finally:
            shutil.rmtree(folder)

    def test_offscreen_figure_frames_match_content_height(self) -> None:
        # #66: 화면 밖 sandbox iframe은 렌더링이 멈춰 재생기가 높이를 못 보내 240px에 머물렀다.
        playwright_root = self._playwright_root()
        if playwright_root is None or shutil.which("node") is None:
            self.skipTest("installed Playwright browser is unavailable")
        folder = FIXTURE / "frame-height"
        (folder / "explain").mkdir(parents=True, exist_ok=True)
        report = json.loads((FIXTURE / "input.json").read_text(encoding="utf-8"))
        for option in report["questions"][0]["options"]:
            for image in option["images"]:
                image["thinkflow"] = f"../{image['thinkflow']}"
        explain = {"kind": "explain", "title": "높이", "lead": "그림 높이", "sections": [
            {"title": f"흐름 {name}", "text": ["설명 " * 400], "figure": f"../../flow-{name}.thinkflow"} for name in ("a", "b")
        ]}
        (folder / "input.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        (folder / "explain" / "input.json").write_text(json.dumps(explain, ensure_ascii=False), encoding="utf-8")
        script = r"""
const { createRequire } = await import('node:module');
const { chromium } = createRequire(`${process.env.PLAYWRIGHT_REQUIRE_ROOT}/`)('playwright-core');
const browser = await chromium.launch();
const result = [];
for (const url of JSON.parse(process.env.REPORT_URLS)) for (const width of [390, 1280]) for (const mode of ['light', 'dark']) {
  const page = await browser.newPage({ viewport: { width, height: 800 }, colorScheme: mode });
  await page.goto(url);
  await page.locator(`.theme button[data-mode="${mode}"]`).click();
  await page.waitForTimeout(1500);
  const frames = await page.evaluate(() => [...document.querySelectorAll('iframe[data-diagram]')].map((frame) => {
    const box = frame.getBoundingClientRect();
    return { top: Math.round(box.top), height: Math.round(box.height) };
  }));
  const contents = [];
  for (const frame of page.frames().slice(1)) contents.push(await frame.evaluate(() => Math.ceil(document.body.getBoundingClientRect().height)));
  result.push({ url, width, mode, frames, contents });
  await page.close();
}
await browser.close();
process.stdout.write(JSON.stringify(result));
"""
        try:
            for spec in (folder / "input.json", folder / "explain" / "input.json"):
                command = [sys.executable, str(BUILD), str(spec), "--thinkflow", str(self.thinkflow)]
                completed = subprocess.run(command, capture_output=True, text=True, check=False)
                self.assertEqual(completed.returncode, 0, completed.stderr)
            urls = [(folder / "index.html").as_uri(), (folder / "explain" / "index.html").as_uri()]
            completed = subprocess.run(
                ["node", "--input-type=module", "-e", script],
                capture_output=True,
                check=False,
                env=os.environ | {"PLAYWRIGHT_REQUIRE_ROOT": str(playwright_root), "REPORT_URLS": json.dumps(urls)},
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            for run in json.loads(completed.stdout):
                label = f"{run['url']} {run['width']} {run['mode']}"
                self.assertEqual(len(run["frames"]), 2, label)
                if run["width"] == 390:
                    # 두 번째 그림이 첫 화면 밖에 있어야 이 회귀를 재현한다.
                    self.assertGreater(run["frames"][1]["top"], 800, label)
                self.assertEqual([frame["height"] for frame in run["frames"]], run["contents"], label)
        finally:
            shutil.rmtree(folder)

    def test_navigation_chips_use_state_tokens_and_single_row_css(self) -> None:
        report = self._build_navigation_report()

        self.assertIn("--report-chip-active-fill:var(--color-state-active-fill", report)
        self.assertIn("--report-chip-active-ink:var(--color-state-on-active", report)
        self.assertIn("flex-wrap:nowrap", report)
        self.assertIn("overflow-x:auto", report)
        self.assertIn("activeLink.scrollIntoView", report)

    def test_comparison_columns_collapse_to_one_on_narrow_screens(self) -> None:
        playwright_root = self._playwright_root()
        if playwright_root is None or shutil.which("node") is None:
            self.skipTest("installed Playwright browser is unavailable")
        script = r"""
const { createRequire } = await import('node:module');
const { chromium } = createRequire(`${process.env.PLAYWRIGHT_REQUIRE_ROOT}/`)('playwright-core');
let html = '';
for await (const chunk of process.stdin) html += chunk;
const browser = await chromium.launch();
const columns = {};
for (const width of [390, 900]) {
  const page = await browser.newPage({ viewport: { width, height: 700 } });
  await page.setContent(html);
  columns[width] = await page.evaluate(() => getComputedStyle(document.querySelector('.cols')).gridTemplateColumns.split(' ').length);
  await page.close();
}
await browser.close();
process.stdout.write(JSON.stringify(columns));
"""
        completed = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            input=self._build_navigation_report(options=2),
            capture_output=True,
            check=False,
            env=os.environ | {"PLAYWRIGHT_REQUIRE_ROOT": str(playwright_root)},
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout), {"390": 1, "900": 2})

    def test_navigation_chips_have_aa_contrast_and_stay_in_one_row(self) -> None:
        playwright_root = self._playwright_root()
        if playwright_root is None or shutil.which("node") is None:
            self.skipTest(
                "installed Playwright browser is unavailable; CSS token test ran"
            )

        script = r"""
const { createRequire } = await import('node:module');
const requireFromPlaywright = createRequire(`${process.env.PLAYWRIGHT_REQUIRE_ROOT}/`);
const { chromium } = requireFromPlaywright('playwright-core');
const html = await new Promise((resolve) => {
  let source = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', (chunk) => { source += chunk; });
  process.stdin.on('end', () => { resolve(source); });
});
function contrast(color, background) {
  const channels = (value) => value.match(/\d+(?:\.\d+)?/g).slice(0, 3).map(Number);
  const luminance = (value) => channels(value).map((channel) => {
    const normalized = channel / 255;
    return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
  }).reduce((sum, channel, index) => sum + channel * [0.2126, 0.7152, 0.0722][index], 0);
  const [first, second] = [luminance(color), luminance(background)].sort((left, right) => right - left);
  return (first + 0.05) / (second + 0.05);
}
function chipStyle(element) {
  const style = getComputedStyle(element);
  return {
    color: style.color,
    background: style.backgroundColor,
    border: style.borderColor,
    outline: style.outlineColor,
    contrast: contrast(style.color, style.backgroundColor),
  };
}
const browser = await chromium.launch();
const measurements = {};
for (const [name, colorScheme, mode] of [['system-light', 'light', 'system'], ['system-dark', 'dark', 'system'], ['light', 'dark', 'light'], ['dark', 'light', 'dark']]) {
  const context = await browser.newContext({ colorScheme, viewport: { width: 900, height: 700 } });
  const page = await context.newPage();
  await page.setContent(html);
  await page.locator(`.theme button[data-mode="${mode}"]`).click();
  await page.addScriptTag({ content: `${contrast.toString()}\n${chipStyle.toString()}\nwindow.reportChipStyle = chipStyle;` });
  const normal = page.locator('nav a:not(.is-active)').first();
  const active = page.locator('nav a.is-active');
  const normalStyle = await normal.evaluate((element) => window.reportChipStyle(element));
  await normal.hover();
  const hoverStyle = await normal.evaluate((element) => window.reportChipStyle(element));
  await normal.focus();
  const focusStyle = await normal.evaluate((element) => window.reportChipStyle(element));
  const activeStyle = await active.evaluate((element) => window.reportChipStyle(element));
  await page.evaluate(() => window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'instant' }));
  // scrollLeft는 정수지만 글꼴 레이아웃 경계는 소수라 같은 CSS 픽셀로 비교한다.
  await page.waitForFunction(() => {
    const nav = document.querySelector('nav');
    const active = nav.querySelector('a.is-active').getBoundingClientRect();
    const bounds = nav.getBoundingClientRect();
    return nav.scrollLeft > 0 && Math.round(active.left) >= Math.round(bounds.left) && Math.round(active.right) <= Math.round(bounds.right);
  }, null, { timeout: 5000 }).catch(async (error) => {
    const state = await page.evaluate(() => {
      const nav = document.querySelector('nav');
      return { scrollY, height: document.documentElement.scrollHeight, nav: nav.getBoundingClientRect().toJSON(), active: nav.querySelector('a.is-active').getBoundingClientRect().toJSON(), scrollLeft: nav.scrollLeft };
    });
    throw new Error(`${error.message}: ${JSON.stringify(state)}`);
  });
  const navigation = await page.evaluate(() => {
    const nav = document.querySelector('nav');
    const activeChip = nav.querySelector('a.is-active');
    const navRect = nav.getBoundingClientRect();
    const activeRect = activeChip.getBoundingClientRect();
    const rows = [...new Set([...nav.querySelectorAll('a')].map((chip) => Math.round(chip.getBoundingClientRect().top)))];
    return {
      activeVisible: Math.round(activeRect.left) >= Math.round(navRect.left) && Math.round(activeRect.right) <= Math.round(navRect.right),
      horizontalOverflow: nav.scrollWidth > nav.clientWidth,
      rows,
      scrollHeight: nav.scrollHeight,
      clientHeight: nav.clientHeight,
      scrollLeft: nav.scrollLeft,
    };
  });
  measurements[name] = { normal: normalStyle, hover: hoverStyle, focus: focusStyle, active: activeStyle, navigation };
  await context.close();
}
await browser.close();
process.stdout.write(JSON.stringify(measurements));
"""
        environment = os.environ | {"PLAYWRIGHT_REQUIRE_ROOT": str(playwright_root)}
        completed = subprocess.run(
            ["node", "-e", script],
            input=self._build_navigation_report(),
            capture_output=True,
            check=False,
            env=environment,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        measurements = json.loads(completed.stdout)
        for mode in ("system-light", "system-dark", "light", "dark"):
            for state in ("normal", "hover", "focus", "active"):
                self.assertGreaterEqual(measurements[mode][state]["contrast"], 4.5)
            navigation = measurements[mode]["navigation"]
            self.assertTrue(navigation["horizontalOverflow"])
            self.assertEqual(len(navigation["rows"]), 1)
            self.assertLessEqual(
                navigation["scrollHeight"], navigation["clientHeight"] + 1
            )
            self.assertTrue(navigation["activeVisible"])
            self.assertGreater(navigation["scrollLeft"], 0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--thinkflow", type=Path, required=True)
    arguments, unittest_args = parser.parse_known_args()
    InlineThinkflowReportTest.thinkflow = arguments.thinkflow.resolve()
    unittest.main(argv=[sys.argv[0], *unittest_args])


if __name__ == "__main__":
    main()
