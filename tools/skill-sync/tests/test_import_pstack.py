"""pstack 가져오기: 원문 보존, name 정규화, Codex 수동 호출 파일, 형식 검사 계약."""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import import_pstack  # noqa: E402
import skill_check  # noqa: E402

MANUAL = '---\nname: Alpha Mode\ndescription: Use for /alpha-mode.\ndisable-model-invocation: true\n---\n\n# Alpha\n\nbody\n'
AUTO = '---\nname: beta\ndescription: Use when beta.\n---\n\n# Beta\n'


# cost: time O(f), heap O(f), stack O(1), io O(f)
# vars: f = 만드는 파일 수
# basis: estimate
def upstream(root: Path) -> Path:
    source = root / 'plugins'
    for name, text in (('alpha-mode', MANUAL), ('beta', AUTO)):
        (source / 'pstack/skills' / name).mkdir(parents=True)
        (source / 'pstack/skills' / name / 'SKILL.md').write_text(text, encoding='utf-8')
    (source / 'pstack/skills/beta/references').mkdir()
    (source / 'pstack/skills/beta/references/x.md').write_text('ref\n', encoding='utf-8')
    (source / 'pstack/agents').mkdir()
    (source / 'pstack/agents/helper.md').write_text('agent\n', encoding='utf-8')
    (source / 'pstack/plugin.json').write_text(json.dumps({'name': 'pstack', 'version': '9.9.9'}), encoding='utf-8')
    for args in (['init', '-q'], ['add', '.'], ['-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'init']):
        subprocess.run(['git', '-C', str(source), *args], check=True, capture_output=True)
    return source


def test_import_keeps_text_normalizes_name_and_marks_manual_skills(tmp_path: Path) -> None:
    source, dest = upstream(tmp_path), tmp_path / 'repo'
    dest.mkdir()
    assert import_pstack.main(['--source', str(source), '--dest', str(dest)]) == 0
    alpha = (dest / 'pstack/alpha-mode/SKILL.md').read_text(encoding='utf-8')
    assert alpha == MANUAL.replace('name: Alpha Mode', 'name: alpha-mode')
    assert (dest / 'pstack/beta/SKILL.md').read_text(encoding='utf-8') == AUTO
    assert (dest / 'pstack/beta/references/x.md').is_file()
    assert 'allow_implicit_invocation: false' in (dest / 'pstack/alpha-mode/agents/openai.yaml').read_text(encoding='utf-8')
    assert not (dest / 'pstack/beta/agents').exists()
    assert (dest / 'pstack/_upstream/agents/helper.md').is_file()
    assert json.loads((dest / 'pstack/beta/UPSTREAM.json').read_text(encoding='utf-8'))['path'] == 'pstack/skills/beta'
    record = json.loads((dest / 'pstack/_upstream/SOURCE.json').read_text(encoding='utf-8'))
    assert record['version'] == '9.9.9' and record['skills'] == 2 and len(record['commit']) == 40
    assert record['patches'] == ['alpha-mode/SKILL.md: name을 폴더 이름으로']
    assert skill_check.check_vendored(dest / 'pstack/alpha-mode/SKILL.md') == []


def test_reimport_replaces_previous_copy(tmp_path: Path) -> None:
    source, dest = upstream(tmp_path), tmp_path / 'repo'
    (dest / 'pstack/stale').mkdir(parents=True)
    assert import_pstack.main(['--source', str(source), '--dest', str(dest)]) == 0
    assert not (dest / 'pstack/stale').exists()


def test_vendored_check_reports_name_mismatch(tmp_path: Path) -> None:
    skill = tmp_path / 'pstack/alpha-mode'
    skill.mkdir(parents=True)
    (skill / 'SKILL.md').write_text(MANUAL, encoding='utf-8')
    assert skill_check.check_vendored(skill / 'SKILL.md') == ['원본 name: 폴더 이름과 다름']
