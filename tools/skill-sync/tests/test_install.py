"""#2의 별도 대상 홈 설치·재실행·zip 일치 계약."""

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Iterator

import pytest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).parent / 'fixtures/valid'
INSTALL = ROOT / 'tools/skill-sync/scripts/install.py'


def test_install_target_home_repeated_sync_preserves_hashes() -> None:
    target_home = ROOT / '.runtime/install-tests' / str(os.getpid())
    target_home.mkdir(parents=True)
    try:
        for tool in ('.claude', '.codex', '.gemini'):
            (target_home / tool).mkdir()
        command = [sys.executable, str(INSTALL), '--source', str(SOURCE), '--target-home', str(target_home), '--dist', str(target_home / 'dist')]
        first = subprocess.run(command, capture_output=True, text=True)
        assert first.returncode == 0, first.stderr
        second = subprocess.run(command, capture_output=True, text=True)
        assert second.returncode == 0, second.stderr
        assert '설치 성공' not in second.stdout
        assert 'Claude 계정 zip 재생성: 없음' in second.stdout
        assert 'Claude 계정 배포 상태: 미확인' in second.stdout
        assert (target_home / '.config/skills/source').read_text().strip() == str(SOURCE.resolve())
        for skill in ('alpha', 'beta', 'repo-docs'):
            expected = hashlib.sha256((SOURCE / skill / 'SKILL.md').read_bytes()).digest()
            for tool in ('.claude/skills', '.codex/skills', '.gemini/config/skills'):
                installed = target_home / tool
                assert skill in json.loads((installed / '.repo-skills.json').read_text())
                assert hashlib.sha256((installed / skill / 'SKILL.md').read_bytes()).digest() == expected
            with zipfile.ZipFile(target_home / 'dist' / f'{skill}.zip') as archive:
                assert hashlib.sha256(archive.read(f'{skill}/SKILL.md')).digest() == expected
    finally:
        shutil.rmtree(target_home)


@pytest.fixture
def install_home(request: pytest.FixtureRequest) -> Iterator[Path]:
    name = request.node.name.replace('/', '_')
    target_home = ROOT / '.runtime/install-tests' / f'{os.getpid()}-{name}'
    target_home.mkdir(parents=True)
    try:
        for tool in ('.claude', '.codex', '.gemini'):
            (target_home / tool).mkdir()
        yield target_home
    finally:
        shutil.rmtree(target_home)


