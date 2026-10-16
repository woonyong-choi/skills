"""#90 상태표: 보류인데 재개 조건이 없거나 보류 30일 이상이면 check가 알리고 상태는 바꾸지 않는다."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import project_status  # noqa: E402


class ProjectAttentionTest(unittest.TestCase):
    def gh(self, items: list[dict], issues: list[dict]) -> object:
        page = {"hasNextPage": False, "endCursor": None}
        options = [{"id": name, "name": name, "color": "GRAY", "description": ""} for name in ("대기", "진행", "검토", "보류", "완료")]

        def fake(args: list[str], payload: str | None) -> dict:
            query = json.loads(payload or "{}").get("query", "")
            if "mutation" in query:
                raise AssertionError("check must not change status")
            if "projectsV2" in query:
                return {"data": {"repository": {"projectsV2": {"nodes": [{"id": "P", "number": 1, "title": "판"}], "pageInfo": page}}}}
            if "fields(" in query:
                return {"data": {"node": {"fields": {"nodes": [{"id": "S", "name": "Status", "options": options}], "pageInfo": page}}}}
            if "issues(" in query:
                self.assertNotIn("comments", query)
                return {"data": {"repository": {"issues": {"nodes": issues, "pageInfo": page}}}}
            if "items(" in query:
                return {"data": {"node": {"items": {"nodes": items, "pageInfo": page}}}}
            raise AssertionError(query)

        return fake

    def item(self, number: int, status: str, *, days: int = 1, hold: str | None = None) -> dict:
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - days * 86400))
        return {
            "id": f"I{number}",
            "content": {"id": f"C{number}", "number": number, "state": "OPEN", "repository": {"nameWithOwner": "o/r"}},
            "fieldValueByName": {"name": status, "updatedAt": stamp},
            "hold": {"text": hold} if hold is not None else None,
        }

    def test_check_reports_missing_resume_and_long_hold(self) -> None:
        issues = [{"id": f"C{number}", "number": number, "state": "OPEN"} for number in (1, 2, 3)]
        items = [
            self.item(1, "진행"),
            self.item(2, "보류", hold="결정 대기"),
            self.item(3, "보류", days=31, hold="결정 대기; 재개 조건: 사용자 선택"),
        ]
        with mock.patch("builtins.print") as printed:
            code = project_status.main(["--repo", "o/r", "check", "--fix"], gh=self.gh(items, issues))
        lines = [call.args[0] for call in printed.call_args_list]
        self.assertEqual(code, 1, lines)
        self.assertFalse(any("#1" in line for line in lines), lines)
        self.assertTrue(any("#2" in line and "재개 조건 없음" in line for line in lines), lines)
        self.assertTrue(any("#3" in line and "보류 30일" in line for line in lines), lines)


if __name__ == "__main__":
    unittest.main()
