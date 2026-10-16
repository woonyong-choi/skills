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
        Path("docs/README.md").write_text("# Docs\n\n## Start\n\n- [Architecture](architecture.md): Code map\n", encoding="utf-8")
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
    """docs/README.md 분류별 목록(## 분류, 문서 줄, 들여 쓴 하위 문서)과 README.en.md 머리 검증."""

    LIST = (
        "# 문서\n\n설계 문서다.\n\n## 시작\n\n- [아키텍처](architecture.md): 구성 요소\n\n"
        "## 설계\n\n- [입력](design/input.md): 입력 접수\n  - [재시도](design/input-retry.md): 재시도 순서\n"
        "- [출력](design/output.md): 결과 형식\n\n## 기록\n\n- [결정 기록](decisions/README.md): 고른 이유\n"
    )
    KOREAN = "# 도구\n\n빠른 색인 도구\n\n한국어 소개 문단.\n"

    # cost: time O(1), heap O(1), stack O(1), io O(1)
    # vars: 없음
    # basis: estimate
    def setUp(self) -> None:
        self.previous = os.getcwd()
        self.directory = tempfile.TemporaryDirectory()
        os.chdir(self.directory.name)
        subprocess.run(["git", "init", "-q"], check=True)
        for path in ("architecture.md", "design/input.md", "design/input-retry.md", "design/output.md", "decisions/README.md"):
            Path("docs", path).parent.mkdir(parents=True, exist_ok=True)
            Path("docs", path).write_text("# 문서\n", encoding="utf-8")

    # cost: time O(1), heap O(1), stack O(1), io O(1)
    # vars: 없음
    # basis: estimate
    def tearDown(self) -> None:
        os.chdir(self.previous)
        self.directory.cleanup()

    # cost: time O(c), heap O(c), stack O(1), io O(1)
    # vars: c = 입력 글자 수
    # basis: estimate
    def run_main(self, index: str, readme: str | None = None, english: str | None = None) -> int | str | None:
        Path("docs/README.md").write_text(index, encoding="utf-8")
        Path("README.md").write_text(readme or self.KOREAN, encoding="utf-8")
        if english is not None:
            Path("README.en.md").write_text(english, encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()):
            try:
                return gen_llms.main(False, raw_url=RAW)
            except SystemExit as error:
                return error.code

    def test_list_links_in_order_split_into_docs_and_optional(self) -> None:
        self.assertEqual(self.run_main(self.LIST), 0)
        text = Path("llms.txt").read_text(encoding="utf-8")
        docs, optional = text.split("## Optional\n")
        self.assertIn(
            f"- [아키텍처]({RAW}docs/architecture.md): 구성 요소\n"
            f"- [입력]({RAW}docs/design/input.md): 입력 접수\n"
            f"- [재시도]({RAW}docs/design/input-retry.md): 재시도 순서\n"
            f"- [출력]({RAW}docs/design/output.md): 결과 형식\n",
            docs,
        )
        self.assertIn(f"- [결정 기록]({RAW}docs/decisions/README.md): 고른 이유", optional)
        self.assertNotIn("시작", text)
        self.assertNotIn("  - [", text)

    def test_header_from_english_readme_when_present(self) -> None:
        english = (
            "# Tool\n\n[한국어](README.md) | English\n\nFast index tool\n\nEnglish intro paragraph.\n"
        )
        readme = '# 도구\n\n한국어 | <a href="README.en.md">English</a>\n\n빠른 색인 도구\n\n한국어 소개 문단.\n'
        self.assertEqual(self.run_main(self.LIST, readme, english), 0)
        text = Path("llms.txt").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# Tool\n\n> Fast index tool\n\nEnglish intro paragraph.\n"), text)
        self.assertNotIn("한국어 소개", text)

    def test_header_from_readme_without_english(self) -> None:
        readme = '# 도구\n\n한국어 | <a href="README.en.md">English</a>\n\n빠른 색인 도구\n\n한국어 소개 문단.\n'
        self.assertEqual(self.run_main(self.LIST, readme), 0)
        self.assertTrue(Path("llms.txt").read_text(encoding="utf-8").startswith("# 도구\n\n> 빠른 색인 도구\n\n한국어 소개 문단.\n"))

    def test_table_only_index_fails_without_writing(self) -> None:
        code = self.run_main("# 문서\n\n| 문서 | 설명 |\n|---|---|\n| [아키텍처](architecture.md) | 구성 요소 |\n")
        self.assertIn("docs/README.md가 목록 형식이 아님", str(code))
        self.assertFalse(Path("llms.txt").exists())

    def test_malformed_list_line_names_line_number(self) -> None:
        for line in ("- 아키텍처: 구성 요소", "- [아키텍처](architecture.md)", "- [아키텍처](architecture.md):"):
            with self.subTest(line=line):
                code = self.run_main("# 문서\n\n## 시작\n\n" + line + "\n")
                self.assertIn("docs/README.md 5번째 줄", str(code))
                self.assertFalse(Path("llms.txt").exists())

    def test_list_lines_in_code_block_are_ignored(self) -> None:
        index = self.LIST + "\n```md\n- [예시](missing.md): 틀 예시\n- 형식 아님\n```\n"
        self.assertEqual(self.run_main(index), 0)
        self.assertNotIn("예시", Path("llms.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
