"""#37: 배포 명령의 검사 중단·실패 코드·최종 해시 대조 계약."""
import importlib
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
deploy = importlib.import_module('deploy')


def test_account_adapter_contracts() -> None:
    result = subprocess.run(['node', '--test', str(Path(__file__).with_name('claude_upload.test.mjs'))], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('stage', ['check', 'install', 'account', 'verify', 'success'])
def test_deploy_stage_failure_returns_nonzero(stage: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deploy.install, 'resolve_source', lambda _: Path('/source'))
    monkeypatch.setattr(deploy.install, 'source_skills', lambda _: [])
    monkeypatch.setattr(deploy.install, 'TOOL_HOMES', {})
    installed = Mock(return_value=1 if stage == 'install' else 0)
    monkeypatch.setattr(deploy.install, 'main', installed)
    monkeypatch.setattr(deploy, 'verify_local', lambda *_, **kwargs: stage != 'verify')
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        is_check = command[0] == sys.executable
        code = int(stage == ('check' if is_check else 'account'))
        return subprocess.CompletedProcess(command, code, 'total 1\n' if code and is_check else 'total 0\n', '')

    monkeypatch.setattr(deploy.subprocess, 'run', run)
    # dry-run에는 홈 생성과 검증이 없어 실제 실행 경로는 두 홈을 가짜 객체로 둔다.
    monkeypatch.setattr(deploy.install, 'TOOL_HOMES', {tool:Mock() for tool in deploy.install.TARGETS})
    result = deploy.main([])
    assert result == (0 if stage == 'success' else 1)
    if stage == 'check':
        installed.assert_not_called()
    if stage in ('check', 'install'):
        assert len(calls) == 1


def test_deploy_dry_run_has_no_local_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deploy.install, 'resolve_source', lambda _: Path('/source'))
    monkeypatch.setattr(deploy.install, 'source_skills', lambda _: [])
    installed = Mock(return_value=0)
    monkeypatch.setattr(deploy.install, 'main', installed)
    monkeypatch.setattr(deploy, 'verify_local', lambda *_: pytest.fail('dry-run verification'))
    monkeypatch.setattr(deploy.subprocess, 'run', lambda *a, **k: subprocess.CompletedProcess(a,0,'total 0\n',''))
    assert deploy.main(['--dry-run']) == 0
    assert installed.call_args.args[0] == ['--source','/source','--dry-run']


def test_deploy_cli_invalid_argument_fails() -> None:
    result = subprocess.run([sys.executable, str(SCRIPTS/'deploy.py'), '--unknown'], capture_output=True, text=True)
    assert result.returncode == 2
