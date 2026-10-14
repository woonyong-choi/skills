"""skills#43: session 명시 bind 우선 라우팅과 관리 창의 task 전환 추적 회귀 검사.

단위 검사는 가짜 tmux로 입력 경계만 확인한다. 실제 4창 clear와 공식 설치는 이 파일의 범위 밖이다.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any
import unittest
from unittest import mock

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "scripts"))

import continuity as core  # noqa: E402
import continuity_hook as hook  # noqa: E402
import continuity_window as window  # noqa: E402

RUNTIME = (
    PLUGIN.parents[2]
    / ".local/orchestration/issue-continuity/test-runtime/continuity-routing"
)
REPO = core.run(["git", "rev-parse", "--show-toplevel"], cwd=str(PLUGIN)).strip()
OTHER_REPO = "/nonexistent/other-repo"
ACTIVE_REPO = str(Path(REPO).parent)  # 활성 task의 작업본: 시작 cwd의 저장소와 다름
OLD, NEW = (
    "11111111-1111-4111-8111-111111111111",
    "22222222-2222-4222-8222-222222222222",
)
CLEARED = "33333333-3333-4333-8333-333333333333"
PANE = "%7"
IDENTITY = "%7|1|@1"


def write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False))


def release_controller_locks() -> None:
    for lock in window._CONTROLLER_LOCKS:
        lock.close()
    window._CONTROLLER_LOCKS.clear()


def record_tmux(calls: list[tuple[str, ...]]) -> Callable[..., str]:
    def fake(*args: str) -> str:
        calls.append(args)
        return ""

    return fake


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
        os.environ.pop("TMUX_PANE", None)
        self.addCleanup(self.environ.stop)
        self.pane_identity = mock.patch.object(
            hook, "pane_identity", return_value=IDENTITY
        )
        self.pane_identity_mock = self.pane_identity.start()
        self.addCleanup(self.pane_identity.stop)

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

    def managed(
        self,
        home: Path,
        active: str,
        pane: str = PANE,
        *,
        phase: str = "clearing",
        old_session: str = OLD,
    ) -> None:
        write(
            home / "window.json",
            {
                "host": "claude",
                "pane": pane,
                "title": "t",
                "identity": IDENTITY,
                "active_task": active,
                "phase": phase,
                "old_session": old_session,
            },
        )
        os.environ["ISSUE_CONTINUITY_WINDOW"] = str(home)
        os.environ["TMUX_PANE"] = PANE

    def state(self, home: Path, active: str) -> dict[str, Any]:
        state = {
            "host": "claude",
            "pane": PANE,
            "session": "continuity-old",
            "title": "t",
            "identity": "%7|1|@1",
            "cycles": 0,
            "active_task": active,
        }
        write(home / "window.json", state)
        return state

    def starting_window(self, home: Path, **extra: Any) -> None:
        """옛 관리기가 멈춰 phase=starting에 머물고 active_task가 없는 Codex 창 기록"""
        write(
            home / "window.json",
            {
                "host": "codex",
                "pane": PANE,
                "title": "t",
                "identity": IDENTITY,
                "phase": "starting",
                **extra,
            },
        )
        os.environ["ISSUE_CONTINUITY_WINDOW"] = str(home)
        os.environ["TMUX_PANE"] = PANE

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

    def test_find_task_managed_window_active_task_beats_launch_hint(self) -> None:
        home = self.task("old", sessions=[], issue=1)
        new = self.task("new", sessions=[], issue=2)
        self.managed(home, "new")
        os.environ["ISSUE_CONTINUITY_TASK"] = "old"

        self.assertEqual(hook.find_task(self.root, self.payload(CLEARED)), new)
        os.environ["TMUX_PANE"] = "%99"
        self.assertIsNone(
            hook.find_task(self.root, self.payload(CLEARED)),
            "unverified managed window fails closed",
        )

    def test_find_task_stale_startup_cwd_follows_managed_window_active_task(
        self,
    ) -> None:
        self.task("stale", sessions=[], repo=REPO, issue=1)
        home = self.task("home", sessions=[OLD], repo=REPO, issue=3)
        active = self.task("active", sessions=[OLD], repo=ACTIVE_REPO, issue=2)
        self.managed(home, "active")
        os.environ["ISSUE_CONTINUITY_TASK"] = "stale"

        self.assertEqual(hook.find_task(self.root, self.payload(CLEARED)), active)

    def test_find_task_managed_window_fails_closed_without_guessing_another_task(
        self,
    ) -> None:
        stale = self.task("stale", sessions=[], repo=REPO, issue=1)
        home = self.task("home", sessions=[OLD], repo=REPO, issue=3)
        self.task("active", sessions=[OLD], repo=ACTIVE_REPO, issue=2)
        os.environ["ISSUE_CONTINUITY_TASK"] = "stale"
        self.managed(home, "active")
        payload = self.payload(CLEARED)

        self.pane_identity_mock.return_value = "%7|999|@2"
        self.assertIsNone(hook.find_task(self.root, payload), "identity differs")
        self.pane_identity_mock.return_value = IDENTITY
        self.assertIsNone(
            hook.find_task(self.root, payload, host="codex"), "host differs"
        )
        del os.environ["TMUX_PANE"]
        self.assertIsNone(hook.find_task(self.root, payload), "pane unknown")
        os.environ["TMUX_PANE"] = PANE
        write(
            home / "window.json",
            {"host": "claude", "pane": PANE, "active_task": "active"},
        )
        self.assertIsNone(hook.find_task(self.root, payload), "record without identity")
        self.assertTrue((stale / "binding.json").exists())

    def test_find_task_does_not_search_other_windows_when_this_window_is_unverified(
        self,
    ) -> None:
        home = self.task("home", sessions=[OLD], repo=REPO, issue=3)
        other = self.task("other-window", sessions=[OLD], repo=REPO, issue=4)
        self.task("active", sessions=[OLD], repo=ACTIVE_REPO, issue=2)
        self.managed(other, "active")
        write(
            home / "window.json",
            {
                "host": "claude",
                "pane": PANE,
                "identity": "%9|1|@9",
                "active_task": "active",
            },
        )
        os.environ["ISSUE_CONTINUITY_WINDOW"] = str(home)

        self.assertIsNone(hook.find_task(self.root, self.payload(CLEARED)))

    def test_managed_window_rejects_pane_string_without_matching_tmux_identity(
        self,
    ) -> None:
        home = self.task("old", sessions=[], issue=1)
        self.managed(home, "old")
        found = hook.managed_window(self.root)
        assert found is not None
        self.assertEqual(found[0], home)

        self.pane_identity_mock.return_value = "%7|999|@2"
        self.assertIsNone(
            hook.managed_window(self.root),
            "same pane string, different process or window",
        )
        self.pane_identity_mock.return_value = None
        self.assertIsNone(
            hook.managed_window(self.root), "tmux unavailable fails closed"
        )

    def test_managed_window_tampered_active_task_name_is_ignored(self) -> None:
        home = self.task("old", sessions=[], issue=1)
        self.managed(home, "../escape")

        self.assertIsNone(hook.window_task(self.root, REPO))

    def test_managed_window_outside_root_is_rejected(self) -> None:
        foreign = RUNTIME / "foreign-home"
        self.managed(foreign, "old")

        self.assertIsNone(hook.managed_window(self.root))


class LinkSessionTest(RoutingCase):
    def test_link_session_adds_only_session_ids_and_keeps_history(self) -> None:
        folder = self.task("active", sessions=[OLD], issue=2)
        before = core.read(folder / "binding.json")

        hook.link_session(self.root, folder, CLEARED)

        after = core.read(folder / "binding.json")
        self.assertEqual(after["session_ids"], sorted([OLD, CLEARED]))
        self.assertEqual(
            {k: v for k, v in after.items() if k != "session_ids"},
            {k: v for k, v in before.items() if k != "session_ids"},
        )
        hook.link_session(self.root, folder, CLEARED)
        self.assertEqual(
            core.read(folder / "binding.json"), after, "second link is idempotent"
        )

    def test_link_session_bound_elsewhere_is_rejected_without_change(self) -> None:
        active = self.task("active", sessions=[OLD], issue=2)
        other = self.task("other", sessions=[CLEARED], issue=3)
        snapshot = [(p / "binding.json").read_bytes() for p in (active, other)]

        with self.assertRaises(core.ContinuityError):
            hook.link_session(self.root, active, CLEARED)

        self.assertEqual(
            snapshot, [(p / "binding.json").read_bytes() for p in (active, other)]
        )

    def test_session_start_in_managed_window_links_new_session(self) -> None:
        home = self.task("old", sessions=[OLD], issue=1)
        new = self.task("new", sessions=[OLD], issue=2)
        self.managed(home, "new")

        result = hook.handle_continuity(
            "claude", self.payload(CLEARED, "SessionStart"), self.root
        )

        self.assertIn(
            "https://example.invalid/issues/2",
            result["hookSpecificOutput"]["additionalContext"],
        )
        self.assertEqual(
            core.read(new / "binding.json")["session_ids"], sorted([OLD, CLEARED])
        )
        self.assertEqual(
            core.read(home / "binding.json")["session_ids"], [OLD], "old task untouched"
        )

    def test_session_start_after_clear_with_stale_startup_cwd_links_active_task(
        self,
    ) -> None:
        stale = self.task("stale", sessions=[], repo=REPO, issue=1)
        home = self.task("home", sessions=[OLD], repo=REPO, issue=3)
        active = self.task("active", sessions=[OLD], repo=ACTIVE_REPO, issue=2)
        self.managed(home, "active")
        os.environ["ISSUE_CONTINUITY_TASK"] = "stale"

        result = hook.handle_continuity(
            "claude", self.payload(CLEARED, "SessionStart"), self.root
        )

        self.assertIn(
            "https://example.invalid/issues/2",
            result["hookSpecificOutput"]["additionalContext"],
        )
        self.assertEqual(
            core.read(active / "binding.json")["session_ids"], sorted([OLD, CLEARED])
        )
        self.assertEqual(core.read(stale / "binding.json")["session_ids"], [])

    def test_stale_cwd_session_start_with_unverified_window_links_nothing(self) -> None:
        stale = self.task("stale", sessions=[], repo=REPO, issue=1)
        home = self.task("home", sessions=[OLD], repo=REPO, issue=3)
        active = self.task("active", sessions=[OLD], repo=ACTIVE_REPO, issue=2)
        self.managed(home, "active")
        os.environ["ISSUE_CONTINUITY_TASK"] = "stale"
        self.pane_identity_mock.return_value = "%7|999|@2"

        hook.handle_continuity(
            "claude", self.payload(CLEARED, "SessionStart"), self.root
        )

        self.assertEqual(core.read(active / "binding.json")["session_ids"], [OLD])
        self.assertEqual(core.read(stale / "binding.json")["session_ids"], [])

    def test_session_start_of_nested_session_in_managed_window_does_not_link(
        self,
    ) -> None:
        home = self.task("old", sessions=[OLD], issue=1)
        new = self.task("new", sessions=[OLD], issue=2)
        self.managed(home, "new", phase="resumed")

        hook.handle_continuity(
            "claude", self.payload(CLEARED, "SessionStart"), self.root
        )

        self.assertEqual(core.read(new / "binding.json")["session_ids"], [OLD])

    def test_session_start_with_unrelated_old_session_does_not_link(self) -> None:
        home = self.task("old", sessions=[OLD], issue=1)
        new = self.task("new", sessions=[], issue=2)
        self.managed(home, "new", phase="clearing", old_session=OLD)

        hook.handle_continuity(
            "claude", self.payload(CLEARED, "SessionStart"), self.root
        )

        self.assertEqual(core.read(new / "binding.json")["session_ids"], [])

    def test_session_start_bound_elsewhere_keeps_its_task_and_active_binding(
        self,
    ) -> None:
        home = self.task("old", sessions=[OLD], issue=1)
        active = self.task("new", sessions=[OLD], issue=2)
        self.task("other", sessions=[CLEARED], issue=3)
        self.managed(home, "new")

        result = hook.handle_continuity(
            "claude", self.payload(CLEARED, "SessionStart"), self.root
        )

        self.assertIn(
            "https://example.invalid/issues/3",
            result["hookSpecificOutput"]["additionalContext"],
        )
        self.assertEqual(core.read(active / "binding.json")["session_ids"], [OLD])

    def test_session_start_outside_managed_window_does_not_link(self) -> None:
        old = self.task("old", sessions=[], issue=1)

        hook.handle_continuity(
            "claude", self.payload(CLEARED, "SessionStart"), self.root
        )

        self.assertEqual(core.read(old / "binding.json")["session_ids"], [])


class WindowFollowTest(RoutingCase):
    def test_follow_task_keeps_window_identity_and_moves_active_task(self) -> None:
        home = self.task("old", sessions=[], issue=1)
        new = self.task("new", sessions=[NEW], issue=2)
        state = self.state(home, "old")
        os.environ["ISSUE_CONTINUITY_ROOT"] = str(self.root)

        with contextlib.redirect_stdout(io.StringIO()):
            moved = window.follow_task(home, state, NEW)
            kept = window.follow_task(home, state, CLEARED)

        saved = core.read(home / "window.json")
        self.assertTrue(moved)
        self.assertFalse(kept)
        self.assertEqual(saved["active_task"], "new")
        self.assertEqual(
            {k: saved[k] for k in ("pane", "identity", "title", "session")},
            {
                "pane": PANE,
                "identity": "%7|1|@1",
                "title": "t",
                "session": "continuity-old",
            },
        )
        self.assertFalse(
            (new / "window.json").exists(), "window record stays in the window home"
        )

    def test_follow_task_duplicate_session_fails_closed(self) -> None:
        home = self.task("old", sessions=[NEW], issue=1)
        self.task("new", sessions=[NEW], issue=2)
        state = self.state(home, "old")
        os.environ["ISSUE_CONTINUITY_ROOT"] = str(self.root)

        with self.assertRaises(core.ContinuityError):
            window.follow_task(home, state, NEW)

        self.assertEqual(state["active_task"], "old")

    def test_task_change_while_waiting_for_checkpoint_stops_before_clear(self) -> None:
        home = self.task("old", sessions=[], issue=1)
        self.task("new", sessions=[NEW], issue=2)
        state = self.state(home, "old")
        os.environ["ISSUE_CONTINUITY_ROOT"] = str(self.root)
        write(
            home / "meter.json", {"session_id": NEW, "percent": 80, "at": time.time()}
        )
        args = mock.Mock(host="claude")

        with mock.patch.object(window, "screen", return_value=""):
            with self.assertRaises(core.ContinuityError) as caught:
                window.ensure_task_unchanged(args, home, state)

        self.assertIn("clear not sent", str(caught.exception))

    def test_unknown_session_before_checkpoint_write_is_refused(self) -> None:
        home = self.task("old", sessions=[], issue=1)
        state = self.state(home, "old")
        os.environ["ISSUE_CONTINUITY_ROOT"] = str(self.root)
        args = mock.Mock(host="claude")

        with mock.patch.object(window, "screen", return_value=""):
            window.ensure_task_unchanged(args, home, state)
            with self.assertRaises(core.ContinuityError):
                window.ensure_task_unchanged(args, home, state, strict=True)

    def test_reset_cycle_without_known_session_sends_nothing(self) -> None:
        home = self.task("old", sessions=[], issue=1)
        state = self.state(home, "old")
        os.environ["ISSUE_CONTINUITY_ROOT"] = str(self.root)
        send = mock.Mock()

        with (
            mock.patch.object(window, "screen", return_value=""),
            mock.patch.object(window, "send", send),
        ):
            with self.assertRaises(core.ContinuityError):
                window.reset_cycle(mock.Mock(host="claude"), home, state)

        send.assert_not_called()

    def test_second_controller_for_same_home_is_refused(self) -> None:
        home = self.task("old", sessions=[], issue=1)
        self.addCleanup(release_controller_locks)

        window.acquire_controller(home)

        with self.assertRaises(core.ContinuityError):
            window.acquire_controller(home)


class AttachAndResumeTest(RoutingCase):
    def args(self, **values: object) -> mock.Mock:
        return mock.Mock(task="old", host="claude", title="t", **values)

    def fake_tmux(self, identity: str = IDENTITY, title: str = "t") -> mock.Mock:
        def answer(*args: str) -> str:
            if "#{cursor_x}" in args:
                return "2"
            return title if "#{pane_title}" in args else identity

        return mock.Mock(side_effect=answer)

    def attach(
        self,
        home: Path,
        *,
        identity: str = IDENTITY,
        idle: bool = True,
        title: str = "t",
    ) -> tuple[object, mock.Mock]:
        send = mock.Mock()
        with (
            mock.patch.object(window, "tmux", self.fake_tmux(identity, title)),
            mock.patch.object(window, "screen", return_value=""),
            mock.patch.object(window, "window_idle", return_value=idle),
            mock.patch.object(window, "send", send),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            try:
                return window.attach_window(self.args(), home), send
            except core.ContinuityError as error:
                return error, send

    def test_attach_validates_identity_host_title_and_idle_without_input(self) -> None:
        home = self.task("old", sessions=[], issue=1)
        self.state(home, "old")

        accepted, send = self.attach(home)
        self.assertIsInstance(accepted, dict)
        send.assert_not_called()
        for label, kwargs in (
            ("identity", {"identity": "%8|1|@1"}),
            ("not idle", {"idle": False}),
        ):
            rejected, send = self.attach(home, **kwargs)
            self.assertIsInstance(rejected, core.ContinuityError, label)
            send.assert_not_called()

    def test_idle_rejects_trust_and_authentication_screens(self) -> None:
        prompt = "\n❯ \n"
        for label, text in (
            (
                "trust",
                "Do you trust this folder?\n1. Yes, I trust this folder" + prompt,
            ),
            ("allow", "Do you want to proceed?\n❯ 1. Yes"),
            ("login", "Invalid API key · Please run /login" + prompt),
            ("not logged in", "Not logged in" + prompt),
            ("api 401", "API Error: 401 authentication_error" + prompt),
        ):
            self.assertFalse(window.idle(text, "claude", 2), label)
        self.assertTrue(window.idle("작업 결과\n" + prompt, "claude", 2))

    def test_attach_refuses_trust_or_authentication_screen_without_input(self) -> None:
        home = self.task("old", sessions=[], issue=1)
        self.state(home, "old")
        for text in ("Do you trust this folder?\n❯ \n", "Please run /login\n❯ \n"):
            send = mock.Mock()

            def fake_tmux(*args: str) -> str:
                return "2" if "#{cursor_x}" in args else IDENTITY

            with (
                mock.patch.object(window, "tmux", side_effect=fake_tmux),
                mock.patch.object(window, "screen", return_value=text),
                mock.patch.object(window, "send", send),
            ):
                with self.assertRaises(core.ContinuityError):
                    window.attach_window(self.args(), home)
            send.assert_not_called()

    def test_attach_checks_actual_pane_title_not_only_the_argument(self) -> None:
        home = self.task("old", sessions=[], issue=1)
        self.state(home, "old")

        accepted, send = self.attach(home, title="t · 작업")
        rejected, send_rejected = self.attach(home, title="다른 제목")

        self.assertIsInstance(accepted, dict)
        self.assertIsInstance(rejected, core.ContinuityError)
        send.assert_not_called()
        send_rejected.assert_not_called()

    def test_attach_refuses_while_clearing(self) -> None:
        home = self.task("old", sessions=[], issue=1)
        state = self.state(home, "old")
        write(home / "window.json", {**state, "phase": "clearing"})

        rejected, send = self.attach(home)

        self.assertIsInstance(rejected, core.ContinuityError)
        send.assert_not_called()

    def resume(
        self, home: Path, state: dict[str, Any], *, new_session: str = CLEARED
    ) -> mock.Mock:
        send = mock.Mock()
        with (
            mock.patch.object(window, "tmux", return_value="t"),
            mock.patch.object(window, "screen", return_value=""),
            mock.patch.object(window, "confirm_new_session", return_value=new_session),
            mock.patch.object(window, "finish_resume"),
            mock.patch.object(time, "sleep"),
            mock.patch.object(window, "send", send),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            window.finish_reset(self.args(), home, state)
        return send

    def clearing_state(
        self, home: Path, active: str, revision: str = "r1"
    ) -> dict[str, Any]:
        state = {
            **self.state(home, active),
            "old_session": OLD,
            "checkpoint": revision,
            "checkpoint_task": active,
        }
        os.environ["ISSUE_CONTINUITY_ROOT"] = str(self.root)
        return state

    def test_finish_reset_links_new_session_before_resume_input(self) -> None:
        home = self.task("old", sessions=[OLD], issue=1)
        write(home / "checkpoint.json", {"remote_id": "r1"})
        state = self.clearing_state(home, "old")

        send = self.resume(home, state)

        self.assertEqual(
            core.read(home / "binding.json")["session_ids"], sorted([OLD, CLEARED])
        )
        self.assertIn("restore --task old", send.call_args_list[-1].args[1])

    def test_finish_reset_refuses_changed_checkpoint_or_foreign_session_without_input(
        self,
    ) -> None:
        home = self.task("old", sessions=[OLD], issue=1)
        self.task("other", sessions=[CLEARED], issue=3)
        write(home / "checkpoint.json", {"remote_id": "r2"})
        state = self.clearing_state(home, "old")
        for revision, label in (
            ("r1", "revision changed"),
            ("r2", "session bound elsewhere"),
        ):
            state["checkpoint"] = revision
            send = mock.Mock()
            with (
                mock.patch.object(window, "tmux", return_value="t"),
                mock.patch.object(window, "confirm_new_session", return_value=CLEARED),
                mock.patch.object(window, "send", send),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                with self.assertRaises(core.ContinuityError, msg=label):
                    window.finish_reset(self.args(), home, state)
            send.assert_not_called()
        self.assertEqual(core.read(home / "binding.json")["session_ids"], [OLD])

    def test_finish_reset_uses_new_active_task_after_switch(self) -> None:
        home = self.task("old", sessions=[], issue=1)
        new = self.task("new", sessions=[OLD], issue=2)
        write(new / "checkpoint.json", {"remote_id": "r9"})
        state = self.clearing_state(home, "new", "r9")

        send = self.resume(home, state)

        self.assertEqual(
            core.read(new / "binding.json")["session_ids"], sorted([OLD, CLEARED])
        )
        self.assertEqual(core.read(home / "binding.json")["session_ids"], [])
        self.assertIn("restore --task new", send.call_args_list[-1].args[1])

    def test_resume_prompt_names_verified_context_and_explicit_root_once(self) -> None:
        home = self.task("old", sessions=[OLD], issue=1)
        write(home / "checkpoint.json", {"remote_id": "r1"})
        state = self.clearing_state(home, "old")

        send = self.resume(home, state)

        prompts = [call.args[1] for call in send.call_args_list]
        self.assertEqual(len(prompts), 1)
        text = prompts[0]
        for expected in (
            "https://example.invalid/issues/1",
            REPO,
            CLEARED,
            f"--root {self.root} restore --task old --offline",
            str(home / "binding.json"),
            "binding repo에서 실행",
        ):
            self.assertIn(expected, text)
        self.assertIn(CLEARED, core.read(home / "binding.json")["session_ids"])

    def test_checkpoint_request_names_context_and_explicit_root(self) -> None:
        home = self.task("old", sessions=[OLD], issue=1)
        state = {**self.state(home, "old"), "active_task": "old"}
        os.environ["ISSUE_CONTINUITY_ROOT"] = str(self.root)
        send = mock.Mock()
        with mock.patch.object(window, "send", send):
            window.request_checkpoint(
                self.args(), state, home, core.read(home / "binding.json")
            )

        text = send.call_args.args[1]
        self.assertEqual(send.call_count, 1)
        self.assertIn(f"--root {self.root} restore --task old --offline", text)
        self.assertIn("https://example.invalid/issues/1", text)
        self.assertIn(REPO, text)

    def test_send_with_lead_types_short_request_first_and_presses_enter_once(
        self,
    ) -> None:
        calls: list[tuple[str, ...]] = []
        with (
            mock.patch.object(window, "tmux", side_effect=record_tmux(calls)),
            mock.patch.object(time, "sleep") as sleep,
        ):
            window.send(PANE, "상세\n입력", lead="요청")

        self.assertEqual(
            calls,
            [
                ("send-keys", "-t", PANE, "-l", "요청"),
                ("send-keys", "-t", PANE, "-l", "상세 입력"),
                ("send-keys", "-t", PANE, "Enter"),
            ],
        )
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [0.5, 0.5])

    def test_send_without_lead_keeps_clear_and_rename_input(self) -> None:
        calls: list[tuple[str, ...]] = []
        with (
            mock.patch.object(window, "tmux", side_effect=record_tmux(calls)),
            mock.patch.object(time, "sleep"),
        ):
            window.send(PANE, "/clear")

        self.assertEqual(
            calls,
            [
                ("send-keys", "-t", PANE, "-l", "/clear"),
                ("send-keys", "-t", PANE, "Enter"),
            ],
        )

    def test_prompts_use_lead_and_name_orchestration_only_record_location(self) -> None:
        home = self.task("old", sessions=[OLD], issue=1)
        write(home / "checkpoint.json", {"remote_id": "r1"})
        state = self.clearing_state(home, "old")
        resume_send = self.resume(home, state)
        checkpoint_send = mock.Mock()
        with mock.patch.object(window, "send", checkpoint_send):
            window.request_checkpoint(
                self.args(), state, home, core.read(home / "binding.json")
            )

        for sent in (resume_send, checkpoint_send):
            self.assertEqual(sent.call_count, 1)
            self.assertTrue(sent.call_args.kwargs["lead"])
            self.assertIn("활성 orchestration 폴더만 사용", sent.call_args.args[1])


class HookProcessTest(RoutingCase):
    """공식 훅 입력(stdin JSON)을 정본 continuity_hook.py와 continuity_statusline.py에 그대로 전달한다."""

    def run_script(
        self, script: str, payload: dict[str, Any], *args: str, **env: str
    ) -> subprocess.CompletedProcess[str]:
        clean = {
            k: v for k, v in os.environ.items() if not k.startswith("ISSUE_CONTINUITY")
        }
        fake = self.root / "bin" / "tmux"
        if not fake.exists():
            fake.parent.mkdir()
            fake.write_text(
                "#!/bin/sh\nprintf '%s\\n' \"${FAKE_TMUX_IDENTITY:-%7|1|@1}\"\n"
            )
            fake.chmod(0o755)
        clean["PATH"] = str(fake.parent) + os.pathsep + clean.get("PATH", "")
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

    def test_session_start_after_clear_links_session_in_managed_window(self) -> None:
        home = self.task("old", sessions=[OLD], issue=1)
        new = self.task("new", sessions=[OLD], issue=2)
        self.managed(home, "new")

        out = self.hook(
            self.payload(CLEARED, "SessionStart"),
            ISSUE_CONTINUITY_WINDOW=str(home),
            TMUX_PANE=PANE,
            ISSUE_CONTINUITY_TASK="old",
        )

        self.assertIn(
            "https://example.invalid/issues/2",
            out["hookSpecificOutput"]["additionalContext"],
        )
        self.assertEqual(
            core.read(new / "binding.json")["session_ids"], sorted([OLD, CLEARED])
        )

    def test_statusline_writes_meter_to_window_home_while_following_new_task(
        self,
    ) -> None:
        home = self.task("old", sessions=[], issue=1)
        new = self.task("new", sessions=[NEW], issue=2)
        self.managed(home, "new")
        command = self.root / "original-statusline.json"
        write(command, {})
        payload = {**self.payload(NEW), "context_window": {"used_percentage": 81}}

        done = self.run_script(
            "continuity_statusline.py",
            payload,
            "--command-file",
            str(command),
            ISSUE_CONTINUITY_WINDOW=str(home),
            TMUX_PANE=PANE,
        )

        meter = core.read(home / "meter.json")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(
            (meter["session_id"], meter["percent"], meter["task"]), (NEW, 81, "new")
        )
        self.assertFalse((new / "meter.json").exists())
        usage = self.hook(
            self.payload(NEW, "PostToolUse"),
            ISSUE_CONTINUITY_WINDOW=str(home),
            TMUX_PANE=PANE,
        )
        self.assertIn("81%", usage["hookSpecificOutput"]["additionalContext"])

    def test_statusline_wrong_tmux_identity_writes_no_meter(self) -> None:
        home = self.task("old", sessions=[NEW], issue=1)
        self.managed(home, "old")
        command = self.root / "original-statusline.json"
        write(command, {})

        done = self.run_script(
            "continuity_statusline.py",
            {**self.payload(NEW), "context_window": {"used_percentage": 50}},
            "--command-file",
            str(command),
            ISSUE_CONTINUITY_WINDOW=str(home),
            TMUX_PANE=PANE,
            FAKE_TMUX_IDENTITY="%7|999|@2",
        )

        self.assertIn("unverified", done.stderr)
        self.assertFalse((home / "meter.json").exists())

    def test_official_entrypoint_chain_links_cleared_session_despite_stale_startup_cwd(
        self,
    ) -> None:
        """설치 뒤와 같은 구성(stable 진입점 → git-issue 스킬 폴더)을 정본 코드로 재현한다."""
        stale = self.task("stale", sessions=[], repo=REPO, issue=1)
        home = self.task("home", sessions=[OLD], repo=REPO, issue=3)
        active = self.task("active", sessions=[OLD], repo=ACTIVE_REPO, issue=2)
        self.managed(home, "active")
        fake_home = self.root / "home-dir"
        (fake_home / ".config/skills").mkdir(parents=True)
        (fake_home / ".claude/skills").mkdir(parents=True)
        shutil.copy(
            PLUGIN / "scripts/hook_entry.py",
            fake_home / ".config/skills/work-continuity.py",
        )
        (fake_home / ".claude/skills/git-issue").symlink_to(PLUGIN)
        launcher = fake_home / ".config/skills/work-continuity.py"
        clean = {
            k: v for k, v in os.environ.items() if not k.startswith("ISSUE_CONTINUITY")
        }
        fake = self.root / "bin" / "tmux"
        fake.parent.mkdir()
        fake.write_text("#!/bin/sh\nprintf '%s\\n' '%7|1|@1'\n")
        fake.chmod(0o755)

        done = subprocess.run(
            [sys.executable, str(launcher), "claude"],
            input=json.dumps(self.payload(CLEARED, "SessionStart")),
            capture_output=True,
            text=True,
            env={
                **clean,
                "PATH": str(fake.parent) + os.pathsep + clean.get("PATH", ""),
                "ISSUE_CONTINUITY_ROOT": str(self.root),
                "ISSUE_CONTINUITY_WINDOW": str(home),
                "ISSUE_CONTINUITY_TASK": "stale",
                "TMUX_PANE": PANE,
            },
        )

        self.assertEqual((done.returncode, done.stderr), (0, ""))
        context = json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("https://example.invalid/issues/2", context)
        self.assertEqual(
            core.read(active / "binding.json")["session_ids"], sorted([OLD, CLEARED])
        )
        self.assertEqual(core.read(stale / "binding.json")["session_ids"], [])

    def test_statusline_unverified_window_writes_no_meter(self) -> None:
        home = self.task("old", sessions=[NEW], issue=1)
        self.managed(home, "old")
        command = self.root / "original-statusline.json"
        write(command, {})

        done = self.run_script(
            "continuity_statusline.py",
            {**self.payload(NEW), "context_window": {"used_percentage": 50}},
            "--command-file",
            str(command),
            ISSUE_CONTINUITY_WINDOW=str(home),
            TMUX_PANE="%99",
        )

        self.assertIn("unverified", done.stderr)
        self.assertFalse((home / "meter.json").exists())


CODEX_SESSION = "00000000-0000-4000-8000-0000000000c1"  # 명백한 합성 값
OTHER_CODEX_SESSION = "00000000-0000-4000-8000-0000000000c2"
META_STAMP = "2026-01-01T00:00:00.000Z"
WINDOW_SIZE = 258400


def fresh_stamp(seconds_ago: float = 0, offset_hours: int = 0) -> str:
    """지금 기준 token_count 시각(ISO 8601). offset_hours로 UTC가 아닌 시간대를 만든다."""
    zone = timezone(timedelta(hours=offset_hours))
    moment = datetime.now(zone) - timedelta(seconds=seconds_ago)
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def jsonl(record: dict[str, Any]) -> bytes:
    return (json.dumps(record, separators=(",", ":")) + "\n").encode()


def meta_line(session: str = CODEX_SESSION, version: str = "0.158.0") -> bytes:
    payload = {"id": session, "session_id": session, "cli_version": version}
    return jsonl(
        {
            "timestamp": META_STAMP,
            "ordinal": 0,
            "type": "session_meta",
            "payload": payload,
        }
    )


def token_line(
    used: object, window: object = WINDOW_SIZE, stamp: str | None = None
) -> bytes:
    info = {"last_token_usage": {"total_tokens": used}, "model_context_window": window}
    payload = {"type": "token_count", "info": info}
    return jsonl(
        {
            "timestamp": stamp or fresh_stamp(),
            "ordinal": 1,
            "type": "event_msg",
            "payload": payload,
        }
    )


def compacted_line() -> bytes:
    return jsonl(
        {
            "timestamp": META_STAMP,
            "ordinal": 2,
            "type": "compacted",
            "payload": {"message": ""},
        }
    )


class CodexUsageTest(RoutingCase):
    """skills#43 Codex 어댑터: session 검증과 사용량 검증을 분리한다. 합성 rollout만 쓴다."""

    def setUp(self) -> None:
        super().setUp()
        self.codex_home = self.root / "codex"
        self.sessions = self.codex_home / "sessions" / "2026" / "10" / "15"
        self.sessions.mkdir(parents=True)
        os.environ["CODEX_HOME"] = str(self.codex_home.resolve())
        self.home = self.root / "home"

    def rollout(self, *lines: bytes, session: str = CODEX_SESSION) -> Path:
        path = self.sessions / f"rollout-2026-10-15T01-05-53-{session}.jsonl"
        path.write_bytes(b"".join(lines))
        return path.resolve()

    def record(self, path: Path, **overrides: object) -> None:
        meter = {
            "host": "codex",
            "session_id": CODEX_SESSION,
            "transcript_path": str(path),
            "percent": None,
            "at": time.time(),
            **overrides,
        }
        write(self.home / "meter.json", meter)

    def test_codex_usage_computes_ratio_for_verified_session(self) -> None:
        self.record(self.rollout(meta_line(), token_line(129200)))

        self.assertEqual(hook.codex_usage(self.home), (50.0, CODEX_SESSION))

    def test_codex_usage_after_clear_returns_session_without_metric(self) -> None:
        self.record(self.rollout(meta_line()))

        self.assertEqual(hook.codex_usage(self.home), (None, CODEX_SESSION))

    def test_codex_usage_is_unknown_between_compaction_and_next_token_count(
        self,
    ) -> None:
        self.record(self.rollout(meta_line(), token_line(240000), compacted_line()))
        self.assertEqual(hook.codex_usage(self.home), (None, CODEX_SESSION))

        self.record(
            self.rollout(
                meta_line(), token_line(240000), compacted_line(), token_line(25840)
            )
        )
        self.assertEqual(hook.codex_usage(self.home), (10.0, CODEX_SESSION))

    def test_codex_usage_is_unknown_while_last_line_is_unfinished(self) -> None:
        partial = token_line(WINDOW_SIZE)[:-20]
        unterminated = token_line(WINDOW_SIZE)[:-1]  # 완전한 JSON이지만 줄바꿈 전
        self.record(self.rollout(meta_line(), token_line(129200), partial))
        self.assertEqual(hook.codex_usage(self.home), (None, CODEX_SESSION))

        self.record(self.rollout(meta_line(), partial))
        self.assertEqual(hook.codex_usage(self.home), (None, CODEX_SESSION))

        self.record(self.rollout(meta_line(), token_line(129200), partial + b"\n"))
        self.assertEqual(hook.codex_usage(self.home), (None, CODEX_SESSION))

        self.record(self.rollout(meta_line(), token_line(129200), unterminated))
        self.assertEqual(hook.codex_usage(self.home), (None, CODEX_SESSION))

        self.record(self.rollout(meta_line(), token_line(129200)))
        self.assertEqual(hook.codex_usage(self.home), (50.0, CODEX_SESSION))

    def test_session_meta_of_other_json_types_is_rejected_without_error(self) -> None:
        for line in (b"[]\n", b"null\n", b"5\n", b'"text"\n'):
            with self.subTest(line=line):
                self.assertFalse(hook.session_meta_matches(line, CODEX_SESSION))
                self.record(self.rollout(line, token_line(10)))
                self.assertEqual(hook.codex_usage(self.home), (None, None))

    def test_codex_usage_rejects_old_or_untimed_metric_keeping_session(self) -> None:
        cases = {
            "old": "2025-01-01T00:00:00Z",
            "over max age": fresh_stamp(seconds_ago=7 * 3600),
            "no timezone": fresh_stamp().removesuffix("Z"),
            "garbage": "yesterday",
            "number": 5,
        }
        for name, stamp in cases.items():
            with self.subTest(name):
                line = token_line(900, 1000, stamp=stamp)  # type: ignore[arg-type]
                self.record(self.rollout(meta_line(), line))
                self.assertEqual(hook.codex_usage(self.home), (None, CODEX_SESSION))

    def test_codex_usage_accepts_fresh_metric_with_utc_offset(self) -> None:
        line = token_line(900, 1000, stamp=fresh_stamp(offset_hours=9))
        self.record(self.rollout(meta_line(), line))

        self.assertEqual(hook.codex_usage(self.home), (90.0, CODEX_SESSION))

    def test_codex_usage_ignores_token_line_that_is_not_an_object(self) -> None:
        self.record(self.rollout(meta_line(), b'[{"type":"token_count"}]\n'))

        self.assertEqual(hook.codex_usage(self.home), (None, CODEX_SESSION))

    def test_codex_usage_rejects_invalid_numbers_keeping_session(self) -> None:
        cases = [
            (True, WINDOW_SIZE),
            (float("nan"), WINDOW_SIZE),
            (12.5, WINDOW_SIZE),
            ("5", WINDOW_SIZE),
            (-1, WINDOW_SIZE),
            (WINDOW_SIZE + 1, WINDOW_SIZE),
            (10, 0),
            (10, True),
            (10, None),
        ]
        for used, size in cases:
            with self.subTest(used=used, size=size):
                self.record(self.rollout(meta_line(), token_line(used, size)))
                self.assertEqual(hook.codex_usage(self.home), (None, CODEX_SESSION))

    def test_codex_usage_rejects_future_token_stamp_keeping_session(self) -> None:
        line = token_line(10, stamp="2099-01-01T00:00:00.000Z")
        self.record(self.rollout(meta_line(), line))

        self.assertEqual(hook.codex_usage(self.home), (None, CODEX_SESSION))

    def test_codex_usage_session_mismatch_is_unknown_for_both(self) -> None:
        path = self.rollout(meta_line(OTHER_CODEX_SESSION), token_line(10))
        self.record(path)
        self.assertEqual(hook.codex_usage(self.home), (None, None))

        other = self.rollout(
            meta_line(OTHER_CODEX_SESSION), token_line(10), session=OTHER_CODEX_SESSION
        )
        self.record(other)
        self.assertEqual(hook.codex_usage(self.home), (None, None))

    def test_codex_usage_rejects_other_cli_version(self) -> None:
        self.record(self.rollout(meta_line(version="0.159.0"), token_line(10)))

        self.assertEqual(hook.codex_usage(self.home), (None, None))

    def test_codex_usage_rejects_links_and_paths_outside_sessions(self) -> None:
        real = self.rollout(meta_line(), token_line(10))
        link = self.sessions / "rollout-link" / real.name
        link.parent.mkdir()
        os.symlink(real, link)
        self.record(link)
        self.assertEqual(hook.codex_usage(self.home), (None, None), "file link")

        linked_dir = self.sessions.parent / "linked"
        os.symlink(self.sessions, linked_dir)
        self.record(linked_dir / real.name)
        self.assertEqual(hook.codex_usage(self.home), (None, None), "directory link")

        outside = self.root / "outside" / real.name
        outside.parent.mkdir()
        outside.write_bytes(real.read_bytes())
        self.record(outside.resolve())
        self.assertEqual(hook.codex_usage(self.home), (None, None), "outside")

    def test_codex_usage_rejects_stale_or_malformed_record(self) -> None:
        path = self.rollout(meta_line(), token_line(10))
        now = time.time()
        cases: dict[str, dict[str, Any]] = {
            "stale": {"at": now - 7 * 3600},
            "future": {"at": now + 3600},
            "bool at": {"at": True},
            "text at": {"at": "now"},
            "claude meter": {"host": "claude"},
            "no path": {"transcript_path": None},
            "bad session": {"session_id": "not-a-session"},
        }
        for name, overrides in cases.items():
            with self.subTest(name):
                self.record(path, **overrides)
                self.assertEqual(hook.codex_usage(self.home), (None, None))
        (self.home / "meter.json").unlink()
        self.assertEqual(hook.codex_usage(self.home), (None, None), "missing record")

    def test_codex_usage_reads_only_the_tail_of_a_large_file(self) -> None:
        filler = jsonl(
            {
                "timestamp": META_STAMP,
                "ordinal": 3,
                "type": "response_item",
                "payload": {"x": "a" * 1000},
            }
        )
        body = [filler] * 5000
        self.record(
            self.rollout(meta_line(), token_line(240000), *body, token_line(25840))
        )
        self.assertEqual(hook.codex_usage(self.home), (10.0, CODEX_SESSION))

        self.record(self.rollout(meta_line(), token_line(240000), *body))
        self.assertEqual(hook.codex_usage(self.home), (None, CODEX_SESSION))

    def test_window_usage_for_codex_ignores_footer_text(self) -> None:
        self.record(self.rollout(meta_line(), token_line(129200)))

        percent, session = window.usage("Context 42% context left", "codex", self.home)

        self.assertEqual((percent, session), (50.0, CODEX_SESSION))

    def test_confirm_new_session_accepts_session_before_first_token_count(self) -> None:
        args = mock.Mock(host="codex")
        state = {"pane": PANE, "old_session": OLD}
        with (
            mock.patch.object(window, "screen", return_value=""),
            mock.patch.object(window, "window_idle", return_value=True),
            mock.patch.object(window, "usage", return_value=(None, NEW)),
        ):
            self.assertEqual(window.confirm_new_session(args, self.home, state), NEW)

    def test_watch_follows_session_even_when_usage_is_unknown(self) -> None:
        args = mock.Mock(host="codex", threshold=75)
        state = {"pane": PANE, "active_task": "old"}
        with (
            mock.patch.object(window, "screen", return_value=""),
            mock.patch.object(window, "usage", return_value=(None, NEW)),
            mock.patch.object(
                window, "follow_task", side_effect=KeyboardInterrupt
            ) as follow,
            self.assertRaises(KeyboardInterrupt),
        ):
            window.watch(args, self.home, state)
        follow.assert_called_once_with(self.home, state, NEW)


