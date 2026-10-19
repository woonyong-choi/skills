from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize('kind, status', [('missing', 2), ('mixed', 2), ('empty', 0), ('clean', 0), ('hardcoded', 1)])
def test_cli_target_validation(tmp_path: Path, kind: str, status: int) -> None:
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'check_tokens.py'
    tokens = tmp_path / 'tokens.json'
    tokens.write_text('{}', encoding='utf-8')
    clean = tmp_path / 'clean.css'
    clean.write_text('a { color: var(--text); }', encoding='utf-8')
    target = tmp_path / kind
    if kind == 'empty':
        target.mkdir()
    elif kind == 'clean':
        target = clean
    elif kind == 'hardcoded':
        target = tmp_path / 'bad.css'
        target.write_text('a { color: #fff; }', encoding='utf-8')
    targets = [str(clean), str(target)] if kind == 'mixed' else [str(target)]

    result = subprocess.run([sys.executable, str(script), *targets, '--tokens', str(tokens)], capture_output=True, text=True, check=False)

    assert result.returncode == status
    if status == 2:
        assert str(target) in result.stderr
        assert result.stdout == ''
    else:
        assert f'total {1 if status else 0}' in result.stdout
