"""#2의 별도 대상 홈 설치·재실행·zip 일치 계약."""

import hashlib
import json
import os
import runpy
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
        assert len(list(installed.parent.glob('*/SKILL.md'))) == 27
        assert not list(installed.parent.glob('*/tests'))
        # #25: 평탄한 설치본의 검사기가 하위 문서·앵커·용어 정본을 조회.
        checked = subprocess.run([sys.executable, str(installed / 'scripts/skill_check.py'), str(installed.parent)], capture_output=True, text=True)
        assert (checked.returncode, checked.stdout) == (0, 'total 0\n'), checked.stderr + checked.stdout
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


# 이슈 #21: 생성 결과의 SKILL.md 누락·중복·위치 오류는 설치 실패로 보고.
@pytest.mark.parametrize('invalid_kind', ['missing', 'duplicate', 'misplaced'])
def test_install_invalid_generated_zip_fails(install_home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, invalid_kind: str) -> None:
    install = runpy.run_path(str(INSTALL))
    write = zipfile.ZipFile.writestr

    def write_invalid(bundle: zipfile.ZipFile, info: zipfile.ZipInfo, data: bytes, *args: object, **kwargs: object) -> None:
        if info.filename == 'alpha/SKILL.md':
            if invalid_kind == 'missing':
                return
            if invalid_kind == 'duplicate':
                write(bundle, 'alpha/nested/SKILL.md', data)
            if invalid_kind == 'misplaced':
                info.filename = 'wrong/SKILL.md'
        write(bundle, info, data, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, 'writestr', write_invalid)

    result = install['main'](['--source', str(SOURCE), '--target-home', str(install_home), '--dist', str(install_home / 'dist')])

    assert result == 1
    assert 'SKILL.md' in capsys.readouterr().err
    assert not (install_home / 'dist/alpha.zip').exists()
    assert not list((install_home / 'dist').glob('.*.zip'))
