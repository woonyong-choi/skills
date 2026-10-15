"""#68: 저장 주장 대신 실제 상태 대조, 비공개 원래 요청·마지막 대화 복구, SessionStart 주입 안정성과 캐시 측정."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

PLUGIN = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(PLUGIN / "scripts"))

import continuity as core  # noqa: E402
import continuity_hook as hook  # noqa: E402

SESSION = "44444444-4444-4444-8444-444444444444"
DATA = {key: "fixture " + key for key in core.FIELDS}
SCOPE = {"criteria": ["c"], "stage": "s", "relation": "continue", "covers": [1], "reason": "r", "boundary": "b"}


class Case(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.base)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.root = self.base / "records"
        self.folder = self.root / "task"
        self.binding = {
            "repo": str(self.repo),
            "remote": "owner/repo",
            "issue": 1,
            "url": "https://example.invalid/issues/1",
            "session_ids": [SESSION],
        }
        core.save(self.folder / "binding.json", self.binding)
        environ = mock.patch.dict(
            os.environ, {"WORK_CONTINUITY_CONFIG_DIR": str(self.base / "configuration")}
        )
        environ.start()
        self.addCleanup(environ.stop)
        for key in ("WOON_KNOWLEDGE_ROOT", "ISSUE_CONTINUITY_TASK", "ISSUE_CONTINUITY_WINDOW"):
            os.environ.pop(key, None)

    def state(self, *, synced: bool, saved_at: int | None = None, digest: str | None = None) -> dict:
        signed = core.signature(DATA, SCOPE)
        record = {"id": "a" * 32, "parent": None, "digest": digest or signed, "data": DATA, "scope": SCOPE}
        state = {
            "data": DATA,
            "scope": SCOPE,
            "saved_at": saved_at or time.time_ns(),
            **(
                {"pending": None, "sync": "synced", "remote_id": record["id"], "remote_verified": signed}
                if synced
                else {"pending": record, "sync": "pending"}
            ),
        }
        core.save(self.folder / "checkpoint.json", state)
        return record

    def event(self, name: str, host: str = "claude", **extra: object) -> dict:
        payload = {"hook_event_name": name, "session_id": SESSION, "cwd": str(self.repo), **extra}
        return hook.handle_continuity(host, payload, self.root)


class ReadBackTest(Case):
    def test_save_rejects_differing_read_back(self) -> None:
        with mock.patch.object(core, "read", return_value={"other": 1}):
            with self.assertRaisesRegex(core.ContinuityError, "read-back"):
                core.save(self.base / "x.json", {"value": 1})

    def test_verify_checkpoint_compares_actual_files(self) -> None:
        with self.assertRaisesRegex(core.ContinuityError, "not persisted"):
            core.verify_checkpoint(self.folder)
        record = self.state(synced=False)
        self.assertEqual(core.verify_checkpoint(self.folder)["remote"], "pending")
        with self.assertRaisesRegex(core.ContinuityError, "not synced"):
            core.verify_checkpoint(self.folder, synced=True)
        with self.assertRaisesRegex(core.ContinuityError, "during this request"):
            core.verify_checkpoint(self.folder, since=time.time_ns() + 10**9)
        self.state(synced=False, digest="0" * 64)
        with self.assertRaisesRegex(core.ContinuityError, "pending record"):
            core.verify_checkpoint(self.folder)
        self.state(synced=True)
        self.assertEqual(core.verify_checkpoint(self.folder, [record], synced=True)["remote"], "verified")
        for records in ([], [{**record, "digest": "0" * 64}]):
            with self.assertRaisesRegex(core.ContinuityError, "read-back"):
                core.verify_checkpoint(self.folder, records, synced=True)

    def test_sync_requires_published_record_on_read_back(self) -> None:
        record = self.state(synced=False)
        state = core.read(self.folder / "checkpoint.json")
        posted: list[str] = []

        def run(args: list[str], payload: str | None = None, cwd: str | None = None) -> str:
            posted.append(payload or "")
            return "{}"

        core.remember(self.folder, str(self.repo), prompt="secret original request", origin={})
        with mock.patch.object(core, "run", side_effect=run), mock.patch.object(core, "remote_records", return_value=[]):
            with self.assertRaisesRegex(core.ContinuityError, "not found on read-back"):
                core.sync(self.folder, state, self.binding)
        self.assertEqual(core.read(self.folder / "checkpoint.json")["sync"], "pending")
        self.assertFalse(any("secret original request" in body for body in posted))
        published = {**record, "url": "https://example.invalid/c"}
        with mock.patch.object(core, "run", side_effect=run), mock.patch.object(core, "remote_records", side_effect=[[], [published]]):
            result = core.sync(self.folder, state, self.binding)
        self.assertEqual(result["verified"]["remote"], "verified")
        saved = core.read(self.folder / "checkpoint.json")
        self.assertEqual((saved["sync"], saved["remote_verified"]), ("synced", record["digest"]))
        self.assertNotIn("verified", saved)


class RestoreTest(Case):
    def restore(self, remote: dict, **options: bool) -> dict:
        snap = {"head": "h", "branch": "b"}
        with mock.patch.object(core, "remote_records", return_value=[remote]), mock.patch.object(core, "run", return_value='{"state": "open"}'), mock.patch.object(core, "snapshot", return_value=snap):
            return core.restore(self.folder, self.binding, False, **options)

    def test_conversation_fixed_after_issue_and_verify_clear_reads_back(self) -> None:
        record = self.state(synced=True)
        state = core.read(self.folder / "checkpoint.json")
        core.save(self.folder / "checkpoint.json", {**state, "snapshot": {"head": "h", "branch": "b"}})
        self.event("UserPromptSubmit", prompt="원래 요청")
        remote = {**record, "url": "https://example.invalid/c"}
        result = self.restore(remote, verify_clear=True)
        keys = list(result)
        self.assertEqual(keys.index("conversation"), keys.index("issue") + 1)
        self.assertEqual(result["conversation"]["original_request"], "원래 요청")
        with self.assertRaisesRegex(core.ContinuityError, "clear not ready"):
            self.restore({**remote, "scope": {**SCOPE, "stage": "other"}}, verify_clear=True)
        core.save(self.folder / "checkpoint.json", {**core.read(self.folder / "checkpoint.json"), "remote_verified": "0" * 64})
        with self.assertRaisesRegex(core.ContinuityError, "clear not ready: synced checkpoint differs"):
            self.restore(remote, verify_clear=True)


class StopClaimTest(Case):
    def claim(self, command: str) -> None:
        self.event("UserPromptSubmit", prompt="작업 요청")
        self.event("PostToolUse", tool_name="Bash", tool_input={"command": command})

    def test_unpersisted_claim_blocks_once(self) -> None:
        self.claim("python3 scripts/continuity.py --root r checkpoint --task task --input x.json --sync")
        first = self.event("Stop", last_assistant_message="checkpoint 저장 완료")
        self.assertEqual(first["decision"], "block")
        self.assertIn("checkpoint not persisted", first["reason"])
        self.assertEqual(self.event("Stop"), {})
        self.claim("python3 continuity.py checkpoint --task task --input x.json --sync")
        self.assertEqual(self.event("Stop", stop_hook_active=True), {})

    def test_pending_sync_claim_blocks_and_persisted_passes(self) -> None:
        self.claim("python3 continuity.py checkpoint --task task --input x.json --sync")
        self.state(synced=False)
        self.assertIn("not synced", self.event("Stop")["reason"])
        self.claim("python3 continuity.py checkpoint --task task --input x.json --sync")
        self.state(synced=True)
        self.assertEqual(self.event("Stop"), {})
        self.claim("python3 continuity.py checkpoint --task task --input x.json")
        self.state(synced=False)
        self.assertEqual(self.event("Stop"), {})  # 로컬 저장만 주장, 실제 로컬 저장 확인

    def test_codex_list_command_and_stale_checkpoint(self) -> None:
        self.state(synced=True, saved_at=1)
        self.event("UserPromptSubmit", "codex", prompt="요청")
        self.event("PostToolUse", "codex", tool_name="exec_command", tool_input={"cmd": ["bash", "-lc", "python3 continuity.py checkpoint --task task --input x.json"]})
        self.assertIn("during this request", self.event("Stop", "codex")["reason"])

    def test_session_start_reports_unverified_state_stably(self) -> None:
        self.state(synced=False)
        texts = {self.event("SessionStart", source="compact")["hookSpecificOutput"]["additionalContext"] for _ in range(2)}
        self.assertEqual(len(texts), 1)
        self.assertIn("저장 상태 대조 실패: checkpoint not synced", texts.pop())
        self.event("SessionEnd")
        state = next(core.read(path) for path in self.folder.glob("session-*.json"))
        self.assertEqual(state["end_check"], "verified")


class ExchangeTest(Case):
    def test_original_request_and_last_exchange_restore(self) -> None:
        self.event("UserPromptSubmit", prompt="원래 요청: 로그인 오류 수정")
        self.event("UserPromptSubmit", prompt="이어서 테스트 추가")
        self.event("Stop", last_assistant_message="테스트를 추가했습니다.")
        result = core.conversation(self.folder, self.binding)
        self.assertEqual(result["original_request"], "원래 요청: 로그인 오류 수정")
        self.assertEqual(result["last_exchange"], {"user": "이어서 테스트 추가", "assistant": "테스트를 추가했습니다."})
        self.assertEqual(os.stat(self.folder / core.EXCHANGE).st_mode & 0o777, 0o600)

    def test_truncation_marker_keeps_verbatim_prefix(self) -> None:
        text = "가" * 2000
        self.event("UserPromptSubmit", prompt=text)
        latest = core.read(self.folder / core.EXCHANGE)["latest_prompt"]["text"]
        self.assertTrue(latest.startswith("가" * 1333))
        self.assertTrue(latest.endswith("\n[truncated: kept 3999 of 6000 bytes]"))
        self.assertEqual(core.read(self.folder / core.EXCHANGE)["original"]["text"], text)
        self.assertEqual(core.clip("가" * 3000, core.ORIGINAL_LIMIT), "가" * 2666 + "\n[truncated: kept 7998 of 9000 bytes]")

    def test_last_turn_per_host_adapter(self) -> None:
        last = ("고쳐줘", "수정했습니다. 테스트 통과.")
        self.assertEqual(core.last_turn(str(FIXTURES / "claude-transcript.jsonl"), "claude"), last)
        self.assertEqual(core.last_turn(str(FIXTURES / "codex-rollout.jsonl"), "codex"), last)
        # 호스트가 다르면 다른 형식의 줄을 해석하지 않는다
        self.assertEqual(core.last_turn(str(FIXTURES / "codex-rollout.jsonl"), "claude"), (None, None))
        with self.assertRaises(core.ContinuityError):
            core.last_turn("relative.jsonl", "claude")

    def test_claude_stop_uses_transcript_path(self) -> None:
        self.event("Stop", transcript_path=str(FIXTURES / "claude-transcript.jsonl"))
        result = core.conversation(self.folder, self.binding)
        self.assertEqual(result["last_exchange"], {"user": "고쳐줘", "assistant": "수정했습니다. 테스트 통과."})

    def test_codex_stop_with_and_without_transcript_path(self) -> None:
        self.event("Stop", "codex", transcript_path=str(FIXTURES / "codex-rollout.jsonl"))
        self.assertEqual(core.conversation(self.folder, self.binding)["original_request"], "고쳐줘")
        (self.folder / core.EXCHANGE).unlink()
        os.environ["CODEX_HOME"] = str(self.base / "codex")
        self.addCleanup(os.environ.pop, "CODEX_HOME", None)
        day = self.base / "codex/sessions/2026/10/15"
        day.mkdir(parents=True)
        self.event("Stop", "codex")  # rollout 없음: 오류 없이 저장 생략
        self.assertFalse((self.folder / core.EXCHANGE).exists())
        rollout = day / f"rollout-2026-10-15T01-00-00-{SESSION}.jsonl"
        shutil.copy(FIXTURES / "codex-rollout.jsonl", rollout)
        self.assertEqual(core.HOSTS["codex"].locate({"session_id": SESSION}), str(rollout.resolve()))
        self.assertIsNone(core.HOSTS["claude"].locate({"session_id": SESSION}))
        self.event("Stop", "codex")
        result = core.conversation(self.folder, self.binding)
        self.assertEqual(result["last_exchange"], {"user": "고쳐줘", "assistant": "수정했습니다. 테스트 통과."})
        self.event("Stop", "codex", last_assistant_message="훅 응답")  # payload 응답 우선
        self.assertEqual(core.conversation(self.folder, self.binding)["last_exchange"]["assistant"], "훅 응답")

    def test_codex_rollout_lookup_rejects_unverified_candidates(self) -> None:
        os.environ["CODEX_HOME"] = str(self.base / "codex")
        self.addCleanup(os.environ.pop, "CODEX_HOME", None)
        day = self.base / "codex/sessions/2026/10/15"
        day.mkdir(parents=True)
        other = "55555555-5555-4555-8555-555555555555"
        (day / f"rollout-a-{SESSION}.jsonl").write_text(
            (FIXTURES / "codex-rollout.jsonl").read_text().replace(SESSION, other)
        )
        self.assertIsNone(core.codex_rollout(SESSION), "session_meta ID mismatch")
        (day / f"rollout-a-{SESSION}.jsonl").unlink()
        (day / f"rollout-b-{SESSION}.jsonl").symlink_to(FIXTURES / "codex-rollout.jsonl")
        self.assertIsNone(core.codex_rollout(SESSION), "symlink")
        for name in ("c", "d"):
            shutil.copy(FIXTURES / "codex-rollout.jsonl", day / f"rollout-{name}-{SESSION}.jsonl")
        self.assertIsNone(core.codex_rollout(SESSION), "ambiguous")
        self.assertIsNone(core.codex_rollout("../" + SESSION))

    def test_prompt_before_bind_becomes_original(self) -> None:
        core.save(self.folder / "binding.json", {**self.binding, "session_ids": []})
        self.event("UserPromptSubmit", prompt="bind 전 원래 요청")  # 저장소 추정 연결만 있는 세션
        self.assertEqual(len(list((self.root / ".prompts").iterdir())), 1)
        self.assertFalse((self.folder / core.EXCHANGE).exists())
        core.save(self.folder / "binding.json", self.binding)
        self.event("PostToolUse", tool_name="Bash", tool_input={"command": "python3 continuity.py bind --task task"})
        self.event("Stop", last_assistant_message="연결 완료")
        result = core.conversation(self.folder, self.binding)
        self.assertEqual(result["original_request"], "bind 전 원래 요청")
        self.assertEqual(result["last_exchange"]["user"], "bind 전 원래 요청")
        self.assertEqual(list((self.root / ".prompts").iterdir()), [])

    def test_record_root_inside_working_tree_or_vault_stores_nothing(self) -> None:
        inside = self.repo / ".records"
        core.save(inside / "task/binding.json", self.binding)
        hook.handle_continuity("claude", {"hook_event_name": "UserPromptSubmit", "session_id": SESSION, "cwd": str(self.repo), "prompt": "비공개"}, inside)
        self.assertFalse((inside / "task" / core.EXCHANGE).exists())
        self.assertIn("unavailable", core.conversation(inside / "task", self.binding))
        os.environ["WOON_KNOWLEDGE_ROOT"] = str(self.base)
        self.assertTrue(core.private_problem(self.folder, str(self.repo)))


class SessionStartStabilityTest(Case):
    def run_hook(self, payload: dict) -> bytes:
        result = subprocess.run(
            [sys.executable, str(PLUGIN / "scripts/continuity_hook.py"), "claude"],
            input=json.dumps(payload).encode(), capture_output=True, timeout=30,
            env={**os.environ, "ISSUE_CONTINUITY_ROOT": str(self.root)},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(result.stderr, result.stderr)
        return result.stdout

    def test_same_state_injects_identical_bytes(self) -> None:
        self.state(synced=False)
        payload = {"hook_event_name": "SessionStart", "session_id": SESSION, "cwd": str(self.repo), "source": "startup"}
        first = self.run_hook(payload)
        self.run_hook({**payload, "hook_event_name": "UserPromptSubmit", "prompt": "중간 요청"})
        second = self.run_hook(payload)
        self.assertEqual(first, second)
        self.assertIn("additionalContext", json.loads(first)["hookSpecificOutput"])


def claude_turn(message: str, read: int, created: int, uncached: int = 10) -> dict:
    usage = {"input_tokens": uncached, "cache_read_input_tokens": read, "cache_creation_input_tokens": created, "output_tokens": 5}
    return {"type": "assistant", "sessionId": "s1", "message": {"id": message, "usage": usage, "content": [{"type": "text", "text": "본문"}]}}


class CacheReportTest(Case):
    def write(self, name: str, rows: list[dict]) -> str:
        path = self.base / name
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
        return str(path)

    def cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(PLUGIN / "scripts/continuity.py"), "cache-report", *args], capture_output=True, text=True, timeout=30)

    def test_claude_fixture_boundaries_dedupe_and_spikes(self) -> None:
        report = core.cache_report(str(FIXTURES / "claude-transcript.jsonl"))
        self.assertEqual(report["host"], "claude")
        self.assertEqual(report["spike_metric"], "cache_creation")
        self.assertEqual(
            [(t["input"], t["cache_read"], t["cache_creation"], t["boundary"]) for t in report["turns"]],
            [(3, 0, 18000, "start"), (4, 18000, 600, None), (4, 18600, 400, None), (4, 3000, 15000, "compact")],
        )
        self.assertEqual(report["summary"]["boundary_spikes"], [1, 4])
        self.assertEqual(report["summary"]["other_spikes"], [])
        self.assertEqual(report["turns"][1]["read_ratio"], round(18000 / 18604, 4))
        self.assertEqual(report["summary"]["cache_creation"], 34000)
        self.assertNotIn("본문", json.dumps(report, ensure_ascii=False))
        self.assertNotIn("cached_input", report["summary"])

    def test_claude_session_change_is_start(self) -> None:
        path = self.write("c.jsonl", [
            claude_turn("m1", 0, 20000), claude_turn("m2", 20000, 300),
            {**claude_turn("m3", 0, 20000), "sessionId": "s2"},
        ])
        self.assertEqual([t["boundary"] for t in core.cache_report(path)["turns"]], ["start", None, "start"])

    def test_codex_fixture_reports_codex_metrics(self) -> None:
        path = str(FIXTURES / "codex-rollout.jsonl")
        for args in (("--transcript", path), ("--transcript", path, "--host", "codex")):
            result = self.cli(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["host"], "codex")
            self.assertEqual(report["spike_metric"], "uncached_input")
            self.assertEqual(
                [(t["input"], t["cached_input"], t["uncached_input"], t["boundary"]) for t in report["turns"]],
                [(9000, 0, 9000, "start"), (9500, 9000, 500, None), (4000, 0, 4000, "compact")],
            )
            self.assertNotIn("cache_creation", json.dumps(report))
            self.assertEqual(report["turns"][1]["read_ratio"], round(9000 / 9500, 4))
            self.assertEqual(report["summary"]["boundary_spikes"], [1, 3])
            self.assertEqual(report["summary"]["read_ratio"], round(9000 / 22500, 4))
            self.assertNotIn("세션 만료", result.stdout)

    def test_explicit_host_and_unknown_content(self) -> None:
        mismatched = self.cli("--transcript", str(FIXTURES / "codex-rollout.jsonl"), "--host", "claude")
        self.assertEqual(json.loads(mismatched.stdout)["summary"]["turns"], 0)
        unknown = self.write("u.jsonl", [{"type": "other"}])
        self.assertEqual(self.cli("--transcript", unknown).returncode, 2)
        self.assertEqual(self.cli("--transcript", str(self.base / "absent.jsonl")).returncode, 2)
        self.assertEqual(self.cli("--transcript", unknown, "--host", "other").returncode, 2)

if __name__ == "__main__":
    unittest.main()
