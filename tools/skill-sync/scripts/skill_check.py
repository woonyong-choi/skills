"""스킬의 형식과 일관성을 검사한다. 기준: ../references/authoring.md, ../references/consistency.md.

인자: root 원본 저장소, --json 집계 JSON 출력
출력: 스킬별 위반과 total N 또는 JSON, 종료 0 통과·1 위반·2 입력 오류
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from install import source_skills
from consistency import check_consistency

KEYS = ('name', 'description', 'disable-model-invocation', 'user-invocable')
FLAGS = ('disable-model-invocation', 'user-invocable')
DESCRIPTION_LIMIT = 1024
HANGUL = re.compile(r'[가-힣]')
# 제목 다음에 와서는 안 되는 줄: 제목, 목록, 표, 코드 울타리, 인용
NOT_PARAGRAPH = re.compile(r'^(#|- |\* |\+ |\d+\. |\||```|~~~|>)')


def frontmatter(text: str) -> tuple[dict[str, str], str] | None:
    """(칸 이름 → 값 원문, 본문)을 돌려준다. 여는·닫는 `---`가 없으면 None."""
    if not text.startswith('---\n'):
        return None
    end = text.find('\n---\n', 3)
    if end < 0:
        return None
    fields = {}
    for line in text[4:end].split('\n'):
        match = re.match(r'^([A-Za-z][\w-]*):(.*)$', line)
        if match:
            fields[match[1]] = match[2].strip()
        elif line.strip():
            fields.setdefault('', line)  # 들여쓴 줄(여러 줄 값)
    return fields, text[end + 5:]


def check_frontmatter(fields: dict[str, str], folder: str) -> list[str]:
    errors = []
    if '' in fields:
        errors.append('frontmatter: 한 줄 값만 허용')
    for key in fields:
        if key and key not in KEYS:
            errors.append(f'frontmatter: 없는 칸 {key}')
    name = fields.get('name')
    if not name or not re.fullmatch(r'[a-z0-9-]+', name):
        errors.append('name: 영어 소문자·숫자·- 형식')
    elif name != folder:
        errors.append('name: 폴더 이름과 다름')
    for flag in FLAGS:
        if flag in fields and fields[flag] not in ('true', 'false'):
            errors.append(f'frontmatter: {flag} 값은 true 또는 false')
    if fields.get('user-invocable') == 'false' and fields.get('disable-model-invocation') != 'true':
        errors.append('frontmatter: user-invocable false는 disable-model-invocation true와 함께')
    return errors + check_description(fields.get('description'))


def check_description(raw: str | None) -> list[str]:
    if raw is None:
        return ['description: 없음']
    match = re.fullmatch(r'"((?:[^"\\]|\\.)*)"', raw)
    if not match:
        return ['description: 큰따옴표 한 줄']
    text = match[1]
    errors = []
    if not 1 <= len(text) <= DESCRIPTION_LIMIT:
        errors.append(f'description: 1~{DESCRIPTION_LIMIT}자')
    if not HANGUL.search(text):
        errors.append('description: 한국어 문장')
    if not re.search(r'쓴다\.(?:\s|$)', text):
        errors.append('description: 언제 쓰는지 말하는 문장을 "쓴다."로 끝냄')
    if not text.endswith('.'):
        errors.append('description: 마침표로 끝냄')
    return errors


def check_body(body: str) -> list[str]:
    """`# 제목` 다음 첫 줄이 한 줄 목표 문단인지 본다."""
    lines = [line for line in body.split('\n') if line.strip()]
    if not lines or not lines[0].startswith('# '):
        return ['본문 구조: 첫 줄 # 제목']
    if len(lines) < 2 or NOT_PARAGRAPH.match(lines[1].lstrip()):
        return ['본문 구조: 제목 다음 한 줄 목표 문단']
    return []


def check_agent(skill: Path, explicit_only: bool) -> list[str]:
    """Codex 표시 정보. 명시 호출형이면 암묵 호출도 막아 두 도구의 호출 방식을 맞춘다."""
    agent = skill / 'agents' / 'openai.yaml'
    if not agent.is_file():
        return ['agent: agents/openai.yaml 없음']
    metadata = agent.read_text(encoding='utf-8')
    errors = [f'agent: 필드 없음 {key}' for key in ('display_name', 'short_description', 'default_prompt')
              if not re.search(r'^  ' + key + r': .+', metadata, re.M)]
    if not re.search(r'\$' + re.escape(skill.name) + r'(?![a-z0-9-])', metadata):
        errors.append('agent: 호출 이름 불일치')
    if explicit_only != bool(re.search(r'^  allow_implicit_invocation: false$', metadata, re.M)):
        errors.append('agent: disable-model-invocation과 allow_implicit_invocation 불일치')
    return errors


def check(path: Path) -> list[str]:
    parsed = frontmatter(path.read_text(encoding='utf-8'))
    if parsed is None:
        return ['frontmatter: 여는·닫는 --- 없음']
    fields, body = parsed
    explicit_only = fields.get('disable-model-invocation') == 'true'
    return check_frontmatter(fields, path.parent.name) + check_body(body) + check_agent(path.parent, explicit_only)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', action='store_true')
    parser.add_argument('root', type=Path)
    args = parser.parse_args(argv)
    try:
        paths = [skill / 'SKILL.md' for skill in source_skills(args.root)]
    except (OSError, ValueError) as error:
        print(f'검사 입력 오류: {error}', file=sys.stderr)
        return 2
    if not paths:
        print('검사할 SKILL.md 없음', file=sys.stderr)
        return 2
    total, kinds = 0, {}
    try:
        consistency = check_consistency(paths)
        for path in paths:
            errors = check(path) + consistency[path]
            total += len(errors)
            for error in errors:
                kind = error.split(':')[0]
                kinds[kind] = kinds.get(kind, 0) + 1
            if errors and not args.json:
                print(path.parent.name, len(errors), errors)
    except (OSError, UnicodeError, ValueError, SyntaxError) as error:
        print(f'검사 입력 오류: {error}', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({**kinds, 'total': total}, ensure_ascii=False))
    else:
        print('total', total)
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
