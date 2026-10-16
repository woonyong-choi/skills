"""PR 머지 뒤 훅 하나: career-record → repo-docs-journal 순서 안내.

합성 Vault·합성 설정 폴더만 사용
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "scripts"))

import continuity_hook  # noqa: E402


class MergeHookTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.vault = self.root / "vault"
        (self.vault / "career").mkdir(parents=True)
        self.config = self.root / "config"
        self.config.mkdir()
        patcher = mock.patch.dict(os.environ, {"WOON_KNOWLEDGE_ROOT": str(self.vault), "WORK_CONTINUITY_CONFIG_DIR": str(self.config)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def payload(self, command: str, response: object = None) -> dict:
        return {
            "hook_event_name": "PostToolUse",
            "session_id": "s",
            "cwd": str(self.root),
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "tool_response": {"stdout": "✓ Squashed and merged", "stderr": "", "interrupted": False} if response is None else response,
        }

    def test_successful_merge_adds_one_notice_in_order(self) -> None:
        for command in ("gh pr merge 12 --squash", "gh api -X PUT repos/me/x/pulls/12/merge --input body.json"):
            notice = continuity_hook.merge_notice(self.payload(command))
            self.assertIn("record.py", notice, command)
            self.assertIn("journal.py", notice, command)
            self.assertLess(notice.index("1. career-record(모드 normal)"), notice.index("2. repo-docs-journal(모드 normal)"))
        (self.config / "career-record.json").write_text(json.dumps({"mode": "bypass"}), encoding="utf-8")
        (self.config / "journal.json").write_text(json.dumps({"mode": "bypass"}), encoding="utf-8")
        notice = continuity_hook.merge_notice(self.payload("gh pr merge 12"))
        self.assertIn("career-record(모드 bypass)", notice)
        self.assertIn("repo-docs-journal(모드 bypass)", notice)

    def test_journal_only_without_career_folder(self) -> None:
        shutil.rmtree(self.vault / "career")
        notice = continuity_hook.merge_notice(self.payload("gh pr merge 12"))
        self.assertNotIn("career-record", notice)
        self.assertIn("1. repo-docs-journal", notice)

    def test_hook_json_has_one_post_tool_use_entry(self) -> None:
        for host in ("claude", "codex"):
            hooks = json.loads((PLUGIN / "hooks" / f"{host}.json").read_text(encoding="utf-8"))["hooks"]["PostToolUse"]
            self.assertEqual(sum(len(group["hooks"]) for group in hooks), 1, host)

    def test_handle_returns_notice_without_task(self) -> None:
        result = continuity_hook.handle("claude", self.payload("gh pr merge 12 --squash"), self.root / "state")
        self.assertIn("1. career-record", result["hookSpecificOutput"]["additionalContext"])

    def test_no_notice_for_failed_or_other_commands(self) -> None:
        cases = [
            self.payload("gh pr merge 12", {"stdout": "", "stderr": "not mergeable", "exit_code": 1}),
            self.payload("gh pr merge 12", "Exit code: 1\nPull request is not mergeable"),
            self.payload("gh pr view 12"),
            self.payload("gh api repos/me/x/pulls/12/merge"),
            {**self.payload("gh pr merge 12"), "hook_event_name": "PreToolUse"},
        ]
        for payload in cases:
            self.assertEqual(continuity_hook.merge_notice(payload), "", payload)

    def test_no_notice_without_vault(self) -> None:
        with mock.patch.dict(os.environ, {"WOON_KNOWLEDGE_ROOT": ""}):
            self.assertEqual(continuity_hook.merge_notice(self.payload("gh pr merge 12")), "")


if __name__ == "__main__":
    unittest.main()
