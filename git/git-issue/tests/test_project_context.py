"""skills#43: 실제 등록 CLI·Git worktree·제품별 훅 명령의 문서 경계 검증."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest


PLUGIN = Path(__file__).resolve().parents[1]
SCRIPT = PLUGIN / "scripts/project_context.py"
RUNTIME = PLUGIN.parents[2] / ".local/orchestration/issue-continuity/test-runtime/project-context"


class ProjectContextWorkflow(unittest.TestCase):
    def test_registration_recovery_and_document_guards(self) -> None:
        self.assertFalse(RUNTIME.exists(), "do not overwrite another execution")
        RUNTIME.mkdir(parents=True)
        environment = {**os.environ, "WORK_CONTINUITY_CONFIG_DIR": str(RUNTIME / "configuration"), "ISSUE_CONTINUITY_ROOT": str(RUNTIME / "execution")}
        environment.pop("WOON_KNOWLEDGE_ROOT", None)
        environment.pop("ISSUE_CONTINUITY_TASK", None)
        worktree = None

        def run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
            result = subprocess.run(args, cwd=cwd, env=environment, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            return result

        def cli(project: Path, *args: str, expected: int = 0) -> dict:
            result = subprocess.run([sys.executable, str(SCRIPT), "--project", str(project), *args], env=environment, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
            return json.loads(result.stdout)

        def hook(host: str, project: Path, tool: str, tool_input: dict) -> dict:
            payload = {"hook_event_name": "PreToolUse", "session_id": "context-verification", "cwd": str(project), "tool_name": tool, "tool_input": tool_input}
            result = subprocess.run([sys.executable, str(PLUGIN / "scripts/continuity_hook.py"), host], input=json.dumps(payload), env=environment, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(result.stderr, result.stderr)
            return json.loads(result.stdout)

        try:
            vault = RUNTIME / "vault"
            vault.mkdir()
            project = RUNTIME / "catalog"
            project.mkdir()
            self.assertFalse(cli(project, expected=2)["ready"])
            cli(project, "--register-vault", str(vault))
            run(["git", "init", "-q", str(project)])
            run(["git", "remote", "add", "origin", "https://example.org/alpha/catalog.git"], project)
            result = cli(project, "--register-project")
            index = Path(result["index"])
            self.assertEqual(index.parent.parent.name, "catalog")
            self.assertTrue(cli(project)["ready"])
            self.assertEqual((project / "CLAUDE.md").read_text(), "@AGENTS.md\n")

            worktree = RUNTIME / "catalog.wt" / "context-check"
            run(["git", "worktree", "add", "--orphan", "-b", "context-check", str(worktree)], project)
            self.assertFalse(cli(worktree, expected=2)["ready"])
            instructions = "# Shared project rules\n\nPreserve the public contract.\n"
            (project / "AGENTS.md").write_text(instructions)
            cli(project, "--register-project", "--migrate")
            canonical = index.parent / "project.md"
            canonical_bytes = canonical.read_bytes()
            index_bytes = index.read_bytes()
            (worktree / "AGENTS.md").write_text(instructions + "Different scope.\n")
            cli(worktree, "--register-project", "--migrate", expected=2)
            self.assertEqual(canonical.read_bytes(), canonical_bytes)
            self.assertEqual(index.read_bytes(), index_bytes)
            (worktree / "AGENTS.md").write_text(instructions)
            canonical.write_text("<!-- invalid original-scope -->\n" + instructions)
            cli(worktree, "--register-project", "--migrate", expected=2)
            self.assertEqual((worktree / "AGENTS.md").read_text(), instructions)
            canonical.write_bytes(canonical_bytes)
            metadata = json.loads(index.read_text().split("\n", 1)[0][len("<!-- project-context: "):-len(" -->")])
            metadata["common"] = str(RUNTIME / "different.git")
            index.write_text("<!-- project-context: " + json.dumps(metadata) + " -->\n" + index.read_text().split("\n", 1)[1])
            cli(worktree, "--register-project", "--migrate", expected=2)
            self.assertEqual(canonical.read_bytes(), canonical_bytes)
            index.write_bytes(index_bytes)
            same = cli(worktree, "--register-project", "--migrate")
            self.assertEqual(same["index"], str(index))
            self.assertEqual(canonical.read_bytes(), canonical_bytes)

            other = RUNTIME / "other" / "catalog"
            other.mkdir(parents=True)
            run(["git", "init", "-q", str(other)])
            run(["git", "remote", "add", "origin", "git@example.org:beta/catalog.git"], other)
            collision = cli(other, "--register-project")
            self.assertEqual(Path(collision["index"]).parent.parent.name, "beta-catalog")

            local = RUNTIME / "registered-folder"
            local.mkdir()
            original = "# Local rules\n\n" + "- Preserve the stable interface and every user constraint.\n" * 30
            (local / "AGENTS.md").write_text(original)
            (local / "CLAUDE.md").write_text(original)
            cli(local, "--register-project", expected=2)
            migrated = cli(local, "--register-project", "--migrate")
            migrated_index = Path(migrated["index"])
            self.assertTrue((migrated_index.parent / "project.md").read_text().endswith(original))
            self.assertFalse((migrated_index.parent / "claude.md").exists())
            self.assertLess(len((local / "AGENTS.md").read_bytes()), len(original.encode()))
            subdirectory = local / "source"
            subdirectory.mkdir()
            self.assertEqual(cli(subdirectory)["index"], str(migrated_index))

            text = index.read_text()
            first, body = text.split("\n", 1)
            metadata = json.loads(first[len("<!-- project-context: "):-len(" -->")])
            metadata["approved_documents"] = [{"path": "README.md", "approval": "explicit verification exception"}]
            index.write_text("<!-- project-context: " + json.dumps(metadata) + " -->\n" + body)
            allowed = index.parent.parent / "docs" / "guide.md"
            forbidden = project / "unapproved.md"
            approved = project / "README.md"
            for host in ["claude", "codex"]:
                # #62: 지원 문서는 프로젝트 등록과 무관하게 Vault career 영역만 허용.
                career = vault / "career" / "2026-11-30-회사-백엔드" / "전략.md"
                for target, is_allowed in [(allowed, True), (forbidden, False), (approved, True), (career, True), (vault / "careers.md", False)]:
                    tool = "Write" if host == "claude" else "apply_patch"
                    value = {"file_path": str(target), "content": "verified"} if host == "claude" else {"command": f"*** Begin Patch\n*** Add File: {target}\n+verified\n*** End Patch"}
                    decision = hook(host, project, tool, value)
                    self.assertEqual(decision == {}, is_allowed, decision)
                    if is_allowed:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_text("verified")
                    else:
                        self.assertFalse(target.exists())
                self.assertEqual(hook(host, project, "Bash", {"command": f"printf bad > {forbidden}"})["hookSpecificOutput"]["permissionDecision"], "deny")
                self.assertEqual(hook(host, project, "Bash", {"command": "git status --short"}), {})
                for command in (
                    "pip install -r requirements.txt",
                    "python3 -m pip install -r requirements.txt",
                    "env python3 -m pip install -r requirements.txt",
                    "bash -c 'cat guide.md'",
                    "python3 public_links.py --fix body.md",
                    "git commit -F - <<'MSG'\nfix(repo): user's rule\nMSG",
                    "git status\npip install -r requirements.txt",
                    "cat guide.md\ntouch source.py",
                    "printf '<<EOF'\npip install -r requirements.txt",
                    "sed 's/a/b/' guide.md",
                    "perl -pe 's/a/b/' guide.md",
                    "perl -Mstrict -ne 'print' notes.txt",
                    "dd if=guide.md of=result.json",
                    "cat <<-MSG\n\tuser's rule\n\tMSG\npip install -r requirements.txt",
                ):
                    self.assertEqual(hook(host, project, "Bash", {"command": command}), {}, command)
                for command in (
                    "cp body.md fixed.md", "ls\ntouch denied.md",
                    "python3 public_links.py --fix body.md > fixed.md",
                    "cat <<'MSG' > denied.md\nuser's rule\nMSG",
                    "printf '<<EOF'\nprintf bad > denied.md",
                    'printf "<<EOF"\ntouch denied.md',
                    "printf ok # <<EOF\ntouch denied.md",
                    "sed -i '' 's/a/b/' denied.md",
                    "perl -pi -e 's/a/b/' denied.md",
                    "dd if=/dev/null of=denied.md",
                    "bash -c 'tee denied.md'", "sh -lc 'touch denied.md'",
                    "env cp a denied.md", "sudo cp a denied.md",
                    "X=1 cp a denied.md", "command cp a denied.md",
                    "(cp a denied.md)", "{ cp a denied.md; }",
                    "echo $(cp a denied.md)", "if true; then cp a denied.md; fi",
                    "git mv a.md denied.md", "env sed -i s/a/b/ denied.md",
                    "sh <<'MSG'\ncp a denied.md\nMSG",
                    "cp a \\\n denied.md",
                ):
                    self.assertEqual(hook(host, project, "Bash", {"command": command})["hookSpecificOutput"]["permissionDecision"], "deny", command)
                mixed = {"command": "apply_patch", "patch": f"*** Update File: {forbidden}\n@@\n+text"}
                self.assertEqual(hook(host, project, "apply_patch", mixed)["hookSpecificOutput"]["permissionDecision"], "deny")
                self.assertEqual(hook(host, project, "Bash", {"command": "claude -p 'Inspect guide.md' > run.jsonl 2> run.stderr"}), {})
                self.assertEqual(hook(host, project, "Bash", {"command": "python3 check_doc.py guide.md\npython3 install.py --source ."}), {})
                self.assertEqual(hook(host, project, "Bash", {"command": "python3 -c \"Path('result.json').write_text('{}')\"\ncat guide.md"}), {})
                self.assertEqual(hook(host, project, "Bash", {"command": "printf bad > 'unapproved.md'"})["hookSpecificOutput"]["permissionDecision"], "deny")
                self.assertEqual(hook(host, project, "Write", {"file_path": str(project / "source.py"), "content": "pass"}), {})

            escaped = index.parent.parent / "docs" / "escape"
            escaped.symlink_to(project, target_is_directory=True)
            cli(project, "--write", str(escaped / "unapproved.md"), expected=2)
            run(["git", "remote", "set-url", "origin", "https://example.org/changed/catalog.git"], project)
            cli(project, expected=2)
            run(["git", "remote", "set-url", "origin", "https://example.org/alpha/catalog.git"], project)
            environment["WOON_KNOWLEDGE_ROOT"] = str(RUNTIME / "absent-vault")
            cli(project, expected=2)
        finally:
            if worktree and worktree.exists():
                subprocess.run(["git", "-C", str(RUNTIME / "catalog"), "worktree", "remove", "--force", str(worktree)], check=True, capture_output=True)
            shutil.rmtree(RUNTIME)


if __name__ == "__main__":
    unittest.main()
