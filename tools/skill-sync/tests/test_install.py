"""#2의 별도 대상 홈 설치·재실행·zip 일치 계약."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

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
        assert 'Claude 계정에 올릴 zip: 없음' in second.stdout
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
