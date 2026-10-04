"""git-issue 공개 웹 링크 규칙의 게시 전 CLI 계약을 검증한다."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import public_links  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
SHA = "1234567890abcdef1234567890abcdef12345678"
BASE = "https://github.com/example/project/blob/"
FILE = "git/git-issue/SKILL.md"
CASES = [
    ("`/usage`", "`/usage`", 0, 0),
    ("`/model`", "`/model`", 0, 0),
    ("`/prune`", "`/prune`", 0, 0),
    ("`` /help ``", "`` /help ``", 0, 0),
    ("`/custom-command`", "`/custom-command`", 0, 0),
    ("[명령](/usage)", "[명령](/usage)", 1, 1),
    (
        "`/usage` 다음 `/home/person/note.md`",
        "`/usage` 다음 `/home/person/note.md`",
        1,
        1,
    ),
    *[
        (body, body, 1, 1)
        for path in (
            "/Users/person/note.md",
            "/home/person/note.md",
            "/private/var/log/app.log",
            "/tmp/result.md",
            "/opt/project",
            "/usage/details",
        )
        for body in (path, f"`{path}`", f"`cat {path}`")
    ],
    (
        "`curl https://github.com/example/private`",
        "`curl https://github.com/example/private`",
        1,
        1,
    ),
    ("$HOME/notes/result.md", "$HOME/notes/result.md", 1, 1),
    ("/Users/person/notes/result.md", "/Users/person/notes/result.md", 1, 1),
    (
        "https://raw.githubusercontent.com/example/private/main/note.md",
        "https://raw.githubusercontent.com/example/private/main/note.md",
        1,
        1,
    ),
    (f"[규칙]({FILE})", f"[규칙]({BASE}develop/{FILE})", 1, 0),
    (f"`{FILE}`", f"[{FILE}]({BASE}develop/{FILE})", 1, 0),
    (f"`{FILE}:79`", f"[{FILE}:79]({BASE}{SHA}/{FILE}#L79)", 1, 0),
    (f"`{FILE}:79-81`", f"[{FILE}:79-81]({BASE}{SHA}/{FILE}#L79-L81)", 1, 0),
    (f"[규칙]({FILE}#L2-L5)", f"[규칙]({BASE}{SHA}/{FILE}#L2-L5)", 1, 0),
    ("`missing-file.rs:79`", "`missing-file.rs:79`", 0, 0),
    ("`.local/e2e/result.md`", "`.local/e2e/result.md`", 1, 1),
    ("~/notes/result.md", "~/notes/result.md", 1, 1),
    (
        "https://github.com/example/private/blob/main/note.md",
        "https://github.com/example/private/blob/main/note.md",
        1,
        1,
    ),
    (f"[규칙]({BASE}develop/{FILE})", f"[규칙]({BASE}develop/{FILE})", 0, 0),
    (f"[코드]({BASE}{SHA}/{FILE}#L79)", f"[코드]({BASE}{SHA}/{FILE}#L79)", 0, 0),
    (f"[규칙][ref]\n[ref]: {FILE}", f"[규칙][ref]\n[ref]: {BASE}develop/{FILE}", 1, 0),
    (f'[규칙](<{FILE}> "제목")', f'[규칙]({BASE}develop/{FILE} "제목")', 1, 0),
    (f'<a href="{FILE}">규칙</a>', f'<a href="{BASE}develop/{FILE}">규칙</a>', 1, 0),
    ("[절](#section)", "[절](#section)", 0, 0),
    ("[없음](missing-file.md)", "[없음](missing-file.md)", 1, 1),
    (
        "[로컬](file:///Users/person/note.md)",
        "[로컬](file:///Users/person/note.md)",
        1,
        1,
    ),
    ("`cat ~/.ssh/config`", "`cat ~/.ssh/config`", 1, 1),
    (
        "[~/.ssh/config](https://example.com)",
        "[~/.ssh/config](https://example.com)",
        1,
        1,
    ),
    ("`C:\\Users\\person\\note.md`", "`C:\\Users\\person\\note.md`", 1, 1),
    ("../outside/note.md", "../outside/note.md", 1, 1),
    (
        "`git/git-issue/scripts/public_links.py`",
        "`git/git-issue/scripts/public_links.py`",
        1,
        1,
    ),
    (f"[코드]({BASE}develop/{FILE}#L1)", f"[코드]({BASE}develop/{FILE}#L1)", 1, 1),
    (
        f"[기록]({BASE}develop/%2Elocal/log.md)",
        f"[기록]({BASE}develop/%2Elocal/log.md)",
        1,
        1,
    ),
]


@pytest.fixture
def repository(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    visibility = {"example/project": "PUBLIC", "example/private": "PRIVATE"}

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if command[0] == "gh":
            name = command[3]
            if name not in visibility:
                raise subprocess.CalledProcessError(
                    1, command, stderr="repository not found"
                )
            output = json.dumps(
                {
                    "visibility": visibility[name],
                    "nameWithOwner": name,
                    "defaultBranchRef": {"name": "develop"},
                }
            )
        else:
            args = command[3:]
            outputs = {
                ("rev-parse", "--show-toplevel"): str(ROOT),
                ("remote", "get-url", "origin"): "git@github.com:example/project.git",
                ("rev-parse", "HEAD"): SHA,
                ("ls-tree", "-r", "--name-only", "-z", "HEAD"): FILE + "\0",
            }
            output = outputs[tuple(args)]
        return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")

    monkeypatch.setattr(public_links.subprocess, "run", run)
    return visibility


@pytest.mark.parametrize(("body", "expected", "before", "after"), CASES)
def test_cli_public_links_check_fix_recheck(
    body: str,
    expected: str,
    before: int,
    after: int,
    repository: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("서문\n" + body + "\n"))
    assert public_links.main(["--repo", str(ROOT)]) == before
    checked = capsys.readouterr()
    if before:
        expected_line = 3 if body.startswith("[규칙][ref]") else 2
        assert f"{expected_line}:" in checked.out
    monkeypatch.setattr(sys, "stdin", io.StringIO("서문\n" + body + "\n"))

    assert public_links.main(["--repo", str(ROOT), "--fix", "-"]) == after
    fixed = capsys.readouterr()

    assert fixed.out == "서문\n" + expected + "\n"
    assert bool(fixed.err) == bool(after)
    monkeypatch.setattr(sys, "stdin", io.StringIO(fixed.out))
    assert public_links.main(["--repo", str(ROOT)]) == after


@pytest.mark.parametrize("target_visibility", ["PUBLIC", "PRIVATE", "INTERNAL"])
def test_cli_private_links_only_allow_same_posting_repository(
    target_visibility: str,
    repository: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository["example/project"] = target_visibility
    body = f"[동일 저장소]({BASE}develop/{FILE})\nhttps://github.com/example/private\n"
    monkeypatch.setattr(sys, "stdin", io.StringIO(body))

    assert public_links.main(["--repo", str(ROOT), "--fix"]) == 1

    output = capsys.readouterr()
    assert output.out == body
    assert output.err == "2: private repository: summarize without its address\n"


def test_cli_private_repository_path_fix_stays_in_posting_repository(
    repository: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository["example/project"] = "PRIVATE"
    monkeypatch.setattr(sys, "stdin", io.StringIO(f"`{FILE}:2`"))

    assert public_links.main(["--repo", str(ROOT), "--fix"]) == 0

    assert capsys.readouterr().out == f"[{FILE}:2]({BASE}{SHA}/{FILE}#L2)"


def test_cli_file_input_never_overwrites_source(
    repository: dict[str, str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = Path(__file__).parent / "fixtures" / "body.md"
    original = source.read_bytes()

    assert public_links.main(["--repo", str(ROOT), "--fix", str(source)]) == 0

    assert source.read_bytes() == original
    assert capsys.readouterr().out == f"[규칙]({BASE}develop/{FILE})\n"


def test_cli_visibility_failure_returns_error_without_fixed_body(
    repository: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("https://github.com/example/unknown"))

    assert public_links.main(["--repo", str(ROOT), "--fix"]) == 2

    output = capsys.readouterr()
    assert output.out == ""
    assert "public links check failed" in output.err
