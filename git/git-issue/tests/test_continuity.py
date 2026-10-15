"""누락된 플러그인의 실제 Stop 명령이 재시도를 요청하지 않는지 확인."""

import json
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "host,variable", [("codex", "PLUGIN_ROOT"), ("claude", "CLAUDE_PLUGIN_ROOT")]
)
def test_missing_plugin_cache_uses_stable_entrypoint(host: str, variable: str) -> None:
    import os
    import subprocess

    absent = Path(__file__).parent / "absent-plugin"
    assert not absent.exists()
    config = json.loads(
        (Path(__file__).resolve().parents[1] / "hooks" / (host + ".json")).read_text()
    )
    command = config["hooks"]["Stop"][0]["hooks"][0]["command"]
    result = subprocess.run(
        ["/bin/sh", "-c", command],
        input="{}",
        text=True,
        capture_output=True,
        env={**os.environ, variable: str(absent)},
    )
    assert result.returncode == 0
    assert json.loads(result.stdout) == {}
    assert not result.stderr
    import sys
    upgrade = Path(__file__).resolve().parents[1] / "scripts/upgrade_plugin.py"
    for arguments in (("--help",), (host, "--help")):
        help_result = subprocess.run([sys.executable, str(upgrade), *arguments], capture_output=True, text=True, env={**os.environ, "PATH": str(absent)})
        assert help_result.returncode == 0 and "usage:" in help_result.stdout
    # #59: 설치 전에도 셸 복구는 열고 구조화된 쓰기는 차단한다.
    import re
    for tool, allowed in (("Bash", True), ("exec_command", True), ("Write", False), ("apply_patch", False)):
        entry = next(row for row in config["hooks"]["PreToolUse"] if re.fullmatch(row["matcher"], tool))
        missing = subprocess.run(
            ["/bin/sh", "-c", entry["hooks"][0]["command"]],
            input=json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {"command": "ls"}}),
            text=True, capture_output=True,
            env={**os.environ, "HOME": str(absent)},
        )
        assert missing.returncode == 0 and "unavailable" in missing.stderr
        assert (json.loads(missing.stdout) == {}) == allowed


