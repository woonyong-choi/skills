"""#24: 저장소 정책을 받는 기존 공개 진입점의 계약."""

import importlib.util
import subprocess
from types import ModuleType
from typing import Any
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[3]


def load_script(name: str, relative: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LLMS = load_script("gen_llms", "docs/repo-docs-llms/scripts/gen_llms.py")
CLEANUP = load_script("cleanup_merged", "git/git-branch/scripts/cleanup_merged.py")


@pytest.mark.parametrize("branch", ["develop", "release/stable"])
def test_raw_base_url_uses_remote_default_branch(branch: str) -> None:
    def git(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if command[1:3] == ["remote", "get-url"]:
            output = "git@github.com:example/project.git"
        elif command[1] == "ls-remote":
            output = f"ref: refs/heads/{branch}\tHEAD\nabc\tHEAD"
        else:
            raise AssertionError(command)
        return subprocess.CompletedProcess(command, 0, output, "")

    with patch.object(LLMS.subprocess, "run", side_effect=git):
        assert LLMS.raw_base_url() == f"https://raw.githubusercontent.com/example/project/{branch}/"


def test_raw_base_url_explicit_url_skips_remote_lookup() -> None:
    with patch.object(LLMS.subprocess, "run") as run:
        assert LLMS.raw_base_url(raw_url="https://docs.example/raw/trunk") == "https://docs.example/raw/trunk/"
        run.assert_not_called()


@pytest.mark.parametrize("branch,options,expected", [
    ("trunk", [], "skip: trunk: 보호 브랜치"),
    ("release/stable", ["--default-branch", "release/stable"], "skip: release/stable: 보호 브랜치"),
    ("support", ["--protect", "support"], "skip: support: 보호 브랜치"),
    ("feature", ["--remote", "upstream"], "git push upstream --force-with-lease=refs/heads/feature:abc :refs/heads/feature"),
])
def test_cleanup_policy_protects_or_previews_selected_remote(branch: str, options: list[str], expected: str, capsys: pytest.CaptureFixture[str]) -> None:
    calls = []

    def run(command: list[str], check: bool = True) -> str:
        calls.append(command)
        if command[:3] == ["git", "ls-remote", "--symref"]:
            return "ref: refs/heads/trunk\tHEAD\nabc\tHEAD"
        if command[:3] == ["git", "ls-remote", "--heads"]:
            return f"abc\trefs/heads/{branch}"
        if command[:2] == ["git", "rev-parse"]:
            return "abc"
        if command[:3] == ["git", "worktree", "list"] or command[:2] == ["git", "check-ref-format"]:
            return ""
        raise AssertionError(command)

    pr = {"state": "MERGED", "headRefName": branch, "headRefOid": "abc", "number": 1}
    with patch.object(CLEANUP, "resolve_pr", return_value=pr), patch.object(CLEANUP, "run", side_effect=run):
        assert CLEANUP.main(["1", *options]) == 0
    assert expected in capsys.readouterr().out
    assert not any(call[:2] == ["git", "push"] for call in calls)


def test_cleanup_unknown_default_branch_stops_before_actions() -> None:
    with patch.object(CLEANUP, "run", return_value=""), patch.object(CLEANUP, "resolve_pr") as resolve:
        with pytest.raises(SystemExit, match="default branch"):
            CLEANUP.main(["1"])
        resolve.assert_not_called()


# #24: 공개 archive 허용 정책도 비공개·git 제외·경로 탈출 검증 유지.
@pytest.mark.parametrize("relative,ignored,expected", [
    ("docs/archive/a.md", 1, True),
    ("docs/%2570rivate/a.md", 1, False),
    ("docs/.LOCAL/a.md", 1, False),
    ("docs/a.md", 0, False),
    ("../outside.md", 1, False),
    ("/outside.md", 1, False),
    ("docs/a.txt", 1, False),
])
def test_is_public_repository_policy_preserves_guards(relative: str, ignored: int, expected: bool) -> None:
    with patch.object(Path, "is_file", return_value=True), patch.object(LLMS.subprocess, "run", return_value=subprocess.CompletedProcess([], ignored)):
        assert LLMS.is_public(ROOT, relative, (".local", "private")) == expected


# #24: 기본 정책에서는 공개 여부와 무관하게 archive 차단을 유지.
def test_is_public_default_policy_blocks_archive() -> None:
    assert not LLMS.is_public(ROOT, "docs/archive/a.md")


# #24: 원문 URL 미정·잘못된 URL을 main으로 대체하지 않음.
@pytest.mark.parametrize("raw_url", ["file:///docs", "https://example.com/raw?token=x"])
def test_raw_base_url_invalid_override_fails(raw_url: str) -> None:
    with pytest.raises(SystemExit, match="invalid raw base URL"):
        LLMS.raw_base_url(raw_url=raw_url)


# #24: 원격 선택과 명시 브랜치는 GitHub 기본 URL 계약 유지.
def test_raw_base_url_explicit_remote_and_branch() -> None:
    with patch.object(LLMS.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "git@github.com:example/project.git", "")) as run:
        assert LLMS.raw_base_url("upstream", "main") == "https://raw.githubusercontent.com/example/project/main/"
    assert run.call_args.args[0] == ["git", "remote", "get-url", "upstream"]
