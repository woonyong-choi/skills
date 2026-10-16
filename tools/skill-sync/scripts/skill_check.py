"""스킬의 형식과 일관성을 검사한다.

인자: root 원본 저장소, --json 집계 JSON 출력
출력: 스킬별 위반과 total N 또는 JSON, 종료 0 통과·1 위반·2 입력 오류
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

from install import VENDORED_MARKER, source_skills
from consistency import PRIORITY, check_consistency

NOUN_OK = ('흐름', '알림', '없음', '다음', '포함', '결함', '마음', '처음', '이름', '모음', '요금', '그림', '묶음', '느낌', '믿음', '물음', '걸음', '기본값', '보관함', '수신함', '책임',
           '지침', '방침', '아침', '도움', '스트림', '크림', '프레임', '타임', '게임', '네임', '스킴', '리듬', '여름', '기름', '소음', '녹음', '발음', '얼음', '덧셈', '뺄셈', '곱셈', '나눗셈', '바다', '판다', '아젠다', '베란다', '캐나다', '잡음', '필름',
           '잠금', '사람', '바람', '팀', '시스템', '아이템', '점', '홈', '그램', '알고리즘', '메커니즘', '폼', '플랫폼')
NOUN_WORD = ('힘', '꿈', '짐', '봄', '줌', '셈', '김', '삶', '춤', '숨', '룸', '침')  # 앞이 붙으면 동사 명사형(막힘·바꿈)이라 낱말 전체 일치만
NAME_OK = ('안 함', '막힘')  # 상태 이름
# authoring.md `-ㅁ`형 금지: 끝 음절 받침 ㅁ·ㄻ 전체(바뀜·들어감·삶). 명사는 NOUN_OK·NOUN_WORD로 제외
M_FINALS = (16, 10)
# 줄 중간 문장 끝: 문장부호와 공백 앞 명사형
MID_SENTENCE = re.compile(r'([가-힣]+)[.;!?](?=\s)')
# 줄 중간 평서형 끝: 문장부호 앞은 `verb_end`, 공백 앞은 `-ㄴ다`·`-는다`·`이다`·`있다`·`없다`. `마다`·`보다` 조사 제외
CLAUSE = re.compile(r'([가-힣]+다)(?:([.,;:!?)\]])|(?=\s))')
PARTICLE = ('마다', '보다')
# 받침 ㅁ·ㅇ 뒤 `다`는 서술격 조사 축약(결과다)이 될 수 없어 명사(람다)로 보되, 이 동사 끝은 평서형
NASAL_VERB_END = ('남다', '담다', '삼다', '넘다', '참다', '숨다', '심다', '감다')

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
        if not re.search(r"때 [^.]*?사용\.", d):
            errs.append("description 사용 조건 형식")
        elif not d.endswith("사용."):
            errs.append("description 사용. 뒤 글자")
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
    if not head or head[0] != PRIORITY:
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
                    destination = re.sub(r'`[^`]+`', '', clause.split('→', 1)[1])
                    targets.extend(re.findall(r'[a-z][a-z0-9-]*(?:\*)?', destination))
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
    errs.extend(f'{i}: 끝말 {w}' for i, w in bad_endings(lines, 4))
    for ref in sorted(Path(path).parent.glob('references/*.md')):
        ref_lines = ref.read_text(encoding='utf-8').split('\n')
        errs.extend(f'references/{ref.name}:{i}: 끝말 {w}' for i, w in bad_endings(ref_lines, 0))
    return errs

# cost: time O(n·w), heap O(n), stack O(1)
# vars: n = 줄 수, w = 줄 길이
# basis: estimate
def bad_endings(lines, skip):
    """코드 밖 줄 끝·칸 끝·줄 중간 평서형 끝의 금지 끝말을 (줄 번호, 낱말)로 돌려준다."""
    found = []
    fl = 0
    for i, l in enumerate(lines, 1):
        if fl == 0 and l.startswith('```'):
            fl = len(l) - len(l.lstrip('`'))
            continue
        if fl and re.fullmatch('`{%d}' % fl, l.strip()):
            fl = 0
            continue
        if fl or i <= skip or not l.strip() or l.startswith('#') or l.startswith('name:') or l.startswith('description:') or l == '---':
            continue
        t = re.sub(r'[*_]', '', re.sub(r'`[^`]*`', '', l))  # 강조 표시(`*`·`_`) 제거 후 낱말 검사
        words = []
        cells = [c.strip() for c in t.split('|')] if t.startswith('|') else [t]
        for c in cells:
            c = re.sub(r'^[-0-9. ]+', '', c).strip().rstrip('.').strip()
            c = re.sub(r'\([^()]*\)$', '', c).strip()
            if not c or set(c) <= set('-: ') or c in NAME_OK:
                continue
            w = c.split()[-1]
            if verb_end(w) or nominal_end(w):
                words.append(w)
        for m in CLAUSE.finditer(re.sub(r'\]\([^)]*\)', ']', t)):
            w = m.group(1)
            flagged = verb_end(w) if m.group(2) else declarative(w) and not w.endswith(PARTICLE)
            if flagged:
                words.append(w)
        words.extend(m.group(1) for m in MID_SENTENCE.finditer(t) if nominal_end(m.group(1)))
        found.extend((i, w) for w in dict.fromkeys(words))
    return found

# cost: time O(1), heap O(1), stack O(1)
# vars: 없음
# basis: estimate
def nominal_end(word):
    """`-ㅁ`형 끝(받침 ㅁ·ㄻ)인지. 예외 명사(없음·이름·잡음)와 단독 명사(힘·꿈) 제외."""
    last = word[-1:] or ' '
    if not '가' <= last <= '힣' or (ord(last) - 0xAC00) % 28 not in M_FINALS:
        return False
    return not word.endswith(NOUN_OK) and word not in NOUN_WORD and word not in NAME_OK


# cost: time O(1), heap O(1), stack O(1)
# vars: 없음
# basis: estimate
def verb_end(word):
    """평서형 `-다` 끝인지. 조사(마다), 예외 명사(바다), 받침 ㅁ·ㅇ 뒤 명사(람다) 제외."""
    if not word.endswith('다') or len(word) < 2 or word.endswith(PARTICLE + NOUN_OK):
        return False
    prev = word[-2]
    final = (ord(prev) - 0xAC00) % 28 if '가' <= prev <= '힣' else 0
    return final not in (16, 21) or word.endswith(NASAL_VERB_END)

# cost: time O(1), heap O(1), stack O(1)
# vars: 없음
# basis: estimate
def declarative(word):
    """공백 앞에서도 평서형으로 보는 `-ㄴ다`·`-는다`·`이다`·`있다`·`없다` 끝인지."""
    if word.endswith(('는다', '이다', '있다', '없다')):
        return True
    prev = word[-2] if len(word) > 1 else ''
    return '가' <= prev <= '힣' and (ord(prev) - 0xAC00) % 28 == 4

# cost: time O(n), heap O(n), stack O(1), io 1
# vars: n = SKILL.md 바이트
# basis: estimate
def check_vendored(path: Path) -> list[str]:
    """가져온 원본 스킬의 형식만 검사: frontmatter, name과 폴더 일치, description 1~1024자"""
    text = path.read_text(encoding='utf-8')
    parts = text.split('---', 2)
    if not text.startswith('---\n') or len(parts) != 3:
        return ['원본 frontmatter 형식']
    errors = []
    name = re.search(r'^name: ([a-z0-9-]+)$', parts[1], re.M)
    if not name or name.group(1) != path.parent.name:
        errors.append('원본 name: 폴더 이름과 다름')
    description = re.search(r'^description: (.+)$', parts[1], re.M)
    if not description:
        errors.append('원본 description: 없음')
    elif description.group(1).strip() not in ('>-', '>', '|') and len(description.group(1).strip().strip('"')) > 1024:
        errors.append('원본 description: 1024자 초과')
    return errors


# cost: time O(s·n·k), heap O(s + n), stack O(1), io O(s)
# vars: s = 스킬 수, n = 스킬 줄 수, k = 스킬 이름 수
# basis: estimate
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', action='store_true')
    parser.add_argument('root', type=Path)
    args = parser.parse_args(argv)
    try:
        skills = source_skills(args.root)
        paths = [skill / 'SKILL.md' for skill in skills if not (skill / VENDORED_MARKER).is_file()]
        vendored = [skill / 'SKILL.md' for skill in skills if (skill / VENDORED_MARKER).is_file()]
    except (OSError, ValueError) as error:
        print(f'검사 입력 오류: {error}', file=sys.stderr)
        return 2
    if not paths:
        print('검사할 SKILL.md 없음', file=sys.stderr)
        return 2
    names = [path.parent.name for path in paths]
    total, kinds = 0, {}
    try:
        for path in vendored:
            errors = check_vendored(path)
            total += len(errors)
            for error in errors:
                kinds[error.split(':')[0]] = kinds.get(error.split(':')[0], 0) + 1
            if errors and not args.json:
                print(path.parent.name, len(errors), errors)
        consistency = check_consistency(paths)
        for path in paths:
            errors = check(str(path), names) + consistency[path]
            total += len(errors)
            for error in errors:
                kind = '끝말' if '끝말' in error else error.split(':')[0]
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