@pytest.mark.parametrize("host", ["codex", "claude"])
def test_hook_records_without_reset_or_read_only_stop(host: str) -> None:
    """skills#43: 실제 checkpoint와 훅 명령의 저장 전용 계약."""
    import os
    import shutil
    import subprocess
    import time

    plugin = Path(__file__).resolve().parents[1]
    repo = plugin.parents[1]
    root = (
        repo.parent
        / ".local/orchestration/issue-continuity/test-runtime"
        / ("hook-policy-" + host)
    )
    # 원격 조회 실패가 고정 경로를 남기지 않도록 생성 전에 조회한다.
    issue = json.loads(subprocess.run(["gh", "api", "repos/woonyong-choi/skills/issues/43"], capture_output=True, text=True, check=True).stdout)
    assert not root.exists()
    folder = root / "policy"
    folder.mkdir(parents=True)
    session = "00000000-0000-4000-8000-000000000043"
    binding = {
        "repo": str(repo),
        "remote": "woonyong-choi/skills",
        "issue": 43,
        "url": "https://github.com/woonyong-choi/skills/issues/43",
        "session_ids": [session],
    }
    (folder / "binding.json").write_text(json.dumps(binding))
    record = {
        key: "fixture"
        for key in (
            "goal",
            "constraints",
            "plan",
            "hypotheses",
            "actions",
            "results",
            "next",
        )
    }
    import re
    section = issue["body"].split("## 완료 조건\n", 1)[1].split("\n## ", 1)[0]
    criteria = re.findall(r"^- \[[ xX]\] (.+)$", section, re.M)
    record["scope"] = {"criteria": criteria, "stage": "저장·복구 경계 검사", "relation": "continue", "covers": [2], "reason": "기존 기록 계약의 실제 CLI 검사", "boundary": "별도 기능은 새 과업"}
    record["scope"]["outcomes"] = [{"result": "저장한 작업 기록을 복구", "criterion": 2, "criterion_result": "기록 저장·복구 검사", "verification": "실제 checkpoint 후 restore의 필드 대조", "independent": False, "counterfactual": "저장·복구 조건을 충족하려면 같은 기록 보존이 필요하며 별도 결과 없음"}]
    record["actions"] = "fixture\nfixture"
    source = root / "record.json"
    source.write_text(json.dumps(record))

    def invoke(event: str, *, actor: str = session) -> dict:
        result = subprocess.run(
            ["python3", str(plugin / "scripts/continuity_hook.py"), host],
            input=json.dumps(
                {"hook_event_name": event, "session_id": actor, "cwd": str(repo)}
            ),
            capture_output=True,
            text=True,
            env={**os.environ, "ISSUE_CONTINUITY_ROOT": str(root)},
        )
        assert result.returncode == 0 and not result.stderr, result.stderr
        return json.loads(result.stdout)

    try:
        saved = subprocess.run(
            [
                "python3",
                str(plugin / "scripts/continuity.py"),
                "--root",
                str(root),
                "checkpoint",
                "--task",
                "policy",
                "--input",
                str(source),
                "--watch-path",
                "git/git-issue/tests/continuity-runtime-fixture",
            ],
            capture_output=True,
            text=True,
        )
        assert saved.returncode == 0, saved.stderr
        saved_record = json.loads(saved.stdout)
        assert saved_record["data"]["actions"] == "fixture"
        for change in ("goal", "relation", "covers", "criteria", "missing", "vague", "independent", "uncovered"):
            invalid = json.loads(json.dumps(record))
            if change == "vague":
                del invalid["scope"]["outcomes"]
                invalid["scope"]["reason"] = "전체 작업과 관련된 개선"
            elif change == "independent":
                invalid["scope"]["outcomes"][0]["independent"] = True
            elif change == "uncovered":
                invalid["scope"]["covers"] = [1, 2]
            elif change == "goal":
                invalid["goal"] = "different outcome"
            elif change == "missing":
                del invalid["scope"]
            else:
                invalid["scope"][change] = "independent" if change == "relation" else []
            source.write_text(json.dumps(invalid))
            rejected = subprocess.run(["python3", str(plugin / "scripts/continuity.py"), "--root", str(root), "checkpoint", "--task", "policy", "--input", str(source)], capture_output=True, text=True)
            assert rejected.returncode == 2, rejected.stdout
            assert json.loads((folder / "checkpoint.json").read_text())["pending"]["id"] == saved_record["pending"]["id"]
        source.write_text(json.dumps(record))
        prompt = invoke("UserPromptSubmit")["hookSpecificOutput"]["additionalContext"]
        assert "--from-task policy" in prompt
        assert invoke("Stop") == {}
        (folder / "meter.json").write_text(
            json.dumps({"session_id": session, "percent": 80, "at": time.time()})
        )
        text = invoke("PostToolUse")["hookSpecificOutput"]["additionalContext"]
        assert "같은 채팅에서 계속" in text
        assert "/clear" not in text and "/compact" not in text
        assert invoke("PostToolUse") == {}
        restored = subprocess.run(
            [
                "python3",
                str(plugin / "scripts/continuity.py"),
                "--root",
                str(root),
                "restore",
                "--task",
                "policy",
                "--offline",
            ],
            capture_output=True,
            text=True,
        )
        assert restored.returncode == 0, restored.stderr
        assert json.loads(restored.stdout)["ready"] is True
        assert "untracked" not in json.loads(restored.stdout)["actual"]
        binding["repo"] = str(root / "removed-worktree")
        (folder / "binding.json").write_text(json.dumps(binding))
        missing = subprocess.run(
            [
                "python3",
                str(plugin / "scripts/continuity.py"),
                "--root",
                str(root),
                "restore",
                "--task",
                "policy",
                "--offline",
            ],
            capture_output=True,
            text=True,
        )
        assert missing.returncode == 0, missing.stderr
        result = json.loads(missing.stdout)
        assert result["ready"] is False and result["data"] == saved_record["data"]
        assert "working tree missing" in result["problems"]
        assert invoke("Stop") == {}
        assert (
            "--from-task policy"
            in invoke("UserPromptSubmit")["hookSpecificOutput"]["additionalContext"]
        )
        assert invoke("Stop") == {}
        binding["repo"] = str(repo)
        (folder / "binding.json").write_text(json.dumps(binding))
        (folder / "checkpoint.json").unlink()
        assert invoke("Stop") == {}
        saved = subprocess.run(
            ["python3", str(plugin / "scripts/continuity.py"), "--root", str(root),
             "checkpoint", "--task", "policy", "--input", str(source),
             "--watch-path", "git/git-issue/tests/continuity-runtime-fixture"],
            capture_output=True, text=True, check=True,
        )
        invoke("UserPromptSubmit")
        invoke("UserPromptSubmit", actor="unbound-reader")
        changed_file = repo / "git/git-issue/tests/continuity-runtime-fixture"
        other_file = repo / ("git/git-issue/tests/continuity-other-" + host)
        assert not changed_file.exists()
        assert not other_file.exists()
        try:
            other_file.write_text("another task")
            assert invoke("Stop") == {}
            other_file.write_text("another task changed again")
            assert invoke("Stop") == {}
            changed_file.write_text("runtime change")
            assert invoke("Stop", actor="unbound-reader") == {}
            assert invoke("Stop")["decision"] == "block"
            assert invoke("Stop") == {}
            subprocess.run(
                ["python3", str(plugin / "scripts/continuity.py"), "--root", str(root),
                 "checkpoint", "--task", "policy", "--input", str(source)],
                capture_output=True, text=True, check=True,
            )
            assert invoke("Stop") == {}
            changed_file.unlink()
            assert invoke("Stop")["decision"] == "block"
            assert invoke("Stop") == {}
            invoke("SessionStart")
            invoke("UserPromptSubmit")
            assert invoke("Stop") == {}
        finally:
            changed_file.unlink(missing_ok=True)
            other_file.unlink()
    finally:
        shutil.rmtree(root)


def test_rule_gate_blocks_edits_not_reads(tmp_path: Path) -> None:
    """#62: 읽기·실행 명령은 필수 원문 강제 대상이 아니고, 편집만 미전달 원문으로 거부한다."""
    import subprocess
    import sys

    scripts = Path(__file__).resolve().parents[1] / "scripts"
    sys.path.insert(0, str(scripts))
    import continuity_hook

    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src/a.py").write_text("def f():\n    return open('x').read()\n")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    root = tmp_path / "tasks"
    (root / "t").mkdir(parents=True)
    session = "00000000-0000-4000-8000-000000000062"
    (root / "t/binding.json").write_text(json.dumps({"repo": str(repo), "session_ids": [session]}))
    base = {"hook_event_name": "PreToolUse", "session_id": session, "cwd": str(repo)}
    read = {**base, "tool_name": "Bash", "tool_input": {"command": "cat src/a.py"}}
    assert continuity_hook._rule_gate("claude", read, root) == {}
    edit = {**base, "tool_name": "Edit", "tool_input": {"file_path": str(repo / "src/a.py"), "old_string": "x", "new_string": "y"}}
    denied = continuity_hook._rule_gate("claude", edit, root)
    assert denied["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert continuity_hook._rule_gate("claude", read, root) == {}
