"""skills#43: session 명시 bind 우선 라우팅 회귀 검사.

과업 찾기 순서: 세션 명시 bind → ISSUE_CONTINUITY_TASK 힌트 → 같은 저장소 binding 1개.
"""

from __future__ import annotations

import json
import tempfile
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any
import unittest
from unittest import mock

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "scripts"))

import continuity as core  # noqa: E402
import continuity_hook as hook  # noqa: E402

RUNTIME = Path(tempfile.gettempdir()) / "skills-test-runtime" / "continuity-routing"
REPO = core.run(["git", "rev-parse", "--show-toplevel"], cwd=str(PLUGIN)).strip()
OTHER_REPO = "/nonexistent/other-repo"
NEW = "22222222-2222-4222-8222-222222222222"
CLEARED = "33333333-3333-4333-8333-333333333333"


def write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False))


class RoutingCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if RUNTIME.exists():
            raise AssertionError("do not overwrite another execution")
        RUNTIME.mkdir(parents=True)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(RUNTIME, ignore_errors=True)

    def setUp(self) -> None:
        self.root = RUNTIME / self.id().rsplit(".", 1)[-1]
        self.root.mkdir()
        self.environ = mock.patch.dict(os.environ, clear=False)
        self.environ.start()
        for key in [k for k in os.environ if k.startswith("ISSUE_CONTINUITY")]:
            del os.environ[key]
        self.addCleanup(self.environ.stop)

    def task(
        self, name: str, *, sessions: list[str], repo: str = REPO, issue: int = 1
    ) -> Path:
        folder = self.root / name
        write(
            folder / "binding.json",
            {
                "repo": repo,
                "remote": "woonyong-choi/skills",
                "issue": issue,
                "project": 16,
                "url": f"https://example.invalid/issues/{issue}",
                "status_map": ["진행=작업 중"],
                "session_ids": sessions,
            },
        )
        return folder

    def payload(self, session: str, event: str = "UserPromptSubmit") -> dict[str, Any]:
        return {"hook_event_name": event, "session_id": session, "cwd": str(PLUGIN)}


class FindTaskTest(RoutingCase):
    def test_find_task_explicit_session_bind_beats_env_hint(self) -> None:
        self.task("old", sessions=[], issue=1)
        new = self.task("new", sessions=[NEW], issue=2)
        os.environ["ISSUE_CONTINUITY_TASK"] = "old"

        self.assertEqual(hook.find_task(self.root, self.payload(NEW)), new)

    def test_find_task_duplicate_session_fails_closed(self) -> None:
        self.task("old", sessions=[NEW], issue=1)
        self.task("new", sessions=[NEW], issue=2)
        os.environ["ISSUE_CONTINUITY_TASK"] = "old"

        self.assertIsNone(hook.find_task(self.root, self.payload(NEW)))
        del os.environ["ISSUE_CONTINUITY_TASK"]
        self.assertIsNone(hook.find_task(self.root, self.payload(NEW)))
        text = hook.handle_continuity(
            "claude", self.payload(NEW, "SessionStart"), self.root
        )
        self.assertIn("여러 task", text["hookSpecificOutput"]["additionalContext"])

    def test_find_task_unregistered_session_uses_verified_fallback(self) -> None:
        old = self.task("old", sessions=[], issue=1)
        self.task("elsewhere", sessions=[], repo=OTHER_REPO, issue=3)
        payload = self.payload(CLEARED)

        self.assertEqual(hook.find_task(self.root, payload), old)
        os.environ["ISSUE_CONTINUITY_TASK"] = "elsewhere"
        self.assertIsNone(
            hook.find_task(self.root, payload), "hint with another repo is rejected"
        )
        os.environ["ISSUE_CONTINUITY_TASK"] = "old"
        self.assertEqual(hook.find_task(self.root, payload), old)
        del os.environ["ISSUE_CONTINUITY_TASK"]
        self.task("second", sessions=[], issue=4)
        self.assertIsNone(
            hook.find_task(self.root, payload), "two repo matches are ambiguous"
        )

    def test_session_start_with_repo_fallback_does_not_link(self) -> None:
        old = self.task("old", sessions=[], issue=1)

        hook.handle_continuity(
            "claude", self.payload(CLEARED, "SessionStart"), self.root
        )

        self.assertEqual(core.read(old / "binding.json")["session_ids"], [])


