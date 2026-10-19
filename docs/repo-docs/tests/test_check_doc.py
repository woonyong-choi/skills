"""repo-docs 문체·저장 전 검사의 탐지와 원문 보존 경계 검증."""

import contextlib
import io
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_doc  # noqa: E402


class DocumentStyleTest(unittest.TestCase):
    def test_main_diagramplay_marker_preserves_html_and_sentence_checks(self) -> None:
        cases = [
            ("guide.md", "![요청](usage-request.svg)<!-- torso -->\n", ["HTML"]),
            ("guide.md", "![요청을 저장하는 경로](usage-request.svg)<!-- diagramplay -->\n", []),
            ("README.md", "![요청](usage-request.svg)<!-- diagramplay -->\n", []),
            ("guide.md", "> ![요청](usage-request.svg)<!-- diagramplay -->\n", ["인용 블록"]),
            ("guide.md", "![요청](usage-request.svg)<!-- DiagramPlay -->\n", ["HTML"]),
            ("guide.md", "![요청](usage-request.svg)<!--diagramplay-->\n", ["HTML"]),
            ("guide.md", "![요청](usage-request.svg)<!-- diagramplay extra -->\n", ["HTML"]),
            ("guide.md", "![요청](usage-request.svg)<!-- diagramplay md v2 x -->\n", ["HTML"]),
            ("guide.md", "<!-- 설명 -->\n", ["HTML"]),
            ("guide.md", "<div>그림</div><!-- diagramplay -->\n", ["HTML"]),
            ("guide.md", "![요청](usage-request.svg)<!-- diagramplay --><!-- 설명 -->\n", ["HTML"]),
            ("guide.md", "```text\n<!-- diagramplay -->\n<!-- 설명 -->\n<div>그림</div>\n```\n", []),
            ("guide.md", "입력을 저장해요.<!-- diagramplay -->\n", ["문체"]),
            ("guide.md", "입력을 저장합니다.<!-- diagramplay -->\n", ["문체(평서)"]),
            ("README.md", "입력을 저장한다.<!-- diagramplay -->\n", ["문체(합쇼)"]),
            ("guide.md", "입력을 저장한다.<!-- diagramplay -->\n", []),
        ]
        for name, source, expected in cases:
            with self.subTest(name=name, source=source):
                output = io.StringIO()
                with patch("builtins.open", mock_open(read_data=source)), contextlib.redirect_stdout(output):
                    code = check_doc.main([name])
                messages = [line.split(": ", 1)[1] for line in output.getvalue().splitlines()]
                self.assertEqual(messages, expected)
                self.assertEqual(code, 1 if expected else 0)

    def test_generated_boundaries_and_noun_cells(self) -> None:
        accepted = [
            "<!-- diagramplay scenes v1 name=state -->",
            "<!-- /diagramplay scenes v1 name=state -->",
            "  <!-- diagramplay fold v1 n=12 -->",
            "  <!-- /diagramplay fold v1 n=12 -->",
            "<!-- diagramplay scenes v1 name=flow-2 -->",
            *[f"<!-- {table}-table:{edge} -->" for table in ("check", "grammar") for edge in ("start", "end")],
            "| 값 묶음 | 차트 행의 숫자 자리에 값 이름을 써서, 그 값이 바뀔 때 차트가 바뀌게 하는 연결이다. | `value`, `timeline.charts` |",
        ]
        rejected = [
            "<!-- torso scenes v1 name=state -->",
            "<!-- /torso fold v1 n=12 -->",
            "<!-- diagramplay scenes v2 name=state -->",
            "<!-- diagramplay fold v1 name=State -->",
            "<!-- diagramplay scenes v1 name=-state -->",
            "<!-- diagramplay fold v1 n=0 -->",
            "<!-- diagramplay fold v1 n=state -->",
            "<!-- diagramplay scenes v1 name=state extra -->",
            "<!--diagramplay scenes v1 name=state-->",
            "<!-- check-table:other -->",
            "<!-- diagramplay fold v1 name=`ignored`state -->",
            "> <!-- check-table:start -->",
            "<!-- grammar-table:start extra -->",
            "글<!-- check-table:start -->",
            "<!-- diagramplay fold v1 name=state --><div>글</div>",
            "<!-- 설명 -->",
            "| 동작 | 저장함 |",
            "| 동작 | 기록했음 |",
        ]
        for source in accepted + rejected:
            with self.subTest(source=source):
                output = io.StringIO()
                with patch("builtins.open", mock_open(read_data=source + "\n")), contextlib.redirect_stdout(output):
                    result = check_doc.main(["guide.md"])
                self.assertEqual(result, int(source in rejected), output.getvalue())

    # 파일 대신 메모리 표본으로 공개 CLI 진입점 실행
    def test_main_style_signals_and_preserved_sources(self) -> None:
        cases = [
            ("입력을 저장한다 — 재시작하면 복구한다.\n", {"줄표 문장 연결"}),
            ("| 값 | — |\n", set()),
            ("범위는 1–4ms다. A → B 순서다.\n", set()),
            ("상태 \U0001F916\n", {"이모지"}),
            ("상태 \u2705\n", {"이모지"}),
            ("상태 \u2764\uFE0F\n", {"이모지"}),
            ("상태 1\uFE0F\u20E3\n", {"이모지"}),
            ("국가 \U0001F1F0\U0001F1F7\n", {"이모지"}),
            ("다음과 같습니다.\n", {"안내 말"}),
            ("동작을 살펴보겠습니다.\n", {"안내 말"}),
            ("Let's start.\n", {"안내 말"}),
            ("LET’S start.\n", {"안내 말"}),
            ("In summary, data persists.\n", {"안내 말"}),
            ("It's worth noting that data persists.\n", {"안내 말"}),
            ("It’s worth noting that data persists.\n", {"안내 말"}),
            ("Stored in summary.json.\n", set()),
            ("Stored in summary tables.\n", set()),
            ("**In summary**, data persists.\n", {"안내 말", "굵게"}),
            ("**확인**한 결과다.\n", {"굵게"}),
            ("__강조__\n", {"굵게"}),
            ("mcp__server__tool\n", set()),
            (r"\*\*문자\*\*" + "\n", set()),
            ("`— 다음과 같습니다 **강조** \U0001F916`\n", set()),
            ("`` `예` — 다음과 같습니다 **강조** \U0001F916 ``\n", set()),
            ("```text\nA — B **강조** \U0001F916\n```\n", set()),
            ("~~~text\nA — B **강조** \U0001F916\n~~~\n", set()),
            ("````text\n```\nA — B \U0001F916\n````\n", set()),
            ("> A — B **강조** \U0001F916\n", set()),
            ("> [!NOTE]\n> A — B\n", {"줄표 문장 연결"}),
            ("> [!NOTE]\n\n> A — B\n", set()),
            ('[문서](https://example.org/—/\U0001F916 "In summary")\n', set()),
            ("[문서][In summary]\n", set()),
            ("[In summary]: https://example.org/\U0001F916\n", set()),
            ('<img alt="In summary \U0001F916">\n', set()),
            ("<!-- A — B\nIn summary \U0001F916 -->\n", set()),
            ("<!-- 설명 -->A — B\n", {"줄표 문장 연결"}),
            ("```text\n<!--\n```\nA — B\n", {"줄표 문장 연결"}),
            ("<!--\n```text\n-->\nA — B\n", {"줄표 문장 연결"}),
            ("[다음과 같습니다](guide.md)\n", {"안내 말"}),
            ("**가나** **다라** **마바** 사아자차카타파하가나다라마바\n", {"굵게"}),
            ("**가나** **다라** **마바** 사아자차카타파하가나다라마바사아자차카타파하가나다라\n", {"굵게"}),
            ("**가나** **다라**\n", {"굵게"}),
            ("**검증.** 결과를 직접 확인한다.\n", set()),
            ("- **검증.** 결과를 직접 확인한다.\n", set()),
            ("1. **검증.** 결과를 직접 확인한다.\n", set()),
            ("**검증:** 결과를 직접 확인한다.\n", {"굵게"}),
            ("**검증.** 결과를 **직접** 확인한다.\n", {"굵게"}),
            ("결과를 **검증.** 확인한다.\n", {"굵게"}),
        ]
        signals = ("줄표 문장 연결", "이모지", "안내 말", "굵게")
        for source, expected in cases:
            with self.subTest(source=source):
                output = io.StringIO()
                with patch("builtins.open", mock_open(read_data=source)), contextlib.redirect_stdout(output):
                    code = check_doc.main(["guide.md"])
                messages = [line.split(": ", 1)[1] for line in output.getvalue().splitlines()]
                found = {"굵게 남용 비율" if message.startswith("굵게 남용 비율") else message for message in messages if message.startswith(signals)}
                self.assertEqual(found, expected)
                self.assertEqual(code, 1 if messages else 0)
        for name, source, expected in (
            ("README.md", "설계 단계입니다.\n", 0),
            ("README.md", "설계 단계입니다.\n", 0),
            ("guide.md", "설계 단계입니다.\n", 1),
            ("README.md", "설계 단계다.\n", 1),
            ("/work/p/docs/design/a.md", "# 가\n\n## 사용 예\n\n## 요약\n", 1),
        ):
            with patch("builtins.open", mock_open(read_data=source)), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(check_doc.main([name]), expected)


    # 비공개 폴더는 repo-docs 비공개 작업 파일 절의 `.local/` 하나
    def test_private_links_follow_local_folder_rule(self) -> None:
        for source, expected in (
            ("[기록](.local/decisions/a.tsv)\n", True),
            ("[기록](%2Elocal/a.md)\n", True),
            ("[보관](archive/a.md)\n", False),
        ):
            with self.subTest(source=source):
                output = io.StringIO()
                with patch("builtins.open", mock_open(read_data=source)), contextlib.redirect_stdout(output):
                    check_doc.main(["guide.md"])
                self.assertEqual("비공개 경로" in output.getvalue(), expected)

    # 목록 항목 문장의 종결 검사 누락 회귀
    def test_list_item_sentences_use_paragraph_endings(self) -> None:
        cases = [
            ("guide.md", "1. 엔진이 입력을 저장해요.\n", ["문체"]),
            ("guide.md", "- 입력을 저장함.\n", ["문체"]),
            ("guide.md", "2. 엔진이 입력을 저장합니다.\n", ["문체(평서)"]),
            ("README.md", "1. 엔진이 입력을 저장한다.\n", ["문체(합쇼)"]),
            ("guide.md", "1. 엔진이 입력을 저장한다.\n", []),
            ("README.md", "1. 다음 명령으로 설치하세요.\n", []),
            ("guide.md", "- 입력 기록 보존\n", []),
            ("guide.md", "- 기본값: 없음\n", []),
            # #64: 끝 괄호 보충 앞 종결
            ("guide.md", "엔진이 입력을 저장합니다(기본값).\n", ["문체(평서)"]),
            ("guide.md", "- 엔진이 입력을 저장합니다 (기본값).\n", ["문체(평서)"]),
            ("guide.md", "- 입력을 저장함(기본값).\n", ["문체"]),
            ("README.md", "엔진이 입력을 저장한다(기본값).\n", ["문체(합쇼)"]),
            ("guide.md", "엔진이 입력을 저장한다(기본값).\n", []),
        ]
        for name, source, expected in cases:
            with self.subTest(name=name, source=source):
                output = io.StringIO()
                with patch("builtins.open", mock_open(read_data=source)), contextlib.redirect_stdout(output):
                    check_doc.main([name])
                messages = [line.split(": ", 1)[1] for line in output.getvalue().splitlines()]
                self.assertEqual([message for message in messages if message.startswith("문체")], expected)