# #32: 세 도구 설치본과 zip에서 tests 제외, 원본 관리 스킬 수 보존.
def test_install_tests_excluded_from_all_targets(install_home: Path) -> None:
    command = [sys.executable, str(INSTALL), '--source', str(ROOT), '--target-home', str(install_home), '--dist', str(install_home / 'dist')]

    result = subprocess.run(command, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
    source = ROOT / 'tools/skill-sync'
    files = {
        path.relative_to(source).as_posix(): path.read_bytes()
        for path in source.rglob('*')
        if path.is_file() and not {'tests', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.DS_Store'}.intersection(path.parts)
    }
    for tool in ('.claude/skills', '.codex/skills', '.gemini/config/skills'):
        installed = install_home / tool / 'skill-sync'
        assert {path.relative_to(installed).as_posix(): path.read_bytes() for path in installed.rglob('*') if path.is_file()} == files
        expected_names = {p.parent.name for category in ('code', 'docs', 'design', 'git', 'tools', 'pstack') for p in (ROOT / category).glob('*/SKILL.md')}
        assert {p.parent.name for p in installed.parent.glob('*/SKILL.md')} == expected_names
        assert not list(installed.parent.glob('*/tests'))
        assert not list(installed.parent.glob('*/.claude-plugin'))
        assert not list(installed.parent.glob('*/.codex-plugin'))
        # #25: 평탄한 설치본의 검사기가 하위 문서·앵커·용어 정본을 조회.
        checked = subprocess.run([sys.executable, str(installed / 'scripts/skill_check.py'), str(installed.parent)], capture_output=True, text=True)
        assert (checked.returncode, checked.stdout) == (0, 'total 0\n'), checked.stderr + checked.stdout
        reader = installed.parent / 'developer-thinking/scripts/read_rules.py'
        selected = subprocess.run([sys.executable, str(reader), 'product', 'implement', 'failure', 'implement'], capture_output=True, text=True)
        assert selected.returncode == 0, selected.stderr
        assert '- 필요할 때만 읽기: 결과가 다른 미확정 설계 선택' in selected.stdout
        assert '- 필요할 때만 읽기: 코드에 들어간 인터페이스 문서' in selected.stdout
        assert selected.stdout.index('# Code Style') < selected.stdout.index('## 실패 처리')
        for heading in ('조건별 읽기', '원칙', '구현', '실패 처리', '검증'):
            assert selected.stdout.count(f'\n## {heading}\n') == 1
        review = subprocess.run([sys.executable, str(reader), 'review'], capture_output=True, text=True)
        assert review.returncode == 0, review.stderr
        assert '## 구현' not in review.stdout and '## 실패 처리' not in review.stdout
        reader = installed.parent / 'code-style/scripts/read_rules.py'
        command = [sys.executable, str(reader), '--ids', 'CS-ERROR', 'CS-TEST', 'CS-ERROR']
        original = subprocess.run(command, capture_output=True, text=True)
        plain = subprocess.run([*command, '--text'], capture_output=True, text=True)
        assert original.returncode == plain.returncode == 0
        for row in json.loads(original.stdout):
            assert plain.stdout.count(row['text']) == 1
        invalid = subprocess.run([sys.executable, str(reader), '--catalog', '--text'], capture_output=True, text=True)
        assert invalid.returncode == 2 and not invalid.stdout
        _check_code_style_language_reader(reader, installed.parent)
        _check_installed_rule_hooks(installed.parent, install_home / 'orchestration')

    with zipfile.ZipFile(install_home / 'dist/skill-sync.zip') as archive:
        assert [name for name in archive.namelist() if Path(name).name == 'SKILL.md'] == ['skill-sync/SKILL.md']
        expected = {f'skill-sync/{name}': content for name, content in files.items() if not name.startswith('tests/fixtures/valid/')}
        assert {name: archive.read(name) for name in archive.namelist()} == expected
    # #25: 모든 스킬 zip에 하위 문서 원문과 SKILL.md 하나 보존.
    for archive_path in (install_home / 'dist').glob('*.zip'):
        with zipfile.ZipFile(archive_path) as archive:
            assert [name for name in archive.namelist() if Path(name).name == 'SKILL.md'] == [f'{archive_path.stem}/SKILL.md']
            installed = install_home / '.codex/skills' / archive_path.stem
            for reference in (installed / 'references').rglob('*.md'):
                assert archive.read(f'{archive_path.stem}/{reference.relative_to(installed)}') == reference.read_bytes()


# 이슈 #21: 원본 해시가 같은 기존 zip도 잘못된 내용이면 재생성.
@pytest.mark.parametrize('invalid_entry', ['alpha/nested/SKILL.md', 'missing', 'wrong/SKILL.md', 'alpha/__pycache__/cache.pyc'])
def test_install_invalid_existing_zip_rebuilt(install_home: Path, invalid_entry: str) -> None:
    command = [sys.executable, str(INSTALL), '--source', str(SOURCE), '--target-home', str(install_home), '--dist', str(install_home / 'dist')]
    first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    archive_path = install_home / 'dist/alpha.zip'
    with zipfile.ZipFile(archive_path) as archive:
        expected = {name: archive.read(name) for name in archive.namelist()}
    entries = dict(expected)
    if invalid_entry in ('missing', 'wrong/SKILL.md'):
        entries.pop('alpha/SKILL.md')
    if invalid_entry != 'missing':
        entries[invalid_entry] = b'invalid'
    with zipfile.ZipFile(archive_path, 'w') as archive:
        for name, content in entries.items():
            archive.writestr(name, content)

    result = subprocess.run(command, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
    assert '설치 성공' not in result.stdout
    with zipfile.ZipFile(archive_path) as archive:
        assert {name: archive.read(name) for name in archive.namelist()} == expected


# #31: 원본 manifest가 같아도 zip의 실제 파일과 내용이 다르면 복구.
@pytest.mark.parametrize('damage', ['stale', 'missing-helper', 'extra', 'duplicate', 'truncated'])
def test_install_changed_zip_payload_rebuilt(install_home: Path, damage: str) -> None:
    command = [sys.executable, str(INSTALL), '--source', str(SOURCE), '--target-home', str(install_home), '--dist', str(install_home / 'dist')]
    first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    archive_path = install_home / 'dist/alpha.zip'
    with zipfile.ZipFile(archive_path) as archive:
        expected = {name: archive.read(name) for name in archive.namelist()}
    entries = dict(expected)
    if damage == 'stale':
        entries['alpha/SKILL.md'] = b'old description'
    elif damage == 'missing-helper':
        entries.pop('alpha/references/storage.md')
    elif damage == 'extra':
        entries['alpha/obsolete.txt'] = b'old helper'
    with zipfile.ZipFile(archive_path, 'w') as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
        if damage == 'duplicate':
            with pytest.warns(UserWarning, match='Duplicate name'):
                archive.writestr('alpha/references/storage.md', b'duplicate')
    if damage == 'truncated':
        archive_path.write_bytes(b'PK incomplete')
    damaged = archive_path.read_bytes()

    preview = subprocess.run([*command, '--dry-run'], capture_output=True, text=True)
    assert preview.returncode == 0, preview.stderr
    assert str(archive_path) in preview.stdout
    assert archive_path.read_bytes() == damaged
    result = subprocess.run(command, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
    assert '설치 성공' not in result.stdout
    with zipfile.ZipFile(archive_path) as archive:
        assert len(archive.namelist()) == len(expected)
        assert {name: archive.read(name) for name in archive.namelist()} == expected


def _check_installed_rule_hooks(skills: Path, root: Path) -> None:
    # #58: 시작·압축 복구마다 정본 한 번, 미저장 checkpoint는 본문 재주입 사유가 아니다.
    hook = skills / 'git-issue/scripts/continuity_hook.py'
    root_rules = (skills / 'developer-thinking/SKILL.md').read_text()
    env = {**os.environ, 'ISSUE_CONTINUITY_ROOT': str(root), 'ISSUE_CONTINUITY_TASK': '', 'ISSUE_CONTINUITY_WINDOW': ''}
    folder = root / 'rule-entry'
    folder.mkdir(parents=True, exist_ok=True)
    for host in ('claude', 'codex'):
        for is_bound in (False, True):
            session = f'install-rules-{host}-{is_bound}-{skills.parent.name}'
            binding = {'repo': str(ROOT), 'url': 'https://github.com/woonyong-choi/skills/issues/58', 'session_ids': [session]}
            (folder / 'binding.json').write_text(json.dumps(binding if is_bound else {}))
            events = [('SessionStart', 1), ('UserPromptSubmit', 0), ('UserPromptSubmit', 0)]
            if is_bound:
                events += [('PostCompact', 0), ('UserPromptSubmit', 1), ('UserPromptSubmit', 0)]
            for event, expected_count in events:
                payload = {'hook_event_name': event, 'cwd': str(ROOT), 'session_id': session}
                hooked = subprocess.run([sys.executable, str(hook), host], input=json.dumps(payload), capture_output=True, text=True, env=env)
                assert hooked.returncode == 0 and not hooked.stderr, hooked.stderr
                context = json.loads(hooked.stdout).get('hookSpecificOutput', {}).get('additionalContext', '')
                assert context.count(root_rules) == expected_count, (host, is_bound, event)
            if is_bound:
                _check_rule_gate(hook, env, host, session)


def _check_rule_gate(hook: Path, env: dict[str, str], host: str, session: str) -> None:
    # #58: 실제 설치 훅 → 누락 차단 → 원문 조회 → 출력 대조 → 원래 도구 재개. #62: 편집만 차단 대상
    target = str(ROOT / 'git/git-issue/scripts/continuity_hook.py')
    payload = {'cwd': str(ROOT), 'session_id': session, 'tool_name': 'Edit', 'tool_input': {'file_path': target, 'old_string': 'a', 'new_string': 'a'}}
    def invoke(event: str, **extra: object) -> dict:
        done = subprocess.run([sys.executable, str(hook), host], input=json.dumps({**payload, 'hook_event_name': event, **extra}), capture_output=True, text=True, env=env)
        assert done.returncode == 0 and not done.stderr, done.stderr
        return json.loads(done.stdout)

    blocked = invoke('PreToolUse')['hookSpecificOutput']
    assert blocked['permissionDecision'] == 'deny'
    command = blocked['permissionDecisionReason'].split('`')[1]
    delivered = []
    for _ in range(8):
        read = subprocess.run(shlex.split(command), capture_output=True, text=True, env=env)
        assert read.returncode == 0, read.stderr
        assert read.stdout not in delivered
        delivered.append(read.stdout)
        if len(delivered) == 1:
            invoke('PostToolUse', tool_response={'stdout': read.stdout[:20]})
            assert invoke('PreToolUse')['hookSpecificOutput']['permissionDecision'] == 'deny'
        invoke('PostToolUse', tool_response={'stdout': read.stdout})
        if not invoke('PreToolUse'):
            break
    else:
        raise AssertionError('rule gate did not finish after complete output')
    repeated = subprocess.run(shlex.split(command), capture_output=True, text=True, env=env)
    assert '전달 완료' in repeated.stdout
    assert not invoke('PreToolUse')
    reader = hook.parents[2] / 'developer-thinking/scripts/read_rules.py'
    query = {'command': f'{sys.executable} {reader} implement'}
    rewritten = invoke('PreToolUse', tool_input=query)['hookSpecificOutput']['updatedInput']
    reused = subprocess.run(shlex.split(rewritten['command']), capture_output=True, text=True, env=env)
    assert reused.returncode == 0 and '전달 완료' in reused.stdout
    style = hook.parents[2] / 'code-style/scripts/read_rules.py'
    for arguments in ('--ids=CS-ERROR --text --language=python', '--ids CS-ERROR --text --language python'):
        query_input = {'command': f'{sys.executable} {style} {arguments}'}
        rewritten = invoke('PreToolUse', tool_input=query_input)['hookSpecificOutput']['updatedInput']
        reused = subprocess.run(shlex.split(rewritten['command']), capture_output=True, text=True, env=env)
        assert reused.returncode == 0 and '전달 완료' in reused.stdout
    for arguments in ('--ids CS-NAEM --text', '--ids CS-ERROR --text --language=Py/x', '--ids CS-ERROR --text --language=missing'):
        invalid = f'{sys.executable} {style} {arguments}'
        assert not invoke('PreToolUse', tool_input={'command': invalid})
        failed = subprocess.run(shlex.split(invalid), capture_output=True, text=True, env=env)
        assert (failed.returncode, failed.stdout) == (2, '')
    patch = '*** Begin Patch\n*** Update File: code/code-style/scripts/read_rules.py\n@@\n+def added():\n+    raise ValueError()\n*** End Patch'
    for field in ('command', 'patch'):
        assert invoke('PreToolUse', session_id=session + '-patch-' + field, tool_name='apply_patch', tool_input={field: patch})['hookSpecificOutput']['permissionDecision'] == 'deny'
    assert invoke('PreToolUse', session_id=session + '-patch-combined', tool_name='apply_patch', tool_input={'command': 'apply_patch', 'patch': patch})['hookSpecificOutput']['permissionDecision'] == 'deny'
    assert invoke('PreToolUse', agent_id='separate-worker')['hookSpecificOutput']['permissionDecision'] == 'deny'
    fresh = {'session_id': session + '-query-first'}
    invoke('SessionStart', **fresh)
    rewritten = invoke('PreToolUse', tool_input=query, **fresh)['hookSpecificOutput']['updatedInput']
    prior = subprocess.run(shlex.split(rewritten['command']), capture_output=True, text=True, env=env)
    assert prior.returncode == 0 and '# Code Style' in prior.stdout
    invoke('PostToolUse', tool_input=rewritten, tool_response={'stdout': prior.stdout}, **fresh)
    blocked = invoke('PreToolUse', **fresh)['hookSpecificOutput']['permissionDecisionReason']
    remaining = subprocess.run(shlex.split(blocked.split('`')[1]), capture_output=True, text=True, env=env)
    assert remaining.returncode == 0 and '# Code Style\n' not in remaining.stdout
    read_session = {'session_id': session + '-read', 'tool_name': 'Read', 'tool_input': {'file_path': str(ROOT / 'code/code-style/scripts/read_rules.py')}}
    invoke('PostToolUse', tool_response='source inspected', **read_session)
    assert not invoke('Stop', **read_session)
    edit_session = {**read_session, 'session_id': session + '-edit', 'tool_name': 'Edit'}
    invoke('PostToolUse', tool_response='edited', **edit_session)
    assert invoke('Stop', **edit_session)['decision'] == 'block'
    assert not invoke('Stop', stop_hook_active=True, **edit_session)
    invoke('PostCompact')
    assert not invoke('PreToolUse', tool_name='Bash', tool_input={'command': 'true'})
    assert invoke('PreToolUse')['hookSpecificOutput']['permissionDecision'] == 'deny'
    for suffix in ('\ntouch source.py', ' "$(touch source.py)"', ' `touch source.py`', '; touch source.py'):
        unsafe = f'{sys.executable} {style} --catalog' + suffix
        assert not invoke('PreToolUse', tool_name='Bash', tool_input={'command': unsafe})  # 조회 재작성 없음, 셸은 강제 대상 아님
    string_query = invoke('PreToolUse', tool_name='Bash', tool_input=f'{sys.executable} {reader} implement')
    assert '--pending' in string_query['hookSpecificOutput']['updatedInput']['command']
    rule_source = style.parents[1] / 'references/structure.md'
    original = rule_source.read_bytes()
    try:
        rule_source.write_text('## temporarily unavailable\n', encoding='utf-8')
        failed = invoke('PreToolUse')
        assert '필수 규칙 자동 조회 실패' in failed['hookSpecificOutput']['additionalContext']
        assert not invoke('PreToolUse', tool_input={'command': 'ls'})
    finally:
        rule_source.write_bytes(original)
    assert invoke('PreToolUse')['hookSpecificOutput']['permissionDecision'] == 'deny'


# #58: code-style 조회의 --language 공개 계약. 실패는 종료 2와 빈 stdout.
def _check_code_style_language_reader(reader: Path, skills: Path) -> None:
    def run(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(reader), *arguments], capture_output=True, text=True)

    language = (skills / 'code-style-python/SKILL.md').read_text()
    cost = (skills / 'code-style/references/cost.md').read_text()
    rows = json.loads(run('--ids', 'CS-ERROR', 'CS-COST').stdout)
    selected = run('--ids', 'CS-ERROR', 'CS-COST', 'CS-ERROR', '--text', '--language', 'python', 'python')
    assert selected.returncode == 0, selected.stderr
    for text in (*(row['text'] for row in rows), language, cost):
        assert selected.stdout.count(text) == 1
    assert [selected.stdout.count(f'<!-- {name} -->') for name in ('code-style-python/SKILL.md', 'code-style/references/cost.md')] == [1, 1]
    assert selected.stdout.count('<!-- CS-LANGUAGE |') == 1
    assert selected.stdout.index('<!-- CS-LANGUAGE |') < selected.stdout.index('<!-- CS-ERROR |')

    rust = (skills / 'code-style-rust/SKILL.md').read_text()
    for arguments in (
        ('--language', 'python', '--language', 'rust'),
        ('--language', 'python', 'rust', '--language', 'python'),
    ):
        merged = run('--ids', 'CS-ERROR', '--text', *arguments)
        assert merged.returncode == 0, merged.stderr
        assert (merged.stdout.count(language), merged.stdout.count(rust)) == (1, 1), arguments

    unselected = run('--ids', 'CS-ERROR', '--text')
    assert unselected.returncode == 0, unselected.stderr
    assert language not in unselected.stdout and cost not in unselected.stdout and 'CS-LANGUAGE' not in unselected.stdout

    for arguments in (
        ('--ids', 'CS-ERROR', '--text', '--language', 'Python'),
        ('--ids', 'CS-ERROR', '--text', '--language', 'python', '../python'),
        ('--ids', 'CS-ERROR', '--text', '--language', 'missing-language'),
        ('--ids', 'CS-ERROR', '--language', 'python'),
        ('--catalog', '--text', '--language', 'python'),
        ('--text', '--language', 'python'),
        ('--ids', 'CS-ERROR', '--text', '--language'),
    ):
        failed = run(*arguments)
        assert (failed.returncode, failed.stdout) == (2, ''), arguments

    for removed, arguments in (
        (skills / 'code-style-python/SKILL.md', ('--ids', 'CS-ERROR', '--text', '--language', 'python')),
        (skills / 'code-style/references/cost.md', ('--ids', 'CS-ERROR', 'CS-COST', '--text')),
    ):
        content = removed.read_bytes()
        removed.unlink()
        try:
            failed = run(*arguments)
        finally:
            removed.write_bytes(content)
        assert (failed.returncode, failed.stdout) == (2, ''), removed

    # 같은 ID가 다른 절을 가리키면 마지막 항목으로 덮어쓰지 않고 거부.
    catalog = json.loads((skills / 'code-style/references/rule-map.json').read_text())
    first, second = catalog['sections'][:2]
    duplicate = json.dumps({'sections': [*catalog['sections'], {**first, 'title': second['title']}]})
    for source, replacements, arguments in (
        (skills / 'code-style/references/rule-map.json', ('null', '{"sections": null}', '{"sections": [null]}', '{"sections": [{}]}'), ('--catalog',)),
        (skills / 'code-style/references/rule-map.json', (duplicate,), ('--ids', first['id'], '--text')),
        (skills / 'code-style/references/errors.md', ('## missing\n',), ('--ids', 'CS-ERROR', '--text')),
    ):
        content = source.read_bytes()
        try:
            for replacement in replacements:
                source.write_text(replacement, encoding='utf-8')
                failed = run(*arguments)
                assert (failed.returncode, failed.stdout) == (2, ''), source
                assert str(source) in failed.stderr and 'Traceback' not in failed.stderr
        finally:
            source.write_bytes(content)


def test_dependency_folder_symlink_does_not_block_install(tmp_path: Path) -> None:
    """npm ci가 만든 node_modules 안 symlink는 배포 대상 밖이라 설치를 막지 않고 복사되지도 않음"""
    source = tmp_path / 'source'
    shutil.copytree(SOURCE, source)
    skill = next(path.parent for path in sorted(source.rglob('SKILL.md')))
    modules = skill / 'scripts/node_modules'
    (modules / 'real').mkdir(parents=True)
    (modules / '.bin').mkdir()
    (modules / '.bin/link').symlink_to(modules / 'real')
    home = tmp_path / 'home'
    (home / '.claude').mkdir(parents=True)
    result = subprocess.run(
        [sys.executable, str(INSTALL), '--source', str(source), '--target-home', str(home), '--dist', str(home / 'dist')],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert list(home.rglob('SKILL.md')), 'installed'
    assert not list(home.rglob('node_modules'))
