import re, sys, glob, os

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
    body = s.split('---', 2)[2].lstrip('\n').split('\n')
    if not body[0].startswith('# '):
        errs.append('제목 없음')
    head = [l for l in body[1:6] if l.startswith('- ')]
    if not head or head[0] != '- 저장소 안에 같은 역할의 규칙이 있으면 그것 우선. 없으면 이 스킬이 다른 규칙보다 우선':
        errs.append('머리 1줄')
    if len(head) < 2 or not (head[1].startswith('- 기반: ') or head[1].startswith('- 범위: ')):
        errs.append('머리 2줄')
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

if __name__ == '__main__':
    as_json = sys.argv[1] == '--json'
    root = sys.argv[-1]
    names = [os.path.basename(os.path.dirname(p)) for p in glob.glob(root + '/*/SKILL.md')]
    tot, kinds = 0, {}
    for p in sorted(glob.glob(root + '/*/SKILL.md')):
        e = check(p, names)
        tot += len(e)
        for x in e:
            k = '끝말' if '끝말' in x else x.split(':')[0]
            kinds[k] = kinds.get(k, 0) + 1
        if e and not as_json:
            print(p.split('/')[-2], len(e), e[:12])
    if as_json:
        import json
        kinds['total'] = tot
        print(json.dumps(kinds, ensure_ascii=False))
    else:
        print('total', tot)