class CommandLineTest(unittest.TestCase):
    """#81: 인자 오류와 없는 파일은 traceback 없이 종료 2."""

    def run_cli(self, *args: str) -> "subprocess.CompletedProcess[str]":
        script = Path(__file__).resolve().parents[1] / "scripts" / "check_doc.py"
        return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, timeout=30)

    def test_help_prints_usage(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout)

    def test_bad_arguments_exit_two_without_traceback(self) -> None:
        for args in ((), ("--unknown", "a.md"), ("/nonexistent/a.md",)):
            result = self.run_cli(*args)
            self.assertEqual(result.returncode, 2, args)
            self.assertNotIn("Traceback", result.stderr, args)
            self.assertTrue(result.stderr.strip(), args)


class ReadmeOrderTest(unittest.TestCase):
    """#90 지시 5: README 절 순서는 repo-docs-readme 틀의 두 종류 순서."""

    def errors(self, text: str) -> list[str]:
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            previous = Path.cwd()
            os.chdir(folder)
            try:
                Path("README.md").write_text(text, encoding="utf-8")
                return check_doc.structure_errors("README.md", "README.md")
            finally:
                os.chdir(previous)

    def test_new_template_order(self) -> None:
        self.assertEqual(self.errors("# T\n\n## Quick start\n\n## Why\n\n## How it works\n\n## Status\n"), [])
        self.assertEqual(self.errors("# T\n\n## Why\n\n## Quick start\n"), ["절 순서"])
        self.assertEqual(self.errors("# T\n\n## Problem and constraints\n\n## Design decisions\n\n## Results\n"), [])
        self.assertEqual(self.errors("# T\n\n## Results\n\n## Implementation\n"), ["절 순서"])


