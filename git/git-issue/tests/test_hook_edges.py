"""skills#64: 흐름 시험에서 재현한 문서 가드·등록·복구 안내 결함의 회귀 검사."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "scripts"))

import document_guard as guard  # noqa: E402
import project_context as context  # noqa: E402


class TemporaryCase(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)

    def run_git(self, *args: str, cwd: Path) -> None:
        subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, timeout=15)


class ShellGuardTest(TemporaryCase):
    def decide(self, command: str) -> dict:
        return guard.check_tool({"tool_name": "Bash", "cwd": str(self.root), "tool_input": {"command": command}})

    def test_redirection_option_value_and_escaped_quote_bypasses_denied(self) -> None:
        for command in (
            "echo hi &> x.md", "echo hi >| x.md", "echo hi &>> x.md", "echo hi >& x.md",
            "sudo -u root tee x.md", "sudo --user root tee x.md", "env -u X tee x.md",
            "git -C . mv a.md b.md", "git -c k=v mv a b.md",
            'python3 -c "open(\\"x.md\\",\\"w\\")"',
            "echo hi > llms.txt", "echo hi > llms-full.txt",
        ):
            self.assertEqual(self.decide(command)["hookSpecificOutput"]["permissionDecision"], "deny", command)

    def test_copy_checks_written_names_only(self) -> None:
        (self.root / "existing").mkdir()
        for command in (
            "cp a.md absent/b", "mv a.md absent/b", "install -m 644 a.md absent/x",
            "cp -t existing a.json", "echo hi 2>&1",
        ):
            self.assertEqual(self.decide(command), {}, command)
        for command in (
            "cp a b.md", "mv -- a b.md", "install -m 644 a b.md", "cp --target-directory=d.md a",
            "cp -t docs a.md", "cp a.md existing", "mv a.md newdir/", "install -d out.md",
        ):
            self.assertEqual(self.decide(command)["hookSpecificOutput"]["permissionDecision"], "deny", command)

    def test_configuration_txt_is_not_document(self) -> None:
        for command in (
            "echo x > requirements.txt", "echo x >> requirements-dev.txt", "tee constraints.txt",
            "cp a CMakeLists.txt", "python3 -c \"open('requirements.txt','w')\"",
        ):
            self.assertEqual(self.decide(command), {}, command)
        for name in ("requirements.txt", "requirements-dev.txt", "constraints.txt", "CMakeLists.txt"):
            self.assertEqual(guard.document_paths({"tool_name": "Write", "cwd": "/", "tool_input": {"file_path": f"/x/{name}"}}), [], name)
        for name in ("llms.txt", "llms-full.txt", "notes.txt"):
            self.assertEqual(len(guard.document_paths({"tool_name": "Write", "cwd": "/", "tool_input": {"file_path": f"/x/{name}"}})), 1, name)

    def test_only_final_suffix_marks_document(self) -> None:
        """#68: 문서 확장자 뒤 다른 접미사가 붙은 이름은 문서가 아니다."""
        for command in (
            "echo x > a.txt-bak", "echo x >> notes.md.orig", "cp a notes.md.orig", "tee README.md~",
            "mv a.md.bak b.rst-old", "python3 -c \"open('notes.md.orig','w')\"",
        ):
            self.assertEqual(self.decide(command), {}, command)
        for command in (
            "echo x > a.md", "echo x > 'dir name/a.md'", 'echo x >"a.md"', "cp a d/b.txt",
            "python3 -c \"open('a' + 'b.md','w')\"", 'python3 -c "open(f\'{d}/a.md\',\'w\')"',
            "tee a.MD", "echo x > a.md;echo", "cp --target-directory=d.md a",
        ):
            self.assertEqual(self.decide(command)["hookSpecificOutput"]["permissionDecision"], "deny", command)
        self.assertFalse(guard.mentions_document("a.txt-bak notes.md.orig x.pdf_old"))
        self.assertTrue(guard.mentions_document("see notes.md, then"))

    def test_quoted_redirect_characters_are_arguments(self) -> None:
        for command in ("grep '>' README.md", 'grep -n ">" docs/a.md', "rg '>' README.md", "echo a \\> b.md", "grep 'a;tee' x.md"):
            self.assertEqual(self.decide(command), {}, command)
        for command in ("grep '>' a.md > b.md", "echo 'a;b' ; tee x.md", "bash -c 'echo > a.md'"):
            self.assertEqual(self.decide(command)["hookSpecificOutput"]["permissionDecision"], "deny", command)

    def test_brace_placeholder_does_not_split_command(self) -> None:
        for command in ("find . -name a.md -exec cp {} out.md \\;", "find . -execdir mv {} out.md +", "xargs -I{} cp {} out.md", "xargs -I {} cp {} out.md"):
            self.assertEqual(self.decide(command)["hookSpecificOutput"]["permissionDecision"], "deny", command)
        self.assertEqual(self.decide("find . -name a.md -exec grep x {} \\;"), {})