class IdleScreenTest(unittest.TestCase):
    """관리기가 자동 초기화하기 전에 실제 작업 중 화면을 보수적으로 거절하는지 확인한다."""

    PROMPT = "❯ \n"

    def test_idle_rejects_observed_claude_busy_lines(self) -> None:
        busy = [
            "· Synthesizing… (1m 56s · ↓ 9.9k tokens)",
            "· Grooving…",
            "✻ Thinking…",
            "(45s · ↑ 1.2k tokens)",
            "⏺ Bash(sleep 30)\n  ⎿  Running…",
            "Press up to edit queued messages",
        ]
        for line in busy:
            with self.subTest(line=line):
                self.assertFalse(window.idle(f"{line}\n{self.PROMPT}", "claude", 2))

    def test_idle_rejects_prompt_with_typed_input(self) -> None:
        self.assertFalse(window.idle("● done\n❯ draft text\n", "claude", 2))

    def test_idle_accepts_quiet_claude_prompt(self) -> None:
        self.assertTrue(window.idle(f"● Finished.\n{self.PROMPT}", "claude", 2))


class StopWatch(Exception):
    """watch를 한 번만 돌리기 위한 시험용 중단"""


def fake_tmux(*args: str) -> str:
    return "t" if args[-1] == "#{pane_title}" else IDENTITY


