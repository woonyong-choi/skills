"""gen_llms의 README 소개 추출·실패 종료·기본 브랜치 안내 검증."""

from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import gen_llms  # noqa: E402

RAW = "https://example.com/raw/"


class GenerateIndexTest(unittest.TestCase):
    # cost: time O(1), heap O(1), stack O(1), io O(1)
    # vars: 없음
    # basis: estimate
    # 임시 Git 저장소에 최소 문서 목록 생성
    def setUp(self) -> None:
        self.previous = os.getcwd()
        self.directory = tempfile.TemporaryDirectory()
        os.chdir(self.directory.name)
        subprocess.run(["git", "init", "-q"], check=True)
        Path("docs").mkdir()
        Path("docs/README.md").write_text("| [Architecture](architecture.md) | Code map |\n", encoding="utf-8")
        Path("docs/architecture.md").write_text("# Architecture\n", encoding="utf-8")

    # cost: time O(1), heap O(1), stack O(1), io O(1)
    # vars: 없음
    # basis: estimate
    def tearDown(self) -> None:
        os.chdir(self.previous)
        self.directory.cleanup()

    # cost: time O(c), heap O(c), stack O(1), io O(1)
    # vars: c = README 글자 수
    # basis: estimate
    def run_main(self, readme: str) -> tuple[int | str | None, str]:
        Path("README.md").write_text(readme, encoding="utf-8")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            try:
                code = gen_llms.main(False, raw_url=RAW)
            except SystemExit as error:
                code = error.code
        return code, stderr.getvalue()

    # cost: time O(c), heap O(c), stack O(1), io O(1)
    # vars: c = README 글자 수
    # basis: estimate
    def test_new_template_uses_why_section_as_intro(self) -> None:
        # #90 지시 5: 새 README 틀은 머리 뒤 소개 문단 없이 데모·알림·절. 소개는 해결하는 문제 절 첫 문단
        readme = (
            '<h1 align="center">Tool</h1>\n\n<p align="center">\n  Fast index tool<br>\n'
            '  <a href="#quick-start">Quick start</a> · <a href="#why">Why</a>\n</p>\n\n'
            "![Search finishes in one step](docs/assets/demo.gif)\n\n> [!NOTE]\n> In development.\n\n"
            "## Quick start\n\nRun it.\n\n## Why\n\nIndexing big folders is slow. Tool keeps an index.\n"
        )
        code, error = self.run_main(readme)
        self.assertIn(code, (0, None), error)
        index = Path("llms.txt").read_text(encoding="utf-8")
        self.assertIn("> Fast index tool", index)
        self.assertIn("Indexing big folders is slow. Tool keeps an index.", index)
        self.assertNotIn("\n!\n", index)

    def test_single_link_navigation_is_not_intro(self) -> None:
        cases = [
            "[Status](#status)",
            '<p align="center"><a href="#status">Status</a></p>',
            "[![CI](https://example.com/b.svg)](https://example.com/ci)",
        ]
        for navigation in cases:
            with self.subTest(navigation=navigation):
                code, _ = self.run_main(f"# Tool\n\n{navigation}\n\nShort tagline.\n\nIntro paragraph.\n")
                self.assertEqual(code, 0)
                text = Path("llms.txt").read_text(encoding="utf-8")
                self.assertIn("> Short tagline.\n\nIntro paragraph.\n", text)
                self.assertNotIn("Status", text)

    # cost: time O(c), heap O(c), stack O(1), io O(1)
    # vars: c = README 글자 수
    # basis: estimate
    def test_missing_intro_exits_with_reason(self) -> None:
        for readme in ["# Tool\n\nOnly tagline.\n", "# Tool\n\n[Status](#status)\n\nOnly tagline.\n", "No title.\n\nIntro.\n"]:
            with self.subTest(readme=readme):
                Path("llms.txt").unlink(missing_ok=True)
                code, _ = self.run_main(readme)
                self.assertNotIn(code, (0, None))
                self.assertIn("intro paragraph", str(code))
                self.assertFalse(Path("llms.txt").exists())

    # cost: time O(c), heap O(c), stack O(1), io O(1)
    # vars: c = README 글자 수
    # basis: estimate
    # 소개 문단 대신 알림 인용·하위 제목이 들어가는 회귀
    def test_quote_or_section_is_not_intro(self) -> None:
        cases = [
            "# Tool\n\nShort tagline.\n\n> [!NOTE]\n> Beta only.\n",
            "# Tool\n\nShort tagline.\n\n## How it works\n\nEngine stores input.\n",
            "# Tool\n\nShort tagline.\n\n### Notes\n",
        ]
        for readme in cases:
            with self.subTest(readme=readme):
                Path("llms.txt").unlink(missing_ok=True)
                code, _ = self.run_main(readme)
                self.assertNotIn(code, (0, None))
                self.assertIn("intro paragraph", str(code))
                self.assertFalse(Path("llms.txt").exists())

    # cost: time O(c), heap O(c), stack O(1), io O(1)
    # vars: c = README 글자 수
    # basis: estimate
    # 가운뎃점이 든 한 줄 소개 보존, 가운뎃점 이동 줄 제외
    def test_middle_dot_tagline_is_kept(self) -> None:
        navigation = [
            "[Install](#install) · [Usage](#usage)",
            '<p align="center"><a href="#install">Install</a> · <a href="#usage">Usage</a></p>',
        ]
        for line in navigation:
            with self.subTest(navigation=line):
                code, _ = self.run_main(f"# Tool\n\n{line}\n\nLine counter · CLI\n\nIntro paragraph.\n\n## Usage\n\nRun it.\n")
                self.assertEqual(code, 0)
                text = Path("llms.txt").read_text(encoding="utf-8")
                self.assertIn("> Line counter · CLI\n\nIntro paragraph.\n", text)
                self.assertNotIn("Install", text)

    # cost: time O(c), heap O(c), stack O(1), io O(1)
    # vars: c = README 글자 수
    # basis: estimate
    # #64: 제목과 같은 블록의 소개, 일반 인용 소개, 코드 블록, 제목 안 태그 처리
    def test_title_block_quote_fence_and_tagged_title(self) -> None:
        cases = [
            ("# Widget\nShort tagline.\n\nIntro paragraph.\n", "Widget"),
            ("<h1>Widget</h1>\n<p>Short tagline.</p>\n\nIntro paragraph.\n", "Widget"),
            ("# Widget\n\n> Short tagline.\n\nIntro paragraph.\n", "Widget"),
            ("# Widget\n\nShort tagline.\n\n```sh\nwidget run\n```\n\nIntro paragraph.\n\n## Usage\n", "Widget"),
            ('<h1><img src="logo.svg" alt=""><br>Widget</h1>\n\nShort tagline.\n\nIntro paragraph.\n', "Widget"),
        ]
        for readme, name in cases:
            with self.subTest(readme=readme):
                code, _ = self.run_main(readme)
                self.assertEqual(code, 0)
                text = Path("llms.txt").read_text(encoding="utf-8")
                self.assertTrue(text.startswith(f"# {name}\n\n> Short tagline.\n\nIntro paragraph.\n"), text)
                self.assertNotIn("widget run", text)

    # cost: time O(1), heap O(1), stack O(1), io O(1)
    # vars: 없음
    # basis: estimate
    def test_remote_head_failure_names_branch_option(self) -> None:
        responses = [
            subprocess.CompletedProcess([], 0, "https://github.com/owner/repo.git\n", ""),
            subprocess.CompletedProcess([], 128, "", "fatal: could not read from remote"),
        ]
        with patch.object(gen_llms.subprocess, "run", side_effect=responses):
            with self.assertRaises(SystemExit) as raised:
                gen_llms.raw_base_url()
        self.assertIn("use --branch", str(raised.exception.code))


class DocumentListTest(unittest.TestCase):
    """#90 지시 5: docs/README.md 분류별 목록(들여쓰기 3단계)의 문서 줄을 순서대로 읽는다."""

    def test_list_rows_in_order_without_category_lines(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            previous = os.getcwd()
            os.chdir(folder)
            try:
                Path("docs").mkdir()
                Path("docs/README.md").write_text(
                    "# 문서\n\n소개.\n\n- 시작\n  - [아키텍처](architecture.md): 구성 요소\n"
                    "- 설계\n  - [입력](design/input.md): 입력 접수\n    - [재시도](design/input-retry.md): 재시도 순서\n"
                    "- 기록\n  - [결정 기록](decisions/README.md): 고른 이유\n",
                    encoding="utf-8",
                )
                rows = gen_llms.read_rows()
            finally:
                os.chdir(previous)
        self.assertEqual(
            rows,
            [
                ("아키텍처", "architecture.md", "구성 요소"),
                ("입력", "design/input.md", "입력 접수"),
                ("재시도", "design/input-retry.md", "재시도 순서"),
                ("결정 기록", "decisions/README.md", "고른 이유"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
