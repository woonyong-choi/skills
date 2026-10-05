"""Daphnis 그림이 이미지가 아닌 인라인 문서로 들어가는지 검사한다."""

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
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "inline-daphnis"
BUILD = ROOT / "docs" / "html-report" / "scripts" / "build_report.py"
PLAYWRIGHT_ROOTS = (
    Path.home() / ".local" / "lib" / "node_modules",
    ROOT.parent.parent / "oss" / "daphnis" / "node_modules",
)


class ReportParser(HTMLParser):
    """보고서의 이미지와 Daphnis iframe 속성을 모은다."""

    def __init__(self) -> None:
        super().__init__()
        self.images: list[dict[str, str | None]] = []
        self.frames: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "img":
            self.images.append(dict(attrs))
        if tag == "iframe":
            self.frames.append(dict(attrs))


class InlineDaphnisReportTest(unittest.TestCase):
    """두 Daphnis 재생기가 독립 iframe 문서로 생성되는지 확인한다."""

    daphnis: Path | None = None

    @classmethod
    def setUpClass(cls) -> None:
        if cls.daphnis is not None:
            return
        daphnis = os.environ.get("DAPHNIS_PATH")
        if not daphnis:
            raise unittest.SkipTest(
                "daphnis path is not configured; set DAPHNIS_PATH to the checkout root "
                "or run this script with --daphnis <path>"
            )
        cls.daphnis = Path(daphnis).resolve()

    def _build_navigation_report(self) -> str:
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
                    {"label": "확인", "text": "탐색 칩 대비와 스크롤을 확인합니다."}
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
        renderer = module.FigureRenderer(base=FIXTURE, daphnis=None, static=False)
        tokens_css = (self.daphnis / "src" / "tokens.css").read_text(encoding="utf-8")
        return module.build(report, renderer, tokens_css)

    def _playwright_root(self) -> Path | None:
        candidates = (*PLAYWRIGHT_ROOTS, self.daphnis / "node_modules")
        for root in candidates:
            if (root / "playwright-core" / "package.json").is_file():
                return root
        return None

    def test_dap_figures_use_inline_svg_documents_not_images(self) -> None:
        output = FIXTURE / "index.html"
        command = [
            sys.executable,
            str(BUILD),
            str(FIXTURE / "input.json"),
            str(output),
            "--daphnis",
            str(self.daphnis),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)

        parser = ReportParser()
        report = output.read_text(encoding="utf-8")
        parser.feed(report)

        self.assertEqual(parser.images, [])
        self.assertEqual(len(parser.frames), 2)
        self.assertIn("daphnis-theme", report)
        self.assertIn('data-mode="system"', report)
        self.assertIn('data-mode="light"', report)
        self.assertIn('data-mode="dark"', report)
        for frame in parser.frames:
            self.assertIn("data-daphnis", frame)
            document = frame.get("srcdoc")
            self.assertIsNotNone(document)
            self.assertIn("<svg", document)
            self.assertIn("fl-figure", document)

    def test_navigation_chips_use_state_tokens_and_single_row_css(self) -> None:
        report = self._build_navigation_report()

        self.assertIn("--report-chip-active-fill:var(--color-state-active-fill", report)
        self.assertIn("--report-chip-active-ink:var(--color-state-on-active", report)
        self.assertIn("flex-wrap:nowrap", report)
        self.assertIn("overflow-x:auto", report)
        self.assertIn("activeLink.scrollIntoView", report)

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
    parser.add_argument("--daphnis", type=Path, required=True)
    arguments, unittest_args = parser.parse_known_args()
    InlineDaphnisReportTest.daphnis = arguments.daphnis.resolve()
    unittest.main(argv=[sys.argv[0], *unittest_args])


if __name__ == "__main__":
    main()
