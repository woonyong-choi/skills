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


if __name__ == "__main__":
    unittest.main()
