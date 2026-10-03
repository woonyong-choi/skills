"""Mutoscope 그림이 이미지가 아닌 인라인 문서로 들어가는지 검사한다."""

from __future__ import annotations

import argparse
import subprocess
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "inline-mutoscope"
BUILD = ROOT / "html-report" / "scripts" / "build_report.py"


class ReportParser(HTMLParser):
    """보고서의 이미지와 Mutoscope iframe 속성을 모은다."""

    def __init__(self) -> None:
        super().__init__()
        self.images: list[dict[str, str | None]] = []
        self.frames: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "img":
            self.images.append(dict(attrs))
        if tag == "iframe":
            self.frames.append(dict(attrs))


class InlineMutoscopeReportTest(unittest.TestCase):
    """두 Mutoscope 재생기가 독립 iframe 문서로 생성되는지 확인한다."""

    mutoscope: Path

    def test_muto_figures_use_inline_svg_documents_not_images(self) -> None:
        output = FIXTURE / "index.html"
        command = [
            sys.executable,
            str(BUILD),
            str(FIXTURE / "input.json"),
            str(output),
            "--mutoscope",
            str(self.mutoscope),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)

        parser = ReportParser()
        report = output.read_text(encoding="utf-8")
        parser.feed(report)

        self.assertEqual(parser.images, [])
        self.assertEqual(len(parser.frames), 2)
        self.assertIn("mutoscope-theme", report)
        self.assertIn('data-mode="system"', report)
        self.assertIn('data-mode="light"', report)
        self.assertIn('data-mode="dark"', report)
        for frame in parser.frames:
            self.assertEqual(frame.get("data-mutoscope"), None)
            document = frame.get("srcdoc")
            self.assertIsNotNone(document)
            self.assertIn("<svg", document)
            self.assertIn("fl-figure", document)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mutoscope", type=Path, required=True)
    arguments, unittest_args = parser.parse_known_args()
    InlineMutoscopeReportTest.mutoscope = arguments.mutoscope.resolve()
    unittest.main(argv=[sys.argv[0], *unittest_args])


if __name__ == "__main__":
    main()
