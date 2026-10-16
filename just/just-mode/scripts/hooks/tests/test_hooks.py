"""just do 훅: 진입 안내, 결정 기록 확인, 편집 전 규칙 확인, 진입점·매니페스트 계약.

모든 시험은 임시 git 저장소와 임시 설정 폴더만 쓴다.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HOOKS = Path(__file__).resolve().parents[1]
PLUGIN = HOOKS.parents[2]
REPO = PLUGIN.parent
sys.path.insert(0, str(HOOKS))

import entry  # noqa: E402
import task  # noqa: E402

SESSION = "019e0000-0000-7000-8000-00000000abcd"
LOGGER = REPO / "just/show-me-your-work/scripts/log.sh"


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, timeout=15)


class HookCase(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.base)
        self.repo = self.base / "work"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        (self.repo / "README.md").write_text("# work\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "init")
        self.env = {**os.environ, "SKILLS_CONFIG_DIR": str(self.base / "config")}
        for key in ("CAREER_ROOT", task.DEADLINE_ENV, "CODEX_THREAD_ID"):
            self.env.pop(key, None)

    def hook(self, event: str, host: str = "claude", **extra: object) -> dict:
        payload = {"hook_event_name": event, "session_id": SESSION, "cwd": str(self.repo), **extra}
        done = subprocess.run([sys.executable, str(HOOKS / "hook.py"), host], input=json.dumps(payload), capture_output=True, text=True, env=self.env, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stderr, "")
        return json.loads(done.stdout)

    def context(self, result: dict) -> str:
        return result.get("hookSpecificOutput", {}).get("additionalContext", "")

    def bind(self, name: str = "hooks-work", issue: str = "https://github.com/o/r/issues/7") -> dict:
        done = subprocess.run([sys.executable, str(HOOKS / "task.py"), "bind", "--session-id", SESSION, "--task", name, "--issue", issue, "--cwd", str(self.repo)], capture_output=True, text=True, env=self.env, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)

    def log(self, decision: str, name: str = "hooks-work") -> None:
        path = self.repo / ".local/decisions" / f"{name}.tsv"
        subprocess.run(["bash", str(LOGGER), str(path), "구현", decision, "이유", "근거", "통과"], check=True, timeout=15)


class EntryNoticeTest(HookCase):
    def test_session_start_is_one_line_outside_git(self) -> None:
        for host in ("claude", "codex"):
            payload = json.dumps({"hook_event_name": "SessionStart", "session_id": SESSION, "cwd": str(self.base)})
            done = subprocess.run([sys.executable, str(HOOKS / "hook.py"), host], input=payload, capture_output=True, text=True, env=self.env, timeout=30)
            text = json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"]
            self.assertEqual(text, f"코드를 바꾸는 개발 일이면 {HOOKS.parents[1] / 'SKILL.md'}를 읽고 그 순서로 진행한다.")
            self.assertNotIn("\n", text)

    def test_unbound_session_gets_bind_command_without_skill_body(self) -> None:
        text = self.context(self.hook("SessionStart"))
        lines = text.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("just-mode/SKILL.md를 읽고 그 순서로 진행한다", lines[0])
        self.assertIn(f"bind --session-id {SESSION}", lines[1])
        skill = (HOOKS.parents[1] / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn(skill.splitlines()[-1], text)

    def test_bound_session_gets_issue_and_last_five_decisions(self) -> None:
        bound = self.bind()
        self.assertEqual(bound["decisions"], str(self.repo / ".local/decisions/hooks-work.tsv"))
        for number in range(7):
            self.log(f"결정 {number}")
        text = self.context(self.hook("SessionStart", host="codex"))
        self.assertIn("연결 과업: hooks-work, 이슈 https://github.com/o/r/issues/7", text)
        self.assertEqual([number for number in range(7) if f"결정 {number}\t" in text], [2, 3, 4, 5, 6])

    def test_post_compact_reinjects_once_on_next_prompt(self) -> None:
        self.bind()
        self.log("첫 결정")
        start = self.context(self.hook("SessionStart"))
        self.assertEqual(self.context(self.hook("UserPromptSubmit", prompt="a")), "")
        self.assertEqual(self.hook("PostCompact"), {})
        self.assertEqual(self.context(self.hook("UserPromptSubmit", prompt="b")), start)
        self.assertEqual(self.context(self.hook("UserPromptSubmit", prompt="c")), "")

    def test_pre_compact_reports_stale_decision_log(self) -> None:
        self.bind()
        self.hook("UserPromptSubmit", prompt="a")
        stale = self.hook("PreCompact")
        self.assertIn("결정 기록에 새 줄이 없다", stale["systemMessage"])
        self.hook("PostCompact")
        self.assertIn("결정을 먼저 한 줄로 남긴다", self.context(self.hook("UserPromptSubmit", prompt="b")))
        self.log("이번 요청 결정")
        self.assertEqual(self.hook("PreCompact"), {})

    def test_local_folder_ignores_itself(self) -> None:
        self.hook("UserPromptSubmit", prompt="a")
        self.assertEqual((self.repo / ".local/.gitignore").read_text(encoding="utf-8"), "*\n")
        status = subprocess.run(["git", "-C", str(self.repo), "status", "--porcelain"], capture_output=True, text=True, timeout=15)
        self.assertEqual(status.stdout, "")


class StopTest(HookCase):
    def test_changed_files_without_decision_block_once(self) -> None:
        for bound in (False, True):
            with self.subTest(bound=bound):
                if bound:
                    self.bind()
                self.hook("UserPromptSubmit", prompt="고친다")
                (self.repo / f"note-{bound}.txt").write_text("x\n", encoding="utf-8")
                blocked = self.hook("Stop")
                self.assertEqual(blocked["decision"], "block")
                self.assertIn("log.sh", blocked["reason"])
                self.assertEqual(self.hook("Stop", stop_hook_active=True), {})
                self.assertEqual(self.hook("Stop"), {})

    def test_decision_line_or_no_change_passes(self) -> None:
        self.bind()
        self.hook("UserPromptSubmit", prompt="질문만")
        self.assertEqual(self.hook("Stop"), {})
        self.hook("UserPromptSubmit", prompt="고친다")
        (self.repo / "README.md").write_text("# changed\n", encoding="utf-8")
        self.log("README 수정")
        self.assertEqual(self.hook("Stop"), {})
        self.hook("UserPromptSubmit", prompt="계획 모드")
        (self.repo / "README.md").write_text("# plan\n", encoding="utf-8")
        self.assertEqual(self.hook("Stop", permission_mode="plan"), {})


class RuleGateTest(HookCase):
    def edit(self, **extra: object) -> dict:
        return self.hook("PreToolUse", tool_name="Write", tool_input={"file_path": str(self.repo / "app.py"), "content": "def run():\n    raise ValueError('x')\n"}, **extra)

    def test_unbound_git_session_denies_code_edit_until_rules_delivered(self) -> None:
        blocked = self.edit()["hookSpecificOutput"]
        self.assertEqual(blocked["permissionDecision"], "deny")
        command = blocked["permissionDecisionReason"].split("`")[1]
        self.assertIn("read_rules.py --pending", command)
        for _ in range(8):
            read = subprocess.run(shlex.split(command), capture_output=True, text=True, timeout=30)
            self.assertEqual(read.returncode, 0, read.stderr)
            self.hook("PostToolUse", tool_name="Bash", tool_input={"command": command}, tool_response={"stdout": read.stdout})
            if not self.edit():
                break
        else:
            self.fail("rule gate did not open after complete output")
        self.assertEqual(self.hook("PreToolUse", agent_id="worker", tool_name="Write", tool_input={"file_path": str(self.repo / "app.py"), "content": "x = 1\n"})["hookSpecificOutput"]["permissionDecision"], "deny")
        self.hook("PostCompact")
        self.assertEqual(self.edit()["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_reads_docs_and_outside_git_are_not_gated(self) -> None:
        self.assertEqual(self.hook("PreToolUse", tool_name="Bash", tool_input={"command": "ls"}), {})
        self.assertEqual(self.hook("PreToolUse", tool_name="Write", tool_input={"file_path": str(self.repo / "notes.md"), "content": "# x\n"}), {})
        payload = {"hook_event_name": "PreToolUse", "session_id": SESSION, "cwd": str(self.base), "tool_name": "Write", "tool_input": {"file_path": str(self.base / "a.py"), "content": "x = 1\n"}}
        done = subprocess.run([sys.executable, str(HOOKS / "hook.py"), "codex"], input=json.dumps(payload), capture_output=True, text=True, env=self.env, timeout=30)
        self.assertEqual(json.loads(done.stdout), {})

    def test_shell_patch_and_rule_query(self) -> None:
        patch = "apply_patch <<'EOF'\n*** Begin Patch\n*** Add File: tool.py\n+def run():\n+    return 1\n*** End Patch\nEOF"
        denied = self.hook("PreToolUse", host="codex", tool_name="Bash", tool_input={"command": patch})
        self.assertEqual(denied["hookSpecificOutput"]["permissionDecision"], "deny")
        reader = task.skill_file(task.RULE_READER)
        for arguments in ("app.py", "--ids CS-ERROR principle-fix-root-causes", "--ids=CS-ERROR"):
            rewritten = self.hook("PreToolUse", tool_name="Bash", tool_input={"command": f"python3 {reader} {arguments}"})
            self.assertIn("--pending", rewritten["hookSpecificOutput"]["updatedInput"]["command"], arguments)
        for arguments in ("--ids CS-NAEM", "notes.md", "--check", "app.py; touch x.py"):
            self.assertEqual(self.hook("PreToolUse", tool_name="Bash", tool_input={"command": f"python3 {reader} {arguments}"}), {}, arguments)

    def test_stop_blocks_once_after_edit_without_rules(self) -> None:
        self.hook("PostToolUse", tool_name="Edit", tool_input={"file_path": str(self.repo / "app.py"), "old_string": "a", "new_string": "b"}, tool_response="edited")
        blocked = self.hook("Stop")
        self.assertEqual(blocked["decision"], "block")
        self.assertIn("필수 규칙 원문", blocked["reason"])
        self.assertNotIn("필수 규칙 원문", self.hook("Stop").get("reason", ""))


class RuleMapTest(HookCase):
    """편집할 파일 종류·내용 → 원칙 파일, code-style 절, 언어별 스킬 대응(rule-map.json)."""

    def delivered(self, name: str, content: str) -> str:
        """훅 거부 → --pending 조회 반복 → 출력 기록으로 편집이 열릴 때까지 받은 원문 전체."""
        edit = {"tool_name": "Write", "tool_input": {"file_path": str(self.repo / name), "content": content}}
        blocked = self.hook("PreToolUse", **edit)["hookSpecificOutput"]
        self.assertEqual(blocked["permissionDecision"], "deny")
        command = blocked["permissionDecisionReason"].split("`")[1]
        output = ""
        for _ in range(10):
            read = subprocess.run(shlex.split(command), capture_output=True, text=True, timeout=30, check=False)
            self.assertEqual(read.returncode, 0, read.stderr)
            output += read.stdout
            self.hook("PostToolUse", tool_name="Bash", tool_input={"command": command}, tool_response={"stdout": read.stdout})
            if not self.hook("PreToolUse", **edit):
                return output
        self.fail("rule gate did not open")

    def test_typescript_edit_gets_typescript_section_and_type_principles(self) -> None:
        output = self.delivered("a.ts", "export type State = { kind: 'idle' };\n")
        for text in ("<!-- code-style-typescript | code-style-typescript/SKILL.md -->", "## TypeScript 전용", "npx tsc --noEmit", "# 타입 시스템 규율", "# 경계 규율", "# 동작 증명", "기대 결과를 구현 코드, 같은 계산식, 모델 답변에서 베끼지 않는다"):
            self.assertIn(text, output)
        self.assertNotIn("code-style-python", output)

    def test_javascript_edit_skips_typescript_section(self) -> None:
        output = self.delivered("b.mjs", "export const limit = 1;\n")
        self.assertIn("code-style-typescript-common", output)
        self.assertIn("## 이름", output)
        self.assertNotIn("## TypeScript 전용", output)
        self.assertNotIn("# 타입 시스템 규율", output)

    def test_python_edit_gets_python_skill_and_principles(self) -> None:
        output = self.delivered("tool.py", "def run():\n    return 1\n")
        for text in ("<!-- code-style-python | code-style-python/SKILL.md -->", "# 동작 증명", "# 기초부터 생각하기", "# 게으름 규약", "## 수치 기준"):
            self.assertIn(text, output)
        self.assertNotIn("# 공유 상태는", output)
        self.assertNotIn("# 구현 말고 동작 테스트", output)

    def test_concurrency_words_add_shared_state_principles(self) -> None:
        output = self.delivered("worker.py", "import threading\n\nlock = threading.Lock()\n")
        for text in ("# 공유 상태는 한 번에 하나씩 쓰게 하기 전에 먼저 나누기", "# 작업을 멱등으로 만들기", "# 데이터 · 동시성"):
            self.assertIn(text, output)

    def test_test_file_adds_test_principles(self) -> None:
        output = self.delivered("tests/test_tool.py", "def test_run():\n    assert run() == 1\n")
        self.assertIn("# 구현 말고 동작 테스트", output)
        self.assertIn("# 검증 가능한 단위로 순서 짓기", output)

    def test_map_hashes_match_sources(self) -> None:
        reader = task.skill_file(task.RULE_READER)
        done = subprocess.run([sys.executable, str(reader), "--check"], capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual((done.returncode, done.stderr), (0, ""))
        self.assertIn("changed 0", done.stdout)


class PostToolTest(HookCase):
    def merge(self, **extra: object) -> dict:
        return self.hook("PostToolUse", tool_name="Bash", tool_input={"command": "gh pr merge 12 --squash"}, tool_response={"stdout": "merged", "exit_code": 0}, **extra)

    def test_usage_notice_once_at_eighty_percent(self) -> None:
        status = {"session_id": SESSION, "cwd": str(self.repo), "context_window": {"used_percentage": 82}}
        done = subprocess.run([sys.executable, str(HOOKS / "statusline.py"), "--command-file", str(self.base / "none.json")], input=json.dumps(status), capture_output=True, text=True, env=self.env, timeout=30)
        self.assertEqual((done.returncode, done.stderr), (0, ""))
        first = self.context(self.hook("PostToolUse", tool_name="Bash", tool_input={"command": "ls"}))
        self.assertIn("문맥 사용량 82%", first)
        self.assertIn("결정 기록에 지금까지의 결정과 다음 할 일을 남긴 뒤 남은 범위는 새 서브에이전트에 인계한다", first)
        self.assertEqual(self.context(self.hook("PostToolUse", tool_name="Bash", tool_input={"command": "ls"})), "")

    def test_merge_notice_is_one_career_line(self) -> None:
        self.assertEqual(self.context(self.merge()), "")
        career = self.base / "career"
        career.mkdir()
        self.env["CAREER_ROOT"] = str(career)
        notice = self.context(self.merge())
        self.assertEqual(len(notice.splitlines()), 1)
        self.assertIn("career-record(모드 normal)", notice)
        self.assertNotIn("journal", notice)
        failed = self.hook("PostToolUse", tool_name="Bash", tool_input={"command": "gh pr merge 12"}, tool_response="Exit code: 1\nnot mergeable")
        self.assertEqual(self.context(failed), "")


class TaskCliTest(HookCase):
    def test_bind_show_unbind(self) -> None:
        self.bind("작업-1")
        run = lambda *args: json.loads(subprocess.run([sys.executable, str(HOOKS / "task.py"), *args, "--session-id", SESSION, "--cwd", str(self.repo)], capture_output=True, text=True, env=self.env, timeout=30, check=True).stdout)  # noqa: E731
        self.assertEqual(run("show")["task"], "작업-1")
        self.assertNotIn("task", run("unbind"))
        bad = subprocess.run([sys.executable, str(HOOKS / "task.py"), "bind", "--task", "../x", "--session-id", SESSION, "--cwd", str(self.repo)], capture_output=True, text=True, env=self.env, timeout=30)
        self.assertEqual(bad.returncode, 2)


class EntryPointTest(HookCase):
    def install(self, runtime: str | None = None) -> Path:
        home = self.base / "home"
        (home / ".config/skills").mkdir(parents=True, exist_ok=True)
        shutil.copy(HOOKS / "entry.py", home / ".config/skills/just-do.py")
        if runtime is not None:
            target = home / ".claude" / entry.RUNTIME
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(runtime, encoding="utf-8")
        return home

    def call(self, home: Path, payload: dict) -> dict:
        done = subprocess.run([sys.executable, str(home / ".config/skills/just-do.py"), "claude"], input=json.dumps(payload), capture_output=True, text=True, timeout=15)
        return json.loads(done.stdout)

    def test_timeouts_match_hook_definitions(self) -> None:
        for host in ("claude", "codex"):
            hooks = json.loads((PLUGIN / "hooks" / f"{host}.json").read_text(encoding="utf-8"))["hooks"]
            timeouts = {event: {item["timeout"] for group in groups for item in group["hooks"]} for event, groups in hooks.items()}
            self.assertEqual(set(timeouts), set(entry.HOOK_TIMEOUTS[host]))
            for event, values in timeouts.items():
                self.assertEqual(values, {entry.HOOK_TIMEOUTS[host][event]}, f"{host} {event}")
                child, deadline = entry.budget(host, event)
                self.assertLess(deadline, child)
                self.assertLessEqual(child + entry.START_MARGIN, min(values))

    def test_broken_runtime_denies_edits_only_inside_git(self) -> None:
        home = self.install()
        write = {"hook_event_name": "PreToolUse", "tool_name": "Write", "cwd": str(self.repo), "tool_input": {"file_path": "x.py"}}
        self.assertEqual(self.call(home, write)["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(self.call(home, {**write, "cwd": str(self.base)}), {})
        self.assertEqual(self.call(home, {**write, "tool_name": "Bash", "tool_input": {"command": "ls"}}), {})
        self.assertEqual(self.call(home, {"hook_event_name": "Stop", "cwd": str(self.repo)}), {})

    def test_slow_runtime_is_cut_before_host_limit(self) -> None:
        home = self.install("import time\ntime.sleep(30)\n")
        started = time.monotonic()
        result = self.call(home, {"hook_event_name": "PreToolUse", "tool_name": "Edit", "cwd": str(self.repo), "tool_input": {"file_path": "x.py"}})
        self.assertLess(time.monotonic() - started, entry.HOOK_TIMEOUTS["claude"]["PreToolUse"])
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_missing_launcher_fallback(self) -> None:
        home = self.base / "empty-home"
        home.mkdir()
        for host in ("claude", "codex"):
            hooks = json.loads((PLUGIN / "hooks" / f"{host}.json").read_text(encoding="utf-8"))["hooks"]
            for tool, command, inside, denied in (("Write", "", True, True), ("Write", "", False, False), ("Bash", "apply_patch x", True, True), ("Bash", "ls", True, False)):
                group = next(row for row in hooks["PreToolUse"] if re.fullmatch(row["matcher"], tool))
                payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {"command": command}})
                done = subprocess.run(["sh", "-c", group["hooks"][0]["command"]], input=payload, cwd=self.repo if inside else self.base, env={**os.environ, "HOME": str(home)}, capture_output=True, text=True, timeout=15)
                self.assertIn("unavailable", done.stderr)
                self.assertEqual(bool(json.loads(done.stdout)), denied, (host, tool, command, inside))
            stop = subprocess.run(["sh", "-c", hooks["Stop"][0]["hooks"][0]["command"]], input="{}", env={**os.environ, "HOME": str(home)}, capture_output=True, text=True, timeout=15)
            self.assertEqual(json.loads(stop.stdout), {})


class ManifestTest(unittest.TestCase):
    def test_plugin_name_and_marketplaces(self) -> None:
        claude = json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        codex = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual((claude["name"], claude["displayName"]), ("just-do", "just do"))
        self.assertEqual((codex["name"], codex["interface"]["displayName"]), ("just-do", "just do"))
        for manifest, host in ((claude, "claude"), (codex, "codex")):
            self.assertTrue((PLUGIN / manifest["hooks"]).is_file(), host)
            hooks = json.loads((PLUGIN / manifest["hooks"]).read_text(encoding="utf-8"))["hooks"]
            commands = [item["command"] for groups in hooks.values() for group in groups for item in group["hooks"]]
            self.assertTrue(all(f'python3 "$HOME/.config/skills/just-do.py" {host};' in command for command in commands), host)
        market = json.loads((REPO / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))["plugins"]
        self.assertEqual([(row["name"], row["source"]) for row in market], [("just-do", "./just")])
        agents = json.loads((REPO / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))["plugins"]
        self.assertEqual([(row["name"], row["source"]["path"]) for row in agents], [("just-do", "./just")])


if __name__ == "__main__":
    unittest.main()
