"""pstack 원본 갱신: 이식본 보존, 바뀐 원본 파일 목록, 원본 표시 스킬 형식 검사 계약."""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import import_pstack  # noqa: E402
import skill_check  # noqa: E402

SKILL = '---\nname: alpha\ndescription: Use for /alpha.\ndisable-model-invocation: true\n---\n\n# Alpha\n'


# cost: time O(f), heap O(f), stack O(1), io O(f)
# vars: f = 만드는 파일 수
# basis: estimate
def upstream(root: Path, text: str = SKILL) -> Path:
    source = root / 'plugins'
    (source / 'pstack/skills/alpha').mkdir(parents=True, exist_ok=True)
    (source / 'pstack/skills/alpha/SKILL.md').write_text(text, encoding='utf-8')
    (source / 'pstack/plugin.json').write_text(json.dumps({'name': 'pstack', 'version': '9.9.9'}), encoding='utf-8')
    for args in (['init', '-q'], ['add', '.'], ['-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'c']):
        subprocess.run(['git', '-C', str(source), *args], check=True, capture_output=True)
    return source


def test_refresh_keeps_translation_and_lists_changes(tmp_path: Path, capsys) -> None:
    dest = tmp_path / 'repo'
    (dest / 'pstack/alpha').mkdir(parents=True)
    (dest / 'pstack/alpha/SKILL.md').write_text('한국어 이식본\n', encoding='utf-8')
    source = upstream(tmp_path)
    assert import_pstack.main(['--source', str(source), '--dest', str(dest)]) == 0
    assert '+ skills/alpha/SKILL.md' in capsys.readouterr().out
    upstream(tmp_path, SKILL + 'new line\n')
    assert import_pstack.main(['--source', str(source), '--dest', str(dest)]) == 0
    out = capsys.readouterr().out
    assert '~ skills/alpha/SKILL.md' in out and '바뀐 파일 1개' in out
    assert (dest / 'pstack/alpha/SKILL.md').read_text(encoding='utf-8') == '한국어 이식본\n'
    record = json.loads((dest / 'pstack/_upstream/SOURCE.json').read_text(encoding='utf-8'))
    assert record['version'] == '9.9.9' and record['skills'] == 1 and len(record['commit']) == 40


def test_vendored_check_reports_name_mismatch(tmp_path: Path) -> None:
    skill = tmp_path / 'pstack/beta'
    skill.mkdir(parents=True)
    (skill / 'SKILL.md').write_text(SKILL, encoding='utf-8')
    assert skill_check.check_vendored(skill / 'SKILL.md') == ['원본 name: 폴더 이름과 다름']
    (skill / 'SKILL.md').write_text(SKILL.replace('name: alpha', 'name: beta'), encoding='utf-8')
    assert skill_check.check_vendored(skill / 'SKILL.md') == []