class CodexFirstConnectionTest(RoutingCase):
    """옛 관리기 창(active_task 없음)에서 첫 meter → attach → follow_task가 session의 명시 bind를 따르는지 확인한다."""

    def setUp(self) -> None:
        super().setUp()
        self.fresh_scene()

    def fresh_scene(self) -> None:
        """부분 시험마다 task·창·rollout 기록을 비운다."""
        shutil.rmtree(self.root)
        self.root.mkdir()
        self.codex_home = self.root / "codex"
        self.sessions = self.codex_home / "sessions" / "2026" / "10" / "15"
        self.sessions.mkdir(parents=True)
        os.environ["CODEX_HOME"] = str(self.codex_home.resolve())
        os.environ["ISSUE_CONTINUITY_ROOT"] = str(self.root)
        self.pane_identity_mock.return_value = IDENTITY

    def hook_event(self, session: str) -> Path:
        path = self.sessions / f"rollout-2026-10-15T01-05-53-{session}.jsonl"
        path.write_bytes(meta_line(session) + token_line(129200))
        payload = {**self.payload(session), "transcript_path": str(path.resolve())}
        hook.handle_continuity("codex", payload, self.root)
        return path

    def attach_and_watch_once(self, home: Path) -> dict[str, Any]:
        args = mock.Mock(host="codex", title="t", task=home.name, threshold=75)
        with (
            mock.patch.object(window, "tmux", side_effect=fake_tmux),
            mock.patch.object(window, "screen", return_value=""),
            mock.patch.object(window, "window_idle", return_value=True),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            state = window.attach_window(args, home)
        with (
            mock.patch.object(window, "screen", return_value=""),
            mock.patch.object(time, "sleep", side_effect=StopWatch),
            contextlib.redirect_stdout(io.StringIO()),
            self.assertRaises(StopWatch),
        ):
            window.watch(args, home, state)
        return core.read(home / "window.json")

    def scene(self, **window_extra: Any) -> tuple[Path, Path]:
        home = self.task("queue", sessions=[], issue=139)
        fault = self.task("fault", sessions=[CODEX_SESSION], issue=133)
        self.starting_window(home, **window_extra)
        return home, fault

    def test_first_meter_attach_follows_active_issue_133_bind(self) -> None:
        for name, extra in {"no key": {}, "stale": {"active_task": "queue"}}.items():
            with self.subTest(name):
                self.fresh_scene()
                home, fault = self.scene(**extra)
                self.hook_event(CODEX_SESSION)
                self.assertEqual(
                    core.read(home / "meter.json")["session_id"], CODEX_SESSION
                )

                saved = self.attach_and_watch_once(home)

                self.assertEqual(saved["active_task"], "fault")
                self.assertEqual(saved["previous_task"], "queue")
                binding = core.read(fault / "binding.json")
                self.assertIn(
                    "restore --task fault --offline",
                    window.restore_command(saved, binding),
                )
                self.assertIn("issues/133", window.task_context(saved, binding))

    def test_without_first_meter_the_window_keeps_its_old_home_task(self) -> None:
        home = self.task("queue", sessions=[], issue=139)
        self.task(
            "fault", sessions=[], issue=133
        )  # 현재 session은 어느 task에도 묶이지 않음
        self.starting_window(home)
        self.hook_event(CODEX_SESSION)

        saved = self.attach_and_watch_once(home)

        self.assertFalse((home / "meter.json").exists())
        self.assertEqual(saved["active_task"], "queue")
        self.assertNotIn("previous_task", saved)

    def test_follow_task_adopts_session_bind_when_window_has_no_active_task(
        self,
    ) -> None:
        home, _ = self.scene()
        state = core.read(home / "window.json")

        with contextlib.redirect_stdout(io.StringIO()):
            changed = window.follow_task(home, state, CODEX_SESSION)

        self.assertTrue(changed)
        self.assertEqual(state["active_task"], "fault")
        self.assertIsNone(state["previous_task"])

    def test_hook_leaves_window_record_untouched_and_records_minimal_meter(
        self,
    ) -> None:
        home, _ = self.scene()
        before = (home / "window.json").read_bytes()

        self.hook_event(CODEX_SESSION)

        self.assertEqual((home / "window.json").read_bytes(), before)
        self.assertEqual(
            set(core.read(home / "meter.json")),
            {"host", "session_id", "transcript_path", "percent", "at"},
        )

    def test_hook_rejects_unregistered_duplicate_and_untrusted_windows(self) -> None:
        def unregistered() -> None:
            self.task("queue", sessions=[], issue=139)
            self.task("fault", sessions=[], issue=133)
            self.starting_window(self.root / "queue")

        def duplicate() -> None:
            self.task("queue", sessions=[CODEX_SESSION], issue=139)
            self.task("fault", sessions=[CODEX_SESSION], issue=133)
            self.starting_window(self.root / "queue")

        def other_pane() -> None:
            self.scene()
            os.environ["TMUX_PANE"] = "%99"

        def other_host() -> None:
            home, _ = self.scene()
            write(
                home / "window.json",
                {**core.read(home / "window.json"), "host": "claude"},
            )

        def other_identity() -> None:
            self.scene()
            self.pane_identity_mock.return_value = "%7|2|@2"

        cases = {
            "unregistered": unregistered,
            "duplicate bind": duplicate,
            "other pane": other_pane,
            "other host": other_host,
            "identity mismatch": other_identity,
        }
        for name, build in cases.items():
            with self.subTest(name):
                self.fresh_scene()
                build()
                self.hook_event(CODEX_SESSION)
                self.assertFalse((self.root / "queue" / "meter.json").exists())


class CodexRecordTest(RoutingCase):
    """훅이 검증된 Codex 관리 창의 묶인 session만 최소 metadata로 기록하는지 확인한다."""

    def codex_window(self, *, sessions: list[str], phase: str = "running") -> Path:
        home = self.task("old", sessions=sessions, issue=1)
        self.managed(home, "old", phase=phase)
        state = core.read(home / "window.json")
        write(home / "window.json", {**state, "host": "codex"})
        return home

    def event(self, session: str, name: str = "UserPromptSubmit") -> dict[str, Any]:
        return {**self.payload(session, name), "transcript_path": "/rollout.jsonl"}

    def test_codex_hook_records_only_minimal_metadata_for_bound_session(self) -> None:
        home = self.codex_window(sessions=[NEW])

        hook.handle_continuity("codex", self.event(NEW), self.root)

        meter = core.read(home / "meter.json")
        self.assertEqual(
            set(meter), {"host", "session_id", "transcript_path", "percent", "at"}
        )
        self.assertEqual(
            (meter["session_id"], meter["transcript_path"]), (NEW, "/rollout.jsonl")
        )

    def test_codex_hook_does_not_record_unbound_nested_session(self) -> None:
        home = self.codex_window(sessions=[NEW])

        hook.handle_continuity("codex", self.event(CLEARED), self.root)

        self.assertFalse((home / "meter.json").exists())

    def test_codex_hook_records_new_session_linked_during_clear(self) -> None:
        home = self.codex_window(sessions=[OLD], phase="clearing")

        hook.handle_continuity("codex", self.event(CLEARED, "SessionStart"), self.root)

        self.assertEqual(core.read(home / "meter.json")["session_id"], CLEARED)

    def test_codex_hook_records_nothing_in_claude_window(self) -> None:
        home = self.task("old", sessions=[NEW], issue=1)
        self.managed(home, "old")

        hook.handle_continuity("codex", self.event(NEW), self.root)

        self.assertFalse((home / "meter.json").exists())

    def test_post_compact_keeps_codex_record_fields(self) -> None:
        home = self.codex_window(sessions=[NEW])

        hook.handle_continuity("codex", self.event(NEW, "PostCompact"), self.root)

        meter = core.read(home / "meter.json")
        self.assertEqual(meter["host"], "codex")
        self.assertEqual(meter["transcript_path"], "/rollout.jsonl")
        self.assertIsNone(meter["percent"])


if __name__ == "__main__":
    unittest.main()