class LocalRemoteTest(TemporaryCase):
    def test_local_and_file_remotes_get_stable_identity(self) -> None:
        base = self.root / "work" / "project"
        self.assertEqual(context.normalize_remote("../origin.git", base), "file:" + str((self.root / "work/origin.git").resolve()))
        self.assertEqual(context.normalize_remote("/srv/repo.git", base), "file:/srv/repo.git")
        self.assertEqual(context.normalize_remote("file:///srv/repo.git", base), "file:/srv/repo.git")
        self.assertEqual(context.normalize_remote("git@example.org:alpha/catalog.git", base), "example.org/alpha/catalog")
        with self.assertRaises(context.ContextError):
            context.normalize_remote("file://other-host/srv/repo.git", base)

    def test_local_remote_project_registers_and_hint_names_area(self) -> None:
        vault = self.root / "vault"
        vault.mkdir()
        origin = self.root / "origin.git"
        project = self.root / "catalog"
        self.run_git("init", "-q", "--bare", str(origin), cwd=self.root)
        self.run_git("init", "-q", str(project), cwd=self.root)
        self.run_git("remote", "add", "origin", "../origin.git", cwd=project)
        environment = {"WORK_CONTINUITY_CONFIG_DIR": str(self.root / "configuration")}
        with mock.patch.dict(os.environ, environment):
            os.environ.pop("WOON_KNOWLEDGE_ROOT", None)
            context.register_vault(vault)
            import project_registration
            project_registration.register_project(project, None, False)
            ready = context.check_project(project)
            self.assertEqual(ready["identity"], "file:" + str(origin.resolve()))
            area = Path(ready["area"])
            reason = guard.check_tool({"tool_name": "Write", "cwd": str(project), "tool_input": {"file_path": str(project / "notes.md")}})["hookSpecificOutput"]["permissionDecisionReason"]
            self.assertIn(str(area / "docs"), reason)
            self.assertIn("approved_documents", reason)
            self.assertIn(ready["index"], reason)
            self.assertEqual(guard.check_tool({"tool_name": "Write", "cwd": str(project), "tool_input": {"file_path": str(area / "docs/guide.md")}}), {})

    def test_second_clone_registers_with_hint_command(self) -> None:
        vault = self.root / "vault"
        vault.mkdir()
        origin = self.root / "origin.git"
        first, second = self.root / "first", self.root / "second"
        self.run_git("init", "-q", "--bare", str(origin), cwd=self.root)
        for clone in (first, second):
            self.run_git("init", "-q", str(clone), cwd=self.root)
            self.run_git("remote", "add", "origin", str(origin), cwd=clone)
        with mock.patch.dict(os.environ, {"WORK_CONTINUITY_CONFIG_DIR": str(self.root / "configuration")}):
            os.environ.pop("WOON_KNOWLEDGE_ROOT", None)
            context.register_vault(vault)
            import project_registration
            index = Path(project_registration.register_project(first, None, False)["index"])
            stored = context.read_registration(index)["common"]
            reason = guard.check_tool({"tool_name": "Write", "cwd": str(second), "tool_input": {"file_path": str(second / "x.md")}})["hookSpecificOutput"]["permissionDecisionReason"]
            self.assertIn("--register-project", reason)
            command = reason.split("then run ", 1)[1].split("; do not bypass", 1)[0]
            result = subprocess.run(["sh", "-c", command], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout)
            registration = context.read_registration(index)
            self.assertEqual(registration["common"], stored)
            self.assertEqual(registration["paths"], sorted([str(first.resolve()), str(second.resolve())]))
            self.assertTrue(context.check_project(second)["ready"])
            self.assertTrue(context.check_project(first)["ready"])

    def test_session_notice_carries_register_command(self) -> None:
        import continuity_hook
        vault = self.root / "vault"
        vault.mkdir()
        project = self.root / "unregistered"
        self.run_git("init", "-q", str(project), cwd=self.root)
        with mock.patch.dict(os.environ, {"WORK_CONTINUITY_CONFIG_DIR": str(self.root / "configuration")}):
            os.environ.pop("WOON_KNOWLEDGE_ROOT", None)
            context.register_vault(vault)
            with mock.patch.object(continuity_hook, "handle_continuity", return_value={}), mock.patch.object(continuity_hook, "_rule_gate", return_value={}):
                result = continuity_hook.handle("claude", {"hook_event_name": "SessionStart", "cwd": str(project)}, self.root / "state")
        notice = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn(guard.setup_hint("project is unregistered", project), notice)


