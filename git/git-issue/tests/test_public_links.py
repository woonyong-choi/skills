from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Literal

import pytest


@pytest.fixture
def checker(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    script = Path(__file__).resolve().parents[1] / "scripts" / "public_links.py"
    spec = importlib.util.spec_from_file_location("public_links", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    run = subprocess.run

    def github_metadata(
        command: list[str],
        *,
        capture_output: bool,
        text: Literal[True],
        timeout: int,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        if command[:3] != ["gh", "repo", "view"]:
            return run(
                command,
                capture_output=capture_output,
                text=text,
                timeout=timeout,
                check=check,
            )
        name = command[3]
        if name == "woonyong-choi/skills":
            visibility = "PUBLIC"
        elif name in {
            "example/private",
            "user-attachments/private",
            "user-attachments/assets",
            "advisories/private",
        }:
            visibility = "PRIVATE"
        else:
            raise subprocess.CalledProcessError(1, command)
        data = {
            "visibility": visibility,
            "defaultBranchRef": {"name": "main"},
            "nameWithOwner": name,
        }
        return subprocess.CompletedProcess(command, 0, json.dumps(data), "")

    monkeypatch.setattr(subprocess, "run", github_metadata)
    return module


@pytest.mark.parametrize(
    "body",
    [
        "![첨부](https://github.com/user-attachments/assets/11111111-1111-1111-1111-111111111111)",
        "https://www.github.com/user-attachments/assets/11111111-1111-1111-1111-111111111111",
        "`https://github.com/user-attachments/assets/11111111-1111-1111-1111-111111111111`",
        '<img src="https://github.com/user-attachments/assets/11111111-1111-1111-1111-111111111111">',
        "[첨부]: https://github.com/user-attachments/files/123/report.txt",
        "https://github.com/advisories/GHSA-rj75-hqrm-r3gf",
        "[보안 권고](https://www.github.com/advisories/GHSA-rj75-hqrm-r3gf)",
        "`GET /query/x`",
        "`POST /query`",
        "`PATCH /items/{id}?force=true`",
        "`DELETE /items/123`",
        "`PUT /items/123`",
        "`HEAD /health`",
        "`OPTIONS /query`",
        "`TRACE /query`",
        "`GET /`",
        "`/query`",
        "<details>공개 본문</details>",
        "정규식 `/palette/`",
        "testcontrast regexp `/palette/`",
        "regexp: ``/palette/``",
        "인라인 문법 예시 `![title](svg)<!-- muto -->`",
        "인라인 주석 접두사 `// 근거:`",
        "다른 Markdown 예시 `![image](svg)`",
        "다른 주석 접두사 `// 설명:`",
        "`// 문법 예시: ![title](svg)`",
        "정규식 `/palette/`, `![title](svg)<!-- muto -->`, `// 근거:`",
    ],
)
@pytest.mark.parametrize("fix", [False, True])
def test_main_preserves_public_references(
    checker: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    body: str,
    *,
    fix: bool,
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(body))

    status = checker.main(
        [
            "--repo",
            str(Path(__file__).resolve().parents[3]),
            *(["--fix"] if fix else []),
            "-",
        ]
    )

    captured = capsys.readouterr()
    assert (status, captured.out, captured.err) == (0, body if fix else "", "")


@pytest.mark.parametrize(
    "body, reason",
    [
        ("`/Users/name/secret`", "private path"),
        ("`/palette/`", "private path"),
        ("regexp\n`/palette/`", "private path"),
        ("정규식 `/.local/`", "private path"),
        ("regexp `/%2Elocal/`", "private path"),
        ("정규식 `/Users/name/`", "private path"),
        ("정규식 `/project.wt/`", "private path"),
        ("`//server/private`", "private path"),
        ("`// 근거: /tmp/db`", "private path"),
        ("`// 근거: .local/secret`", "private path"),
        (
            "`// 근거: https://github.com/example/private/blob/main/secret.md`",
            "private repository",
        ),
        ("![title](svg)<!-- muto -->", "relative link has no published file"),
        ("`![title](/tmp/db)<!-- muto -->`", "private path"),
        ("`![title](.local/secret)<!-- muto -->`", "private path"),
        (
            "`![title](https://github.com/example/private/blob/main/secret.md)<!-- muto -->`",
            "private repository",
        ),
        (
            "정규식 `/palette/`와 `// 근거:`와 `![title](svg)<!-- muto -->`와 `/tmp/db`",
            "private path",
        ),
        (
            "정규식 `/palette/`와 https://github.com/example/private/blob/main/secret.md",
            "private repository",
        ),
        ("`/tmp/db`", "private path"),
        ("`/query/x`", "private path"),
        ("/query/x", "private path"),
        ("[경로](/query/x)", "private path"),
        ("`GET /query/x /tmp/db`", "private path"),
        ("`get /query/x`", "private path"),
        ("`FETCH /query/x`", "private path"),
        ("`GET //server/private`", "private path"),
        ("`GET /.local/secret`", "private path"),
        ("`GET /%2Elocal/secret`", "private path"),
        ("`POST /project.wt/private`", "private path"),
        ("`GET /query/x`와 `/tmp/db`", "private path"),
        ("https://github.com/user-attachments/assets/.local/secret", "private path"),
        (
            "https://github.com/example/private/blob/main/secret.md",
            "private repository",
        ),
        (
            "https://github.com/user-attachments/private/blob/main/secret.md",
            "private repository",
        ),
        (
            "https://github.com/advisories/private/blob/main/secret.md",
            "private repository",
        ),
        (
            "https://raw.githubusercontent.com/user-attachments/assets/main/secret.md",
            "private repository",
        ),
        (
            "https://github.com/woonyong-choi/skills/blob/main/README.md#L1",
            "full commit SHA",
        ),
    ],
)
@pytest.mark.parametrize("fix", [False, True])
def test_main_rejects_private_or_ambiguous_locations(
    checker: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    body: str,
    reason: str,
    *,
    fix: bool,
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(body))

    status = checker.main(
        [
            "--repo",
            str(Path(__file__).resolve().parents[3]),
            *(["--fix"] if fix else []),
            "-",
        ]
    )

    captured = capsys.readouterr()
    assert status == 1
    assert reason in (captured.err if fix else captured.out)
    assert (captured.out if fix else captured.err) == (body if fix else "")


@pytest.mark.parametrize(
    "body, expected",
    [
        (
            "[안내](README.md)",
            "[안내](https://github.com/woonyong-choi/skills/blob/main/README.md)",
        ),
        (
            "`![안내](README.md)<!-- muto -->`",
            "`![안내](https://github.com/woonyong-choi/skills/blob/main/README.md)<!-- muto -->`",
        ),
        (
            "`README.md`",
            "[README.md](https://github.com/woonyong-choi/skills/blob/main/README.md)",
        ),
    ],
)
def test_main_fix_publishes_repository_file_link(
    checker: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    body: str,
    expected: str,
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(body))

    status = checker.main(
        ["--repo", str(Path(__file__).resolve().parents[3]), "--fix", "-"]
    )

    captured = capsys.readouterr()
    assert (status, captured.out, captured.err) == (
        0,
        expected,
        "",
    )
