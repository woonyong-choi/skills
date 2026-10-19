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
        if command[:2] == ['gh', 'api']:
            endpoint = command[2]
            data = ({'tree': [{'path': 'README.md', 'type': 'blob'}], 'truncated': False}
                    if '/git/trees/' in endpoint else {'sha': endpoint.rsplit('/', 1)[1]})
            return subprocess.CompletedProcess(command, 0, json.dumps(data), '')
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
            "users/example",
            "orgs/example",
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
        "https://github.com/users/example/projects/123",
        "[프로젝트](https://www.github.com/orgs/example/projects/123)",
        "`https://github.com/users/example/projects/123/views/1`",
        '<a href="https://github.com/orgs/example/projects/123?pane=info">프로젝트</a>',
        "[프로젝트]: https://github.com/users/example/projects/123/",
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
        (
            "문서의 ` ```muto ` 블록(`name=` 선택)을 SVG로 만들고 "
            "이미지 줄(`![title](svg)<!-- muto -->`)을 넣거나 고친다."
        ),
        "` ```muto ![title](svg) `",
        "`` `code` ![title](svg) ``` 내용 ``",
        "``` `code` ``code`` ![title](svg) ```` 내용 ```",
        "`` ![title](svg) ``` ![other](svg) ``",
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
        ("`` ![title](svg) ```", "relative link has no published file"),
        ("``` ![title](svg) ``", "relative link has no published file"),
        (
            "` ```muto `과 `![title](svg)<!-- muto -->`와 `/tmp/db`",
            "private path",
        ),
        (
            (
                "` ```muto `과 `![title](svg)<!-- muto -->`와 "
                "`https://github.com/example/private/blob/main/secret.md`"
            ),
            "private repository",
        ),
        ("`` `code` ![title](/tmp/db) ``", "private path"),
        (
            "``` ``code`` ![title](https://github.com/example/private/blob/main/secret.md) ```",
            "private repository",
        ),
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
        ("https://github.com/users/example/projects/123/.local/secret", "private path"),
        (
            "https://github.com/orgs/example/projects/123/%2Elocal/secret",
            "private path",
        ),
        ("https://github.com/users/example/projects", "private repository"),
        ("https://github.com/users/example/projects/abc", "private repository"),
        ("https://github.com/users/example/projects/123abc", "private repository"),
        ("https://github.com/users/example/projects/123%0A", "private repository"),
        ("https://github.com/orgs/example/projects/123%0A", "private repository"),
        ("https://github.com/users/example/projects/１２３", "private repository"),
        ("https://github.com/orgs/example/projects/-123", "private repository"),
        ("https://github.com/orgs/example/projects123", "private repository"),
        ("https://github.com/orgs/example/blob/main/secret.md", "private repository"),
        ("https://github.com/users/example/blob/main/secret.md", "private repository"),
        (
            "https://raw.githubusercontent.com/users/example/projects/123",
            "private repository",
        ),
        (
            "https://raw.githubusercontent.com/orgs/example/projects/123",
            "private repository",
        ),
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
    "body",
    [
        "https://github.com/users//projects/123",
        "https://github.com/orgs//projects/123",
    ],
)
@pytest.mark.parametrize("fix", [False, True])
def test_main_reports_lookup_failure_for_malformed_project_routes(
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
    assert status == 2
    assert "public links check failed" in captured.err
    assert captured.out == ""


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


@pytest.mark.parametrize('suffix', ['', '#section', ':2-4'])
def test_fix_head_only_file_uses_verified_sha(checker: ModuleType, monkeypatch: pytest.MonkeyPatch, suffix: str) -> None:
    root = Path(__file__).resolve().parents[3]
    context = checker._Context(root)
    path = 'git/git-issue/scripts/public_links.py'
    calls = []
    run = checker._run

    def record(command: list[str]) -> str:
        calls.append(command)
        return run(command)

    monkeypatch.setattr(checker, '_run', record)
    body = f'[file]({path}{suffix}) [again]({path}{suffix})'
    fixed = checker._fix(body, checker._scan(body, context))

    fragment = '#L2-L4' if suffix == ':2-4' else suffix
    assert fixed.count(f'/blob/{context.sha}/{path}{fragment}') == 2
    assert not checker._scan(fixed, context)
    assert sum('/git/trees/' in ' '.join(call) for call in calls) <= 1
    assert sum('/commits/' in ' '.join(call) for call in calls) == 1
    assert not any(call[0] == 'git' for call in calls)


@pytest.mark.parametrize('failure', ['unpublished', 'wrong-sha', 'truncated', 'private'])
def test_fix_unverified_version_does_not_publish(
    checker: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: str,
) -> None:
    context = checker._Context(Path(__file__).resolve().parents[3])
    run = checker._run

    def unavailable(command: list[str]) -> str:
        if command[:2] == ['gh', 'api']:
            if failure == 'unpublished':
                raise subprocess.CalledProcessError(1, command)
            if '/commits/' in command[2] and failure == 'wrong-sha':
                return json.dumps({'sha': '0' * 40})
            if failure == 'truncated':
                return json.dumps({'tree': [], 'truncated': True})
        return run(command)

    monkeypatch.setattr(checker, '_run', unavailable)
    if failure == 'private':
        context.target = checker._Repository(context.target.name, 'PRIVATE', 'main')

    monkeypatch.setattr(checker, '_Context', lambda *args: context)
    monkeypatch.setattr(sys, 'stdin', io.StringIO('[file](git/git-issue/scripts/public_links.py)'))

    status = checker.main(['--fix', '-'])

    captured = capsys.readouterr()
    assert status == 2
    assert captured.out == ''
    assert 'public links check failed' in captured.err


def test_fix_default_branch_and_line_links_reuse_context(checker: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    context = checker._Context(Path(__file__).resolve().parents[3])
    calls = []
    run = checker._run

    def record(command: list[str]) -> str:
        calls.append(command)
        return run(command)

    monkeypatch.setattr(checker, '_run', record)
    body = '[a](README.md) [b](README.md#section) [c](README.md:1-2) [d](README.md:3)'
    fixed = checker._fix(body, checker._scan(body, context))

    assert '/blob/main/README.md)' in fixed
    assert '/blob/main/README.md#section)' in fixed
    assert f'/blob/{context.sha}/README.md#L1-L2)' in fixed
    assert f'/blob/{context.sha}/README.md#L3)' in fixed
    assert len(calls) == 2
    assert all(call[:2] == ['gh', 'api'] for call in calls)


@pytest.mark.parametrize('path', ['untracked.md', '.local/secret', 'project.wt/secret', '../outside.md'])
def test_fix_unpublished_or_private_path_has_no_replacement(checker: ModuleType, tmp_path: Path, path: str) -> None:
    context = checker._Context(Path(__file__).resolve().parents[3])
    context.root = tmp_path.resolve()
    (tmp_path / 'untracked.md').write_text('local only', encoding='utf-8')

    findings = checker._scan(f'[file]({path})', context)

    assert findings and all(finding.replacement is None for finding in findings)
