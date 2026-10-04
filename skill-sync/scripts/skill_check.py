import argparse
import json
import os
import re
import sys
from pathlib import Path

NOUN_OK = ('흐름', '알림', '없음', '다음', '포함', '결함', '마음', '처음', '이름', '모음', '요금', '그림', '묶음', '느낌', '믿음', '물음', '걸음', '기본값', '보관함', '수신함')
NAME_OK = ('안 함', '막힘')  # 상태 이름
BAD_END = re.compile(r'(다|함|음|임|됨|봄|름|룸|듦|눔|힘|움|씀|셈|뺌|김|춤|침|줌|둠|꿈|옮|듬|숨|엶|앎|삶|짐|킴|림|핌|닮)$')

# cost: time O(n·k), heap O(n), stack O(1), io 1
# vars: n = SKILL.md 줄 수, k = 다른 스킬 이름 수
# basis: estimate
def check(path, names):
    errs = []
    s = open(path, encoding='utf-8').read()
    lines = s.split('\n')
    me = os.path.basename(os.path.dirname(path))
    m = re.search(r'^description: "(.*)"$', s, re.M)
    if not m:
        errs.append('description 형식')
    else:
        d = m.group(1)
        for n in names:
            if n != me and re.search(r'(?<![\w-])' + re.escape(n) + r'(?![a-z-])', d):
                errs.append('description에 다른 스킬 이름: ' + n)
        if '함께' in d:
            errs.append('description에 함께')
    if not re.search(r'^name: [a-z0-9-]+$', s, re.M):
        errs.append('name 형식')
    # header block
    frontmatter = s.split('---', 2)
    if len(frontmatter) != 3 or not s.startswith('---\n'):
        return errs + ['frontmatter 형식']
    name_match = re.search(r'^name: ([a-z0-9-]+)$', frontmatter[1], re.M)
    if name_match and name_match.group(1) != me:
        errs.append('name과 폴더 불일치')
    body = frontmatter[2].lstrip('\n').split('\n')
    if not body[0].startswith('# '):
        errs.append('제목 없음')
    head = [l for l in body[1:6] if l.startswith('- ')]
    if not head or head[0] not in ('- 저장소 안에 같은 역할의 규칙이 있으면 그것 우선. 없으면 이 스킬이 다른 규칙보다 우선', '- 사용자 지시를 먼저 적용. 해당 주제의 사용자 지시가 없으면 작업 대상 저장소의 같은 주제 규칙 파일(예: `AGENTS.md`, `CONTRIBUTING.md`) 적용. 둘 다 없으면 이 스킬 적용. 다른 스킬과 겹치는 규칙은 머리의 연결에 적힌 스킬 중 그 규칙을 정한 스킬 적용'):
        errs.append('머리 1줄')
    if len(head) < 2 or not (head[1].startswith('- 기반: ') or head[1].startswith('- 범위: ')):
        errs.append('머리 2줄')
    for line in head:
        targets = []
        if line.startswith('- 기반: '):
            targets.extend(line.split(': ', 1)[1].split(' 먼저 적용')[0].split(', '))
        if line.startswith('- 필요할 때만 읽기: '):
            for clause in line.split(';'):
                if '→' in clause:
                    targets.extend(re.findall(r'[a-z][a-z0-9-]*(?:\*)?', clause.split('→', 1)[1]))
        for target in targets:
            if target == 'git-*':
                continue
            if target not in names:
                errs.append('없는 스킬 참조: ' + target)
    agent = Path(path).parent / 'agents' / 'openai.yaml'
    if not agent.is_file():
        errs.append('agent 없음')
    else:
        metadata = agent.read_text(encoding='utf-8')
        for key in ('display_name', 'short_description', 'default_prompt'):
            if not re.search(r'^  ' + key + r': .+', metadata, re.M):
                errs.append('agent 필드 없음: ' + key)
        if not re.search(r'\$' + re.escape(me) + r'(?![a-z0-9-])', metadata):
            errs.append('agent 호출 이름 불일치')
    fl = 0
    for i, l in enumerate(lines, 1):
        if fl == 0 and l.startswith('```'):
            fl = len(l) - len(l.lstrip('`'))
            continue
        if fl and re.fullmatch('`{%d}' % fl, l.strip()):
            fl = 0
            continue
        if fl or i <= 4 or not l.strip() or l.startswith('#') or l.startswith('name:') or l.startswith('description:') or l == '---':
            continue
        t = re.sub(r'`[^`]*`', '', l)
        cells = [c.strip() for c in t.split('|')] if t.startswith('|') else [t]
        for c in cells:
            c = re.sub(r'^[-0-9. ]+', '', c).strip().rstrip('.').strip()
            c = re.sub(r'\([^()]*\)$', '', c).strip()
            if not c or set(c) <= set('-: '):
                continue
            if c in NAME_OK:
                continue
            w = c.split()[-1]
            if BAD_END.search(w) and not w.endswith(NOUN_OK):
                errs.append(f'{i}: 끝말 {w}')
    return errs

# cost: time O(s·n·k), heap O(s + n), stack O(1), io O(s)
# vars: s = 스킬 수, n = 스킬 줄 수, k = 스킬 이름 수
# basis: estimate
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', action='store_true')
    parser.add_argument('root', type=Path)
    args = parser.parse_args(argv)
    paths = sorted(args.root.glob('*/SKILL.md')) if args.root.is_dir() else []
    if not paths:
        print('검사할 SKILL.md 없음', file=sys.stderr)
        return 2
    names = [path.parent.name for path in paths]
    total, kinds = 0, {}
    try:
        for path in paths:
            errors = check(str(path), names)
            total += len(errors)
            for error in errors:
                kind = '끝말' if '끝말' in error else error.split(':')[0]
                kinds[kind] = kinds.get(kind, 0) + 1
            if errors and not args.json:
                print(path.parent.name, len(errors), errors)
    except (OSError, UnicodeError, ValueError) as error:
        print(f'검사 입력 오류: {error}', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({**kinds, 'total': total}, ensure_ascii=False))
    else:
        print('total', total)
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
