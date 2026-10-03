"""repo-docs 문체·저장 전 검사의 탐지와 원문 보존 경계 검증."""

import contextlib
import io
import unittest
from unittest.mock import mock_open, patch

import check_doc


class DocumentStyleTest(unittest.TestCase):
    # cost: time O(Σw²), heap O(c), stack O(1), io 0
    # vars: c = 표본 글자 수, w = 표본의 줄별 글자 수
    # basis: estimate, 파일 대신 메모리 표본으로 공개 CLI 진입점 실행
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
            ("**가나** **다라** **마바** 사아자차카타파하가나다라마바\n", {"굵게", "굵게 남용 비율"}),
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


if __name__ == "__main__":
    unittest.main()