class HookProcessTest(RoutingCase):
    """공식 훅 입력(stdin JSON)을 정본 continuity_hook.py와 continuity_statusline.py에 그대로 전달한다."""

    def run_script(
        self, script: str, payload: dict[str, Any], *args: str, **env: str
    ) -> subprocess.CompletedProcess[str]:
        clean = {
            k: v for k, v in os.environ.items() if not k.startswith("ISSUE_CONTINUITY")
        }
        return subprocess.run(
            [sys.executable, str(PLUGIN / "scripts" / script), *args],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env={**clean, "ISSUE_CONTINUITY_ROOT": str(self.root), **env},
        )
    def hook(self, payload: dict[str, Any], **env: str) -> dict[str, Any]:
        done = self.run_script("continuity_hook.py", payload, "claude", **env)
        self.assertEqual((done.returncode, done.stderr), (0, ""))
        result: dict[str, Any] = json.loads(done.stdout)
        return result

    def test_user_prompt_submit_routes_to_session_bound_task_despite_launch_env(
        self,
    ) -> None:
        self.task("old", sessions=[], issue=1)
        self.task("new", sessions=[NEW], issue=2)

        out = self.hook(self.payload(NEW), ISSUE_CONTINUITY_TASK="old")

        self.assertIn(
            "https://example.invalid/issues/2",
            out["hookSpecificOutput"]["additionalContext"],
        )

    def test_statusline_writes_meter_to_session_bound_task(self) -> None:
        old = self.task("old", sessions=[], issue=1)
        new = self.task("new", sessions=[NEW], issue=2)
        command = self.root / "original-statusline.json"
        write(command, {})
        payload = {**self.payload(NEW), "context_window": {"used_percentage": 81}}

        done = self.run_script(
            "continuity_statusline.py", payload, "--command-file", str(command)
        )

        meter = core.read(new / "meter.json")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(
            (meter["session_id"], meter["percent"], meter["task"]), (NEW, 81, "new")
        )
        self.assertFalse((old / "meter.json").exists())
        usage = self.hook(self.payload(NEW, "PostToolUse"))
        self.assertIn("81%", usage["hookSpecificOutput"]["additionalContext"])


CODEX_SESSION = "00000000-0000-4000-8000-0000000000c1"  # 명백한 합성 값


def meta_line(session: str = CODEX_SESSION) -> bytes:
    record = {
        "timestamp": "2026-01-01T00:00:00.000Z",
        "type": "session_meta",
        "payload": {"id": session, "session_id": session, "cli_version": "0.158.0"},
    }
    return (json.dumps(record, separators=(",", ":")) + "\n").encode()


class CodexRolloutTest(RoutingCase):
    def test_codex_home_behind_link_is_accepted(self) -> None:
        # macOS /var·홈 링크처럼 sessions 위쪽 링크는 허용, sessions 안 링크만 거절
        codex_home = self.root / "codex"
        sessions = codex_home / "sessions" / "2026" / "10" / "15"
        sessions.mkdir(parents=True)
        real = sessions / f"rollout-2026-10-15T01-05-53-{CODEX_SESSION}.jsonl"
        real.write_bytes(meta_line())
        linked_home = self.root / "linked-codex-home"
        os.symlink(codex_home.resolve(), linked_home)
        os.environ["CODEX_HOME"] = str(linked_home)
        self.assertEqual(core.codex_rollout(CODEX_SESSION), str(real.resolve()))


if __name__ == "__main__":
    unittest.main()
