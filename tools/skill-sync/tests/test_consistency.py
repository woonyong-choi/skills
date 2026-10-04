"""#3의 위반 입력 실패·수정 후 통과와 오탐 경계 계약."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = Path(__file__).parent / 'fixtures'
CHECK = ROOT / 'tools/skill-sync/scripts/skill_check.py'
CASES = json.loads((FIXTURES / 'violations.json').read_text())


def run_check(root: Path, *options: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CHECK), *options, str(root)], capture_output=True, text=True)


@pytest.mark.parametrize('case', CASES, ids=lambda case: case['id'])
def test_cli_violation_fails_and_repair_passes(case: dict) -> None:
    root = ROOT / '.runtime' / 'consistency-tests' / f"{os.getpid()}-{case['id']}"
    root.mkdir(parents=True)
    try:
        for source in (FIXTURES / 'valid').rglob('*'):
            if source.is_file():
                target = root / source.relative_to(FIXTURES / 'valid')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
        target = root / case['file']
        valid = target.read_text()
        assert case['before'] in valid
        target.write_text(valid.replace(case['before'], case['after']))

        invalid = run_check(root, '--json')
        assert invalid.returncode == 1, invalid.stderr
        counts = json.loads(invalid.stdout)
        assert counts[case['kind']] > 0
        assert counts['total'] > 0

        target.write_text(valid)
        repaired = run_check(root)
        assert (repaired.returncode, repaired.stdout) == (0, 'total 0\n'), repaired.stderr
    finally:
        shutil.rmtree(root)


def test_cli_quoted_terms_and_referenced_rules_pass() -> None:
    root = FIXTURES / 'valid'
    result = run_check(root, '--json')
    assert (result.returncode, json.loads(result.stdout)) == (0, {'total': 0})


def test_cli_empty_root_is_input_error() -> None:
    result = run_check(FIXTURES)
    assert result.returncode == 2
    assert '검사할 SKILL.md 없음' in result.stderr