class DocsOrderTest(unittest.TestCase):
    """#96: architecture·design·decision 절 순서는 일상어 절 이름 기준."""

    def errors(self, name: str, text: str) -> list[str]:
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            previous = Path.cwd()
            os.chdir(folder)
            try:
                target = Path(name)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
                return check_doc.structure_errors(name, name)
            finally:
                os.chdir(previous)

    def test_new_section_names_are_ordered(self) -> None:
        self.assertEqual(self.errors("docs/architecture.md", "# 아키텍처\n\n## 지켜야 할 규칙\n\n## 구성 요소\n"), ["절 순서"])
        self.assertEqual(self.errors("docs/design/input.md", "# 입력\n\n## 작동 방식\n\n## 사용 예\n"), ["절 순서"])
        self.assertEqual(self.errors("docs/decisions/2026-10-16-x.md", "# x\n\n## 다시 볼 조건\n\n## 영향\n"), ["절 순서"])


class EnglishReadmeTest(unittest.TestCase):
    """#96 언어 기조: README.md 한국어 정본(합쇼), README.en.md 영어판과 절 대응."""

    def run_in(self, files: dict[str, str], name: str) -> list[str]:
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            previous = Path.cwd()
            os.chdir(folder)
            try:
                for path, text in files.items():
                    Path(path).write_text(text, encoding="utf-8")
                return check_doc.structure_errors(name, name)
            finally:
                os.chdir(previous)

    def test_english_readme_must_match_korean_sections(self) -> None:
        korean = "# T\n\n## 빠른 시작\n\n## 작동 방식\n"
        self.assertEqual(self.run_in({"README.md": korean, "README.en.md": "# T\n\n## Quick start\n\n## How it works\n"}, "README.en.md"), [])
        self.assertEqual(self.run_in({"README.md": korean, "README.en.md": "# T\n\n## Quick start\n"}, "README.en.md"), ["README.md와 절 대응 불일치"])

    def test_korean_readme_is_formal(self) -> None:
        self.assertIn("README.md", check_doc.FORMAL_FILES)
        self.assertNotIn("README.en.md", check_doc.FORMAL_FILES)


if __name__ == "__main__":
    unittest.main()
