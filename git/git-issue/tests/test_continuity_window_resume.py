"""skills#53: 복구 입력 뒤 관리 창 감시 회귀 검사.

가짜 tmux 화면과 가짜 시계로 정상 작업(busy)과 사람 입력 대기·정지·식별 불일치를 구분하는지 확인한다.
실제 창에서의 자동 복구 시험은 이 파일의 범위 밖이다.
"""

from __future__ import annotations

import contextlib
import io
import json
import time
from typing import Any, Callable
import unittest
from unittest import mock

import test_continuity_routing as base

core = base.core
window = base.window

IDLE = "작업 결과\n❯ \n"
TRUST = "Do you trust this folder?\n1. Yes, I trust this folder\n❯ \n"
PERMISSION = "Do you want to proceed?\n❯ 1. Yes\n"
LOGIN = "Invalid API key · Please run /login\n❯ \n"


def busy(tick: int) -> str:
    """진행 시간이 매번 바뀌는 정상 작업 화면"""
    return f"작업 로그\n· Thinking… ({tick}s · ↓ 1.2k tokens · esc to interrupt)\n❯ \n"


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class ResumeWatchTest(base.RoutingCase):
    def args(self, **values: object) -> mock.Mock:
        return mock.Mock(task="old", host="claude", title="t", **values)

    def prepare(self) -> tuple[Any, dict[str, Any]]:
        home = self.task("old", sessions=[base.OLD, base.CLEARED], issue=1)
        state = {
            **self.state(home, "old"),
            "phase": "resuming",
            "new_session": base.CLEARED,
            "resume_input_at": 1.0,
            "activity": "input_delivered",
        }
        base.write(home / "window.json", state)
        base.write(
            home / "meter.json",
            {"percent": 10, "session_id": base.CLEARED, "at": time.time() + 10_000},
        )
        return home, state

    def watch(
        self,
        screens: Callable[[float], str],
        *,
        identity: str = base.IDENTITY,
        title: str = "t",
        session: str = base.CLEARED,
        gone: bool = False,
        args: mock.Mock | None = None,
    ) -> tuple[dict[str, Any], mock.Mock, Clock, core.ContinuityError | None]:
        home, state = self.prepare()
        base.write(
            home / "meter.json",
            {"percent": 10, "session_id": session, "at": time.time() + 10_000},
        )
        clock = Clock()
        start = clock.now
        send = mock.Mock()

        def fake_tmux(*call: str) -> str:
            if gone:
                raise core.ContinuityError("tmux failed")
            if "#{cursor_x}" in call:
                return "2"
            return title if "#{pane_title}" in call else identity

        error: core.ContinuityError | None = None
        with (
            mock.patch.object(window, "tmux", side_effect=fake_tmux),
            mock.patch.object(
                window, "screen", side_effect=lambda pane: screens(clock.now - start)
            ),
            mock.patch.object(window, "send", send),
            mock.patch.object(window.time, "monotonic", clock.monotonic),
            mock.patch.object(window.time, "sleep", clock.sleep),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            try:
                window.finish_resume(args or self.args(), home, state)
            except core.ContinuityError as caught:
                error = caught
        return core.read(home / "window.json"), send, clock, error

    def test_long_normal_work_is_watched_without_input_until_idle(self) -> None:
        long_work = 3 * 3600
        saved, send, clock, error = self.watch(
            lambda t: busy(int(t)) if t < long_work else IDLE
        )

        self.assertIsNone(error)
        send.assert_not_called()
        self.assertGreater(clock.now - 1000.0, long_work)
        self.assertEqual(saved["phase"], "resumed")
        self.assertEqual(saved["activity"], "idle_confirmed")
        self.assertIn("working_since", saved)
        self.assertIn("idle_confirmed_at", saved)
        self.assertEqual(saved["resume_input_at"], 1.0)

    def test_idle_needs_stable_observation_after_resume_input(self) -> None:
        saved, send, clock, error = self.watch(lambda t: IDLE)

        self.assertIsNone(error)
        send.assert_not_called()
        self.assertGreaterEqual(clock.now - 1000.0, window.RESUME_MIN_IDLE_SECONDS)
        self.assertEqual(saved["phase"], "resumed")

    def test_each_attention_screen_blocks_with_its_reason_and_no_input(self) -> None:
        for label, screen in (
            ("trust", TRUST),
            ("permission", PERMISSION),
            ("authentication", LOGIN),
        ):
            saved, send, _, error = self.watch(lambda t, s=screen: s)
            self.assertIsInstance(error, core.ContinuityError, label)
            self.assertIn("(attention)", str(error))
            self.assertIn(label, str(error))
            send.assert_not_called()

    def test_attention_wording_in_old_conversation_text_is_not_a_prompt(self) -> None:
        quoted = "API Error: 401 인용 문구\n" + "\n".join(f"줄 {n}" for n in range(60))
        saved, send, _, error = self.watch(
            lambda t: quoted + "\n" + (busy(int(t)) if t < 30 else IDLE)
        )

        self.assertIsNone(error)
        send.assert_not_called()
        self.assertEqual(saved["phase"], "resumed")

    def test_identity_title_session_and_process_loss_block_explicitly(self) -> None:
        cases = (
            ("(identity)", {"identity": "%8|1|@1"}),
            ("(title)", {"title": "다른 제목"}),
            ("(session)", {"session": base.NEW}),
            ("(process)", {"gone": True}),
        )
        for marker, kwargs in cases:
            saved, send, _, error = self.watch(lambda t: busy(int(t)), **kwargs)
            self.assertIsInstance(error, core.ContinuityError, marker)
            self.assertIn(marker, str(error))
            send.assert_not_called()

    def test_frozen_screen_blocks_but_changing_busy_screen_does_not(self) -> None:
        frozen = busy(5)
        _, send, clock, error = self.watch(lambda t: frozen)
        self.assertIn("(stalled)", str(error))
        self.assertGreaterEqual(clock.now - 1000.0, window.RESUME_STALL_SECONDS)
        send.assert_not_called()

        draft = "❯ 보내지 않은 입력\n"
        _, send, _, error = self.watch(lambda t: draft)
        self.assertIn("(stalled)", str(error))
        self.assertIn("prompt has text", str(error))
        send.assert_not_called()

        _, send, _, error = self.watch(
            lambda t: busy(int(t)) if t < 2 * window.RESUME_STALL_SECONDS else IDLE
        )
        self.assertIsNone(error)

    def test_screen_state_separates_busy_idle_attention_and_unknown(self) -> None:
        self.assertEqual(window.screen_state(busy(3), "claude", 2)[0], "busy")
        self.assertEqual(window.screen_state(IDLE, "claude", 2)[0], "idle")
        self.assertEqual(window.screen_state(TRUST, "claude", 2), ("attention", "trust"))
        self.assertEqual(window.screen_state("❯ 입력\n", "claude", 2)[0], "unknown")
        self.assertEqual(
            window.screen_state("› Ask Codex to do anything\n", "codex")[0], "idle"
        )
        self.assertEqual(
            window.screen_state("• Working (3s • esc to interrupt)\n› \n", "codex")[0],
            "busy",
        )

    def test_background_shell_is_busy_until_its_footer_disappears(self) -> None:
        for footer in ("1 shell still running", "⏵⏵ bypass permissions on · 1 shell"):
            screen = f"작업 로그\n❯ \n{footer}\n"
            self.assertEqual(window.screen_state(screen, "claude", 2)[0], "busy", footer)
            self.assertFalse(window.idle(screen, "claude", 2), footer)
        self.assertEqual(window.screen_state(IDLE, "claude", 2)[0], "idle")

        def with_background(tick: int) -> str:
            return f"작업 로그 {tick}\n❯ \n1 shell still running\n"

        saved, send, clock, error = self.watch(
            lambda t: with_background(int(t)) if t < 210 else IDLE
        )
        self.assertIsNone(error)
        send.assert_not_called()
        self.assertGreater(clock.now - 1000.0, 210)
        self.assertEqual(saved["phase"], "resumed")
        self.assertEqual(saved["activity"], "idle_confirmed")

    def test_finish_reset_sends_resume_input_once_then_only_watches(self) -> None:
        home = self.task("old", sessions=[base.OLD], issue=1)
        base.write(home / "checkpoint.json", {"remote_id": "r1"})
        state = {
            **self.state(home, "old"),
            "old_session": base.OLD,
            "checkpoint": "r1",
            "checkpoint_task": "old",
        }
        base.os.environ["ISSUE_CONTINUITY_ROOT"] = str(self.root)
        send = mock.Mock()
        finish = mock.Mock()
        with (
            mock.patch.object(window, "tmux", return_value="t"),
            mock.patch.object(window, "confirm_new_session", return_value=base.CLEARED),
            mock.patch.object(window, "finish_resume", finish),
            mock.patch.object(window, "send", send),
            mock.patch.object(window.time, "sleep"),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            window.finish_reset(self.args(), home, state)

        self.assertEqual(send.call_count, 1)
        finish.assert_called_once()
        saved = core.read(home / "window.json")
        self.assertEqual(saved["activity"], "input_delivered")
        self.assertIn("resume_input_at", saved)

    def test_recover_after_resume_block_watches_without_clear_or_input(self) -> None:
        home = self.task("old", sessions=[base.OLD, base.CLEARED], issue=1)
        base.write(home / "checkpoint.json", {"remote_id": "r1"})
        base.os.environ["ISSUE_CONTINUITY_ROOT"] = str(self.root)
        blocked = {
            **self.state(home, "old"),
            "phase": "blocked",
            "failed_phase": "resuming",
            "error": "window not idle; no reset or duplicate input sent",
            "checkpoint": "r1",
            "new_session": base.CLEARED,
            "resume_input_at": 5.0,
        }
        send = mock.Mock()
        finish = mock.Mock()
        reset = mock.Mock()
        with (
            mock.patch.object(window, "tmux", return_value=base.IDENTITY),
            mock.patch.object(window, "send", send),
            mock.patch.object(window, "finish_resume", finish),
            mock.patch.object(window, "finish_reset", reset),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            window.recover_window(self.args(), home, blocked)

        finish.assert_called_once()
        reset.assert_not_called()
        send.assert_not_called()

        for label, change in (
            ("no input record", {"resume_input_at": None}),
            ("resumed already", {"phase": "resumed", "failed_phase": None}),
            ("identity", {"identity": "%8|1|@1"}),
        ):
            state = {**blocked, **change}
            finish.reset_mock()
            with (
                mock.patch.object(window, "tmux", return_value=base.IDENTITY),
                mock.patch.object(window, "send", send),
                mock.patch.object(window, "finish_resume", finish),
                mock.patch.object(window, "finish_reset", reset),
            ):
                with self.assertRaises(core.ContinuityError, msg=label):
                    window.recover_window(self.args(), home, state)
            finish.assert_not_called()
            send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
