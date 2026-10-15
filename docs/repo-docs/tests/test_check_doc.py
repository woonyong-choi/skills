"""repo-docs 문체·저장 전 검사의 탐지와 원문 보존 경계 검증."""

import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_doc  # noqa: E402


class DocumentStyleTest(unittest.TestCase):
    # cost: time O(Σw²), heap O(c), stack O(1)
    # vars: c = 표본 글자 수, w = 표본의 줄별 글자 수
    # basis: estimate
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
            ("README.ko.md", "설계 단계입니다.\n", 0),
            ("guide.md", "설계 단계입니다.\n", 1),
            ("README.md", "설계 단계다.\n", 1),
            ("/vault/worktree/p/docs/design/a.md", "# 가\n\n## 예시\n\n## 요약\n", 1),
        ):
            with patch("builtins.open", mock_open(read_data=source)), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(check_doc.main([name]), expected)


    # cost: time O(Σw), heap O(c), stack O(1)
    # vars: c = 표본 글자 수, w = 표본의 줄별 글자 수
    # basis: estimate
    # 목록 항목 문장의 종결 검사 누락 회귀
    def test_list_item_sentences_use_paragraph_endings(self) -> None:
        cases = [
            ("guide.md", "1. 엔진이 입력을 저장해요.\n", ["문체"]),
            ("guide.md", "- 입력을 저장함.\n", ["문체"]),
            ("guide.md", "2. 엔진이 입력을 저장합니다.\n", ["문체(평서)"]),
            ("README.ko.md", "1. 엔진이 입력을 저장한다.\n", ["문체(합쇼)"]),
            ("guide.md", "1. 엔진이 입력을 저장한다.\n", []),
            ("README.ko.md", "1. 다음 명령으로 설치하세요.\n", []),
            ("guide.md", "- 입력 기록 보존\n", []),
            ("guide.md", "- 기본값: 없음\n", []),
            # #64: 끝 괄호 보충 앞 종결
            ("guide.md", "엔진이 입력을 저장합니다(기본값).\n", ["문체(평서)"]),
            ("guide.md", "- 엔진이 입력을 저장합니다 (기본값).\n", ["문체(평서)"]),
            ("guide.md", "- 입력을 저장함(기본값).\n", ["문체"]),
            ("README.ko.md", "엔진이 입력을 저장한다(기본값).\n", ["문체(합쇼)"]),
            ("guide.md", "엔진이 입력을 저장한다(기본값).\n", []),
        ]
        for name, source, expected in cases:
            with self.subTest(name=name, source=source):
                output = io.StringIO()
                with patch("builtins.open", mock_open(read_data=source)), contextlib.redirect_stdout(output):
                    check_doc.main([name])
                messages = [line.split(": ", 1)[1] for line in output.getvalue().splitlines()]
                self.assertEqual([message for message in messages if message.startswith("문체")], expected)


if __name__ == "__main__":
    unittest.main()