class RepairCommandTest(TemporaryCase):
    PAYLOAD = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": {"file_path": "x.md"}})

    def home_with(self, pointer: str | None) -> Path:
        home = self.root / f"home-{len(list(self.root.iterdir()))}"
        (home / ".config/skills").mkdir(parents=True)
        shutil.copy(PLUGIN / "scripts/hook_entry.py", home / ".config/skills/work-continuity.py")
        if pointer is not None:
            (home / ".config/skills/source").write_text(pointer + "\n")
        return home

    def source(self) -> Path:
        source = self.root / "skills source"
        (source / "tools/skill-sync/scripts").mkdir(parents=True, exist_ok=True)
        (source / "tools/skill-sync/scripts/install.py").write_text("")
        return source

    def entry_reason(self, home: Path) -> str:
        result = subprocess.run([sys.executable, str(home / ".config/skills/work-continuity.py"), "claude"], input=self.PAYLOAD, capture_output=True, text=True, timeout=15)
        return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecisionReason"]

    def fallback_reason(self, home: Path, host: str) -> str:
        hooks = json.loads((PLUGIN / f"hooks/{host}.json").read_text())["hooks"]["PreToolUse"]
        command = next(item for item in hooks if "Write" in item["matcher"])["hooks"][0]["command"]
        result = subprocess.run(["sh", "-c", command], env={**os.environ, "HOME": str(home)}, capture_output=True, text=True, timeout=15)
        return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecisionReason"]

    def test_entry_prints_absolute_installer_from_pointer(self) -> None:
        source = self.source()
        installer = source / "tools/skill-sync/scripts/install.py"
        self.assertIn(f"run python3 '{installer}' (skill-sync install)", self.entry_reason(self.home_with(str(source))))
        self.assertIn("run python3 tools/skill-sync/scripts/install.py in the skills source repo", self.entry_reason(self.home_with(None)))
        self.assertIn("in the skills source repo", self.entry_reason(self.home_with(str(self.root / "absent"))))

    def test_missing_entry_fallback_reads_pointer(self) -> None:
        source = self.source()
        installer = source / "tools/skill-sync/scripts/install.py"
        for host in ("claude", "codex"):
            home = self.home_with(str(source))
            (home / ".config/skills/work-continuity.py").unlink()
            self.assertIn(f"run python3 '{installer}' (skill-sync install)", self.fallback_reason(home, host))
            for pointer in (None, str(self.root / "absent"), '/bad"path'):
                home = self.home_with(pointer)
                (home / ".config/skills/work-continuity.py").unlink()
                self.assertIn("run python3 tools/skill-sync/scripts/install.py in the skills source repo", self.fallback_reason(home, host))


if __name__ == "__main__":
    unittest.main()
