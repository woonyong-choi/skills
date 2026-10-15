"""skills#80: 훅 기록 위치·프롬프트 정리·시간 예산·가드 실패·호스트 어댑터 회귀 검사."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


PLUGIN = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN / "scripts"
sys.path.insert(0, str(SCRIPTS))

import continuity as core  # noqa: E402
import continuity_hook as hook  # noqa: E402
import continuity_window as window  # noqa: E402
import document_guard as guard  # noqa: E402
import hook_entry  # noqa: E402
import project_context as context  # noqa: E402

SESSION = "019e0000-0000-7000-8000-000000000001"
PATCH = "*** Begin Patch\n*** Add File: docs/x.md\n+# x\n*** End Patch\n"
SHELL_PATCH = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "apply_patch <<'EOF'\n" + PATCH + "EOF"}}
SLOW = subprocess.TimeoutExpired(["git"], 3)


class TemporaryCase(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp()).resolve()  # macOS /var 링크: 등록 경로는 실제 경로
        self.addCleanup(shutil.rmtree, self.base)
        environ = mock.patch.dict(os.environ, {"WORK_CONTINUITY_CONFIG_DIR": str(self.base / "configuration")})
        environ.start()
        self.addCleanup(environ.stop)
        for key in ("ISSUE_CONTINUITY_ROOT", "ISSUE_CONTINUITY_TASK", "ISSUE_CONTINUITY_WINDOW", "WORK_CONTINUITY_DEADLINE"):
            os.environ.pop(key, None)

    def denied(self, result: dict) -> bool:
        return result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


class RecordRootTest(TemporaryCase):
    """기록 루트는 ISSUE_CONTINUITY_ROOT 하나로 정하고 CLI·훅·창 실행기가 같은 값을 쓴다."""

    def test_cli_default_root_follows_environment(self) -> None:
        root = self.base / "records"
        repo = self.base / "repo"
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        core.save(root / "task/binding.json", {"repo": str(repo), "remote": "o/r", "issue": 1, "url": "u", "session_ids": []})
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "continuity.py"), "restore", "--task", "task", "--offline"],
            env={**os.environ, "ISSUE_CONTINUITY_ROOT": str(root)}, capture_output=True, text=True, timeout=30,
        )
        self.assertNotIn("bind an issue", result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_every_reader_uses_one_root_function(self) -> None:
        os.environ["ISSUE_CONTINUITY_ROOT"] = str(self.base / "elsewhere")
        self.assertEqual(core.default_root(), self.base / "elsewhere")
        self.assertEqual(window.root(), self.base / "elsewhere")
        del os.environ["ISSUE_CONTINUITY_ROOT"]
        self.assertEqual(core.default_root(), core.ROOT)
        for name in ("continuity_hook.py", "continuity_window.py", "continuity_statusline.py"):
            self.assertNotIn("ISSUE_CONTINUITY_ROOT", (SCRIPTS / name).read_text(), name)


class PendingPromptTest(TemporaryCase):
    """bind 전 요청 임시 파일은 세션 종료와 보관 기한으로 지운다."""

    def setUp(self) -> None:
        super().setUp()
        self.repo = self.base / "repo"
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.root = self.base / "records"

    def event(self, name: str, session: str = SESSION, **extra: object) -> dict:
        payload = {"hook_event_name": name, "session_id": session, "cwd": str(self.repo), **extra}
        return hook.handle_continuity("claude", payload, self.root)

    def test_session_end_removes_unbound_prompt(self) -> None:
        self.event("UserPromptSubmit", prompt="연결 없는 요청")
        self.assertEqual(len(list((self.root / ".prompts").iterdir())), 1)
        self.event("SessionEnd")
        self.assertEqual(list((self.root / ".prompts").iterdir()), [])

    def test_stale_prompts_are_pruned_on_next_hold(self) -> None:
        stale = hook.pending_prompt_path(self.root, "claude", "old-session")
        core.save(stale, {"text": "오래된 요청"})
        old = time.time() - hook.PROMPT_HOLD_SECONDS - 60
        os.utime(stale, (old, old))
        self.event("UserPromptSubmit", prompt="새 요청")
        self.assertFalse(stale.exists())
        self.assertTrue(hook.pending_prompt_path(self.root, "claude", SESSION).exists())


class GuardFailureTest(TemporaryCase):
    """git이 응답하지 않으면 셸 apply_patch도 구조화 쓰기처럼 거부한다."""

    def test_check_tool_denies_shell_and_structured_patch_on_git_timeout(self) -> None:
        structured = {"hook_event_name": "PreToolUse", "tool_name": "apply_patch", "cwd": str(self.base), "tool_input": {"command": PATCH}}
        shell = {**SHELL_PATCH, "cwd": str(self.base)}
        with mock.patch.object(context, "resolve_vault", return_value=self.base / "vault"), \
                mock.patch.object(context, "check_project", side_effect=SLOW):
            for payload in (structured, shell):
                result = guard.check_tool(payload)
                self.assertTrue(self.denied(result), payload["tool_name"])
                self.assertIn("timed out", result["hookSpecificOutput"]["permissionDecisionReason"])

    def test_hook_failure_denies_shell_patch(self) -> None:
        payload = {**SHELL_PATCH, "cwd": str(self.base)}
        self.assertTrue(guard.guarded_write(payload))
        self.assertFalse(guard.guarded_write({**payload, "tool_input": {"command": "ls"}}))
        with mock.patch.object(hook, "handle", side_effect=SLOW), \
                mock.patch.object(sys, "argv", ["continuity_hook.py", "claude"]), \
                mock.patch.object(sys, "stdin", mock.Mock(read=lambda: json.dumps(payload))), \
                mock.patch("builtins.print") as printed:
            hook.main()
        self.assertTrue(self.denied(json.loads(printed.call_args_list[-1].args[0])))

    def test_entry_failure_denies_shell_patch(self) -> None:
        home = self.base / "home"
        (home / ".config/skills").mkdir(parents=True)
        shutil.copy(SCRIPTS / "hook_entry.py", home / ".config/skills/work-continuity.py")
        for payload, expected in ((SHELL_PATCH, True), ({**SHELL_PATCH, "tool_input": {"command": "ls"}}, False)):
            result = subprocess.run(
                [sys.executable, str(home / ".config/skills/work-continuity.py"), "codex"],
                input=json.dumps(payload), capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(self.denied(json.loads(result.stdout)), expected, payload["tool_input"])


    def test_missing_entry_fallback_denies_shell_patch(self) -> None:
        home = self.base / "home"
        home.mkdir()
        for host in ("claude", "codex"):
            hooks = json.loads((PLUGIN / f"hooks/{host}.json").read_text())["hooks"]["PreToolUse"]
            command = next(item for item in hooks if "Bash" in item["matcher"])["hooks"][0]["command"]
            for payload, expected in ((SHELL_PATCH, True), ({**SHELL_PATCH, "tool_input": {"command": "ls"}}, False)):
                result = subprocess.run(["sh", "-c", command], input=json.dumps(payload), env={**os.environ, "HOME": str(home)}, capture_output=True, text=True, timeout=15)
                self.assertEqual(self.denied(json.loads(result.stdout)), expected, f"{host} {payload['tool_input']}")


class TimeBudgetTest(TemporaryCase):
    """훅 내부 대기는 호스트 제한 시간 안에서 끝난다."""

    def test_entry_budget_fits_every_host_timeout(self) -> None:
        for host in ("claude", "codex"):
            hooks = json.loads((PLUGIN / f"hooks/{host}.json").read_text())["hooks"]
            timeouts = {event: {item["timeout"] for group in groups for item in group["hooks"]} for event, groups in hooks.items()}
            for event, values in timeouts.items():
                self.assertEqual(values, {hook_entry.HOOK_TIMEOUTS[host][event]}, f"{host} {event}")
                child, deadline = hook_entry.budget(host, event)
                self.assertLess(deadline, child, f"{host} {event}")
                self.assertLessEqual(child + hook_entry.START_MARGIN, min(values), f"{host} {event}")

    def test_deadline_caps_internal_waits(self) -> None:
        self.assertEqual(context.time_budget(15), 15)
        os.environ[context.DEADLINE_ENV] = str(time.time() + 2)
        self.assertLessEqual(context.time_budget(15), 2)
        self.assertLessEqual(context.time_budget(1), 1)
        os.environ[context.DEADLINE_ENV] = str(time.time() - 1)
        with self.assertRaises(subprocess.TimeoutExpired):
            context.time_budget(3)
        with self.assertRaises(subprocess.TimeoutExpired):
            core.run(["true"])
        os.environ[context.DEADLINE_ENV] = "not a number"
        self.assertEqual(context.time_budget(3), 3)

    def test_slow_runtime_is_denied_before_host_limit(self) -> None:
        home = self.base / "home"
        (home / ".config/skills").mkdir(parents=True)
        shutil.copy(SCRIPTS / "hook_entry.py", home / ".config/skills/work-continuity.py")
        runtime = home / ".claude/skills/git-issue/scripts/continuity_hook.py"
        runtime.parent.mkdir(parents=True)
        runtime.write_text("import time\ntime.sleep(30)\n")
        started = time.monotonic()
        result = subprocess.run(
            [sys.executable, str(home / ".config/skills/work-continuity.py"), "claude"],
            input=json.dumps({**SHELL_PATCH, "tool_name": "Write", "tool_input": {"file_path": "x.md"}}),
            capture_output=True, text=True, timeout=15,
        )
        self.assertLess(time.monotonic() - started, hook_entry.HOOK_TIMEOUTS["claude"]["PreToolUse"])
        self.assertTrue(self.denied(json.loads(result.stdout)))


class HostAdapterTest(TemporaryCase):
    """세션 사용량 기록은 HOSTS 어댑터의 context 유무로만 분기한다."""

    def test_hook_has_no_host_name_branch(self) -> None:
        source = (SCRIPTS / "continuity_hook.py").read_text()
        self.assertIsNone(re.search(r"host\s*==\s*\"(?:claude|codex)\"|\"codex\"", source))
        self.assertIsNone(re.search(r"host\s*==\s*\"(?:claude|codex)\"", (SCRIPTS / "continuity_window.py").read_text().split("def usage", 1)[1].split("\ndef ", 1)[0]))

    def test_meter_uses_adapter_context(self) -> None:
        home = self.base / "home"
        core.save(home / "meter.json", {"host": "claude", "session_id": SESSION, "transcript_path": "/x", "at": time.time()})
        self.assertEqual(hook.host_meter(home, "claude"), (None, None))
        fake = core.HOSTS["claude"]._replace(context=lambda path, session, now: (42.0, session))
        with mock.patch.dict(core.HOSTS, {"claude": fake}):
            self.assertEqual(hook.host_meter(home, "claude"), (42.0, SESSION))
            self.assertEqual(hook.host_meter(home, "codex"), (None, None), "other host record")


class GuardEdgeTest(TemporaryCase):
    def test_copy_into_home_directory_target(self) -> None:
        (self.base / "docsdir").mkdir()
        with mock.patch.dict(os.environ, {"HOME": str(self.base)}):
            result = guard.check_tool({"tool_name": "Bash", "cwd": str(self.base / "elsewhere"), "tool_input": {"command": "cp notes.md ~/docsdir"}})
        self.assertTrue(self.denied(result))

    def test_non_object_source_root_is_skipped(self) -> None:
        project = {"vault": str(self.base / "vault"), "area": str(self.base / "vault/worktree/p"), "path": str(self.base / "repo"),
                   "registration": {"source_document_roots": ["docs", {"path": "notes", "approval": "user"}]}}
        context.check_write(project, self.base / "repo/notes/a.md")
        with self.assertRaisesRegex(context.ContextError, "outside"):
            context.check_write(project, self.base / "repo/docs/a.md")


if __name__ == "__main__":
    unittest.main()
