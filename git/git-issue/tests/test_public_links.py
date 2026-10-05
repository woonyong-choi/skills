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


# #11: 상대 경로 낱말 중간의 구두점은 비공개 경로 시작이 아니다.
@pytest.mark.parametrize("wrapper", ["{}", "`{}`"])
@pytest.mark.parametrize(
    "path",
    [
        "a--/readme.md",
        "a%2D-/readme.md",
        "x--y/readme.md",
        "a./b.md",
        "docs/a--b.md",
        "a..local/readme.md",
        ".local.md/readme.md",
        "a.../readme.md",
        "a--~/readme.md",
        "a--$HOME/readme.md",
        "a--${HOME}/readme.md",
        r"a--C:\a",
        r"a--\\server\a",
        "a--file:///a",
    ],
)
def test_cli_relative_path_punctuation_is_not_private(
    path: str,
    wrapper: str,
    repository: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    body = wrapper.format(path)
    for args in ([], ["--fix"]):
        monkeypatch.setattr(sys, "stdin", io.StringIO(body))

        assert public_links.main(["--repo", str(ROOT), *args]) == 0

        output = capsys.readouterr()
        assert output.out == (body if args else "")
        assert output.err == ""


# #11: 토큰 시작의 비공개 위치는 구분 문자와 관계없이 게시 금지다.
@pytest.mark.parametrize(
    "wrapper",
    [
        "{}",
        "서문\n{}",
        "위치 {}",
        "({})",
        "[{}]",
        "{{{}}}",
        "'{}'",
        '"{}"',
        "`{}`",
        "<{}>",
    ],
)
@pytest.mark.parametrize(
    "path",
    [
        "/Users/me/a.md",
        "/home/me/a",
        "/tmp/a",
        "~/a",
        "$HOME/a",
        "${HOME}/a",
        r"C:\a",
        r"\\server\a",
        "file:///a",
        ".local/a",
        "x/.local/a",
        "x%2D-/.local/a",
        "x!/.local/a",
        "../a",
    ],
)
def test_cli_private_path_at_token_start_stays_blocked(
    path: str,
    wrapper: str,
    repository: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    body = wrapper.format(path)
    monkeypatch.setattr(sys, "stdin", io.StringIO(body))

    assert public_links.main(["--repo", str(ROOT), "--fix"]) == 1

    output = capsys.readouterr()
    assert output.out == body
    assert "do not publish; summarize without its location" in output.err
    assert "replace with a public web link" not in output.err


# #15: worktree 경로는 표기 방식과 관계없이 위치를 공개하거나 자동 변환하지 않는다.
@pytest.mark.parametrize(
    "wrapper",
    [
        "{}",
        "위치 {}",
        "({})",
        "[{}]",
        "{{{}}}",
        "'{}'",
        '"{}"',
        "`{}`",
        "`cat {}`",
        "<{}>",
        "[경로]({})",
        '[경로](<{}> "제목")',
        "[경로][ref]\n[ref]: {}",
        '<a href="{}">경로</a>',
    ],
)
@pytest.mark.parametrize(
    "path",
    [
        "daphnis.wt/fix-1/a.md",
        "saturn.wt/docs-1-readme",
        "x.wt/",
        "docs/x.wt/a.md",
        "docs/x.wt",
        "docs/a--b.wt/a.md",
        "./docs/x.wt/a.md",
    ],
)
def test_cli_worktree_path_is_private(
    path: str,
    wrapper: str,
    repository: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    body = wrapper.format(path)
    line = 2 if wrapper.startswith("[경로][ref]") else 1
    diagnostic = (
        f"{line}: private path: do not publish; summarize without its location\n"
    )
    for args in ([], ["--fix"]):
        monkeypatch.setattr(sys, "stdin", io.StringIO(body))

        assert public_links.main(["--repo", str(ROOT), *args]) == 1

        output = capsys.readouterr()
        assert output.out == (body if args else diagnostic)
        assert output.err == (diagnostic if args else "")


# #15: .wt 뒤에 이름이 이어지면 worktree 경로 마디가 아니다.
@pytest.mark.parametrize("wrapper", ["{}", "`{}`"])
@pytest.mark.parametrize(
    "path",
    [
        "a.wt.md",
        "a.wt.md/a",
        "docs/x.wtf/a.md",
        "foo.wtx/a",
        "docs/x.wt-backup/a",
        "docs/x.wt_1/a",
        "docs/x.wt!/a",
        ".wt/a",
    ],
)
def test_cli_worktree_lookalike_is_not_private(
    path: str,
    wrapper: str,
    repository: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    body = wrapper.format(path)
    for args in ([], ["--fix"]):
        monkeypatch.setattr(sys, "stdin", io.StringIO(body))

        assert public_links.main(["--repo", str(ROOT), *args]) == 0

        output = capsys.readouterr()
        assert output.out == (body if args else "")
        assert output.err == ""


# #11: 저장소 파일의 링크 교정과 비공개 위치의 게시 금지는 별도 진단이다.
@pytest.mark.parametrize(
    ("body", "reason"),
    [
        (f"`{FILE}`", "repository path in code text: replace with a public web link"),
        (f"[규칙]({FILE})", "relative repository link: replace with a public web link"),
        (
            "`/Users/me/a.md`",
            "private path: do not publish; summarize without its location",
        ),
        (
            "`../a`",
            "path outside repository: do not publish; summarize without its location",
        ),
        (
            "`git/git-issue/scripts/public_links.py`",
            "unpublished file: do not publish; summarize without its location",
        ),
        (
            "https://github.com/example/project/blob/main/.local/a",
            "private path: do not publish; summarize without its location",
        ),
    ],
)
def test_cli_repository_link_and_private_location_have_distinct_diagnostics(
    body: str,
    reason: str,
    repository: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(body))

    assert public_links.main(["--repo", str(ROOT)]) == 1

    output = capsys.readouterr()
    assert output.out == f"1: {reason}\n"
    assert output.err == ""


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
    assert (
        output.err
        == "2: private repository: do not publish; summarize without its address\n"
    )


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


# #24: 공개 링크 검사에서 원격 이름 입력, GitHub 조회·링크 계약 유지.
def test_cli_selected_remote_preserves_public_link_contract(repository: dict[str, str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    original = public_links.subprocess.run
    remotes = []
    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if command[3:5] == ["remote", "get-url"]:
            remotes.append(command[-1])
            command = [*command[:-1], "origin"]
        return original(command, **kwargs)
    monkeypatch.setattr(public_links.subprocess, "run", run)
    monkeypatch.setattr(sys, "stdin", io.StringIO(f"[규칙]({FILE})"))
    assert public_links.main(["--remote", "upstream", "--fix"]) == 0
    assert remotes == ["upstream"]
    assert f"{BASE}develop/{FILE}" in capsys.readouterr().out
