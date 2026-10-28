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
    source_check = subprocess.run([sys.executable, str(ROOT / 'tools/skill-sync/scripts/skill_check.py'), '--json', str(ROOT)], capture_output=True, text=True)
    assert source_check.returncode in (0, 1), source_check.stderr
    source_counts = json.loads(source_check.stdout)
    source = ROOT / 'tools/skill-sync'
    files = {
        path.relative_to(source).as_posix(): path.read_bytes()
        for path in source.rglob('*')
        if path.is_file() and not {'tests', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.DS_Store'}.intersection(path.parts)
    }
    for tool in ('.claude/skills', '.codex/skills', '.gemini/config/skills'):
        installed = install_home / tool / 'skill-sync'
        assert {path.relative_to(installed).as_posix(): path.read_bytes() for path in installed.rglob('*') if path.is_file()} == files
        expected_names = {p.parent.name for category in ('code', 'docs', 'design', 'git', 'tools', 'just', 'personal') for p in (ROOT / category).glob('*/SKILL.md')}
        assert {p.parent.name for p in installed.parent.glob('*/SKILL.md')} == expected_names
        assert not list(installed.parent.glob('*/tests'))
        assert not list(installed.parent.glob('*/.claude-plugin'))
        assert not list(installed.parent.glob('*/.codex-plugin'))
        assert not [path for path in (installed.parent / 'just').rglob('*') if path.name.endswith(('.test.ts', '.test-helper.ts'))]
        # #25: 평탄한 설치본의 검사기가 하위 문서·앵커·용어 정본을 원본과 똑같이 조회. 위반 수는 원본 검사와 같아야 한다.
        checked = subprocess.run([sys.executable, str(installed / 'scripts/skill_check.py'), '--json', str(installed.parent)], capture_output=True, text=True)
        assert checked.returncode in (0, 1), checked.stderr
        assert json.loads(checked.stdout) == source_counts
        _check_rule_reader(installed.parent / 'just/scripts/rules/read_rules.py', install_home / 'work' / f'{installed.parent.parent.name}-reader')
        _check_installed_rule_hooks(installed.parent, install_home / 'work' / installed.parent.parent.name)

    with zipfile.ZipFile(install_home / 'dist/skill-sync.zip') as archive:
        assert [name for name in archive.namelist() if Path(name).name == 'SKILL.md'] == ['skill-sync/SKILL.md']
        expected = {f'skill-sync/{name}': content for name, content in files.items() if not name.startswith('tests/fixtures/valid/')}
        assert {name: archive.read(name) for name in archive.namelist()} == expected
    with zipfile.ZipFile(install_home / 'dist/just.zip') as archive:
        assert not [name for name in archive.namelist() if name.endswith(('.test.ts', '.test-helper.ts'))]
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


def _check_installed_rule_hooks(skills: Path, work: Path) -> None:
    # 설치본 훅: 연결 과업만 복원하고 just dev 자동 진입은 안내하지 않는다.
    hook = skills / 'just/scripts/hooks/hook.py'
    entry_line = "연결 과업: install-check"
    body = (skills / 'just/SKILL.md').read_text()
    work.mkdir(parents=True, exist_ok=True)
    subprocess.run(['git', 'init', '-q', str(work)], check=True)
    (work / 'tool.py').write_text("import subprocess\n\ndef run():\n    raise ValueError('x')\n")
    env = {**os.environ, 'SKILLS_CONFIG_DIR': str(work.parent / 'config')}
    for host in ('claude', 'codex'):
        for is_bound in (False, True):
            session = f'install-rules-{host}-{is_bound}-{skills.parent.name}'
            if is_bound:
                bound = subprocess.run([sys.executable, str(hook.with_name('task.py')), 'bind', '--session-id', session, '--task', 'install-check', '--issue', 'https://github.com/woonyong-choi/skills/issues/58', '--cwd', str(work)], capture_output=True, text=True, env=env)
                assert bound.returncode == 0, bound.stderr
            events = [('SessionStart', True), ('UserPromptSubmit', False), ('PostCompact', False), ('UserPromptSubmit', True), ('UserPromptSubmit', False)]
            for event, expected in events:
                payload = {'hook_event_name': event, 'cwd': str(work), 'session_id': session}
                hooked = subprocess.run([sys.executable, str(hook), host], input=json.dumps(payload), capture_output=True, text=True, env=env)
                assert hooked.returncode == 0 and not hooked.stderr, hooked.stderr
                context = json.loads(hooked.stdout).get('hookSpecificOutput', {}).get('additionalContext', '')
                assert context.startswith(entry_line) == (expected and is_bound), (host, is_bound, event, context)
                assert "코드를 바꾸는 개발 일" not in context
                assert "just/SKILL.md" not in context
                assert body not in context
                assert ('issues/58' in context) == (expected and is_bound), (host, is_bound, event)
            if is_bound:
                _check_rule_gate(hook, env, host, session, work)


def _check_rule_gate(hook: Path, env: dict[str, str], host: str, session: str, work: Path) -> None:
    # #58: 실제 설치 훅 → 누락 차단 → 원문 조회 → 출력 대조 → 원래 도구 재개. #62: 편집만 차단 대상
    target = str(work / 'tool.py')
    payload = {'cwd': str(work), 'session_id': session, 'tool_name': 'Edit', 'tool_input': {'file_path': target, 'old_string': 'a', 'new_string': "import subprocess\n\ndef run():\n    raise ValueError('x')\n"}}
    switched_on = set()

    def invoke(event: str, **extra: object) -> dict:
        request = {**payload, 'hook_event_name': event, **extra}
        if request['session_id'] not in switched_on:
            # 규칙 확인은 /mode로 켠 세션에서만 동작
            switched_on.add(request['session_id'])
            invoke('UserPromptSubmit', session_id=request['session_id'], prompt='/just dev')
        done = subprocess.run([sys.executable, str(hook), host], input=json.dumps(request), capture_output=True, text=True, env=env)
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
    reader = hook.parents[1] / 'rules/read_rules.py'
    for arguments in ('tool.py', '--ids CS-ERROR CS-CORE', '--ids=CS-ERROR'):
        rewritten = invoke('PreToolUse', tool_input={'command': f'{sys.executable} {reader} {arguments}'})['hookSpecificOutput']['updatedInput']
        reused = subprocess.run(shlex.split(rewritten['command']), capture_output=True, text=True, env=env, cwd=work)
        assert reused.returncode == 0 and '전달 완료' in reused.stdout, arguments
    for arguments in ('--ids CS-NAEM', '--ids CS-ERROR --check', 'notes.md'):
        invalid = f'{sys.executable} {reader} {arguments}'
        assert not invoke('PreToolUse', tool_input={'command': invalid})
        failed = subprocess.run(shlex.split(invalid), capture_output=True, text=True, env=env, cwd=work)
        assert (failed.returncode, failed.stdout) == (2, ''), arguments
    patch = '*** Begin Patch\n*** Update File: tool.py\n@@\n+def added():\n+    raise ValueError()\n*** End Patch'
    for field in ('command', 'patch'):
        assert invoke('PreToolUse', session_id=session + '-patch-' + field, tool_name='apply_patch', tool_input={field: patch})['hookSpecificOutput']['permissionDecision'] == 'deny'
    assert invoke('PreToolUse', session_id=session + '-patch-combined', tool_name='apply_patch', tool_input={'command': 'apply_patch', 'patch': patch})['hookSpecificOutput']['permissionDecision'] == 'deny'
    assert invoke('PreToolUse', agent_id='separate-worker')['hookSpecificOutput']['permissionDecision'] == 'deny'
    fresh = {'session_id': session + '-query-first'}
    invoke('SessionStart', **fresh)
    query = {'command': f'{sys.executable} {reader} --ids CS-CORE'}
    rewritten = invoke('PreToolUse', tool_input=query, **fresh)['hookSpecificOutput']['updatedInput']
    prior = subprocess.run(shlex.split(rewritten['command']), capture_output=True, text=True, env=env)
    assert prior.returncode == 0 and '# 코드 스타일' in prior.stdout
    invoke('PostToolUse', tool_input=rewritten, tool_response={'stdout': prior.stdout}, **fresh)
    blocked = invoke('PreToolUse', **fresh)['hookSpecificOutput']['permissionDecisionReason']
    remaining = subprocess.run(shlex.split(blocked.split('`')[1]), capture_output=True, text=True, env=env)
    assert remaining.returncode == 0 and '# 코드 스타일\n' not in remaining.stdout
    read_session = {'session_id': session + '-read', 'tool_name': 'Read', 'tool_input': {'file_path': target}}
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
        unsafe = f'{sys.executable} {reader} tool.py' + suffix
        assert not invoke('PreToolUse', tool_name='Bash', tool_input={'command': unsafe})  # 조회 재작성 없음, 셸은 강제 대상 아님
    string_query = invoke('PreToolUse', tool_name='Bash', tool_input=f'{sys.executable} {reader} {target}')
    assert '--pending' in string_query['hookSpecificOutput']['updatedInput']['command']
    rule_source = hook.parents[3] / 'code-style/references/structure.md'
    original = rule_source.read_bytes()
    try:
        rule_source.write_text('## temporarily unavailable\n', encoding='utf-8')
        failed = invoke('PreToolUse')
        assert '필수 규칙 자동 조회 실패' in failed['hookSpecificOutput']['additionalContext']
        assert not invoke('PreToolUse', tool_input={'command': 'ls'})
    finally:
        rule_source.write_bytes(original)
    assert invoke('PreToolUse')['hookSpecificOutput']['permissionDecision'] == 'deny'


# 규칙 조회기 공개 계약: 파일 종류별 선택, ID 조회, 해시 대조. 실패는 종료 2와 빈 stdout.
def _check_rule_reader(reader: Path, work: Path) -> None:
    skills = reader.parents[3]
    work.mkdir(parents=True, exist_ok=True)

    def run(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(reader), *arguments], capture_output=True, text=True, cwd=work, check=False)

    checked = run('--check')
    assert (checked.returncode, checked.stdout.strip()) == (0, f"rules {len(json.loads((reader.parent / 'rule-map.json').read_text())['rules'])}, changed 0"), checked.stderr
    python = (skills / 'code-style-python/SKILL.md').read_text().split('\n---\n', 1)[1].lstrip('\n')
    selected = run('tool.py', 'tool.py')
    assert selected.returncode == 0, selected.stderr
    assert selected.stdout.count(python) == 1
    assert selected.stdout.index('<!-- principle-prove-it-works |') < selected.stdout.index('<!-- CS-CORE |') < selected.stdout.index('<!-- code-style-python |')
    typescript, javascript = run('view.ts'), run('view.js')
    assert '## TypeScript 전용' in typescript.stdout and '<!-- principle-type-system-discipline |' in typescript.stdout
    assert '## TypeScript 전용' not in javascript.stdout and '## 이름' in javascript.stdout and 'code-style-python' not in javascript.stdout
    repeated = run('--ids', 'CS-ERROR', 'CS-TEST', 'CS-ERROR')
    assert repeated.returncode == 0 and repeated.stdout.count('<!-- CS-ERROR |') == 1 and repeated.stdout.count('<!-- CS-TEST |') == 1

    for arguments in (('--ids', 'CS-NAEM'), ('--ids', 'CS-ERROR', '--check'), ('notes.md',), (), ('--ids',)):
        failed = run(*arguments)
        assert (failed.returncode, failed.stdout) == (2, ''), arguments

    removed = skills / 'code-style-python/SKILL.md'
    content = removed.read_bytes()
    removed.unlink()
    try:
        failed = run('tool.py')
    finally:
        removed.write_bytes(content)
    assert (failed.returncode, failed.stdout) == (2, '')

    catalog = reader.parent / 'rule-map.json'
    for source, replacements, arguments in (
        (catalog, ('null', '{"rules": null, "select": []}', '{"rules": {"x": null}, "select": []}', '{"rules": {}, "select": [{"rules": ["x"]}]}'), ('--ids', 'CS-ERROR')),
        (skills / 'code-style/references/structure.md', ('## missing\n',), ('--ids', 'CS-NAME')),
        (skills / 'code-style/references/errors.md', ('## changed\n',), ('--ids', 'CS-ERROR')),
    ):
        content = source.read_bytes()
        try:
            for replacement in replacements:
                source.write_text(replacement, encoding='utf-8')
                failed = run(*arguments)
                assert (failed.returncode, failed.stdout) == (2, ''), (source, replacement)
                assert 'Traceback' not in failed.stderr and ('rule' in failed.stderr or str(source) in failed.stderr), failed.stderr
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


# 예전 설치본에 남은 TypeScript 시험 파일은 해시가 같아도 다시 설치해 지운다.
def test_install_removes_leftover_typescript_tests(install_home: Path) -> None:
    command = [sys.executable, str(INSTALL), '--source', str(SOURCE), '--target-home', str(install_home), '--dist', str(install_home / 'dist')]
    assert subprocess.run(command, capture_output=True, text=True).returncode == 0
    leftovers = [install_home / '.codex/skills/alpha/scripts/a.test.ts', install_home / '.codex/skills/alpha/b.test-helper.ts']
    for leftover in leftovers:
        leftover.parent.mkdir(parents=True, exist_ok=True)
        leftover.write_text('test', encoding='utf-8')

    result = subprocess.run(command, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
    assert not [leftover for leftover in leftovers if leftover.exists()]
