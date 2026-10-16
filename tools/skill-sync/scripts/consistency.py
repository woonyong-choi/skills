"""스킬 문서의 Markdown 형식, 참조, 용어, 규칙 복제, 스크립트 머리를 검사한다. 기준: ../references/consistency.md."""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit

FENCE = re.compile(r'^\s*(`{3,}|~{3,})(.*)$')
REFERENCE = re.compile(r'\([^)]*[a-z]+(?:-[a-z]+)+[^)]*\)|\[[^]]+\]\([^)]+\)|[a-z][a-z0-9-]* `references/[^`]+\.md`')
DASHES = ('—', '―')  # 엠 대시, 가로 막대
# 스킬 이름을 굵게 가리키는 자리: `**git-issue** 스킬`, `**prove-it-works** 원칙 스킬`
SKILL_MENTION = re.compile(r'\*\*([a-z][a-z0-9]*(?:-[a-z0-9]+)*)\*\* (원칙 )?스킬')
# 이 저장소 밖에서 오는 스킬. 이름으로 가리켜도 저장소 안에 폴더가 없다
EXTERNAL_SKILLS = ('skill-creator',)
# 제품 이름. 명령·확장자·환경 변수는 인라인 코드로 쓰므로 검사 밖이다
PRODUCT_TERMS = {'ThinkFlow': 'Torso', '띵스플로우': 'Torso'}


def documents(skill: Path) -> list[Path]:
    """검사할 문서. SKILL.md, references와 playbooks 아래 Markdown."""
    return [skill / 'SKILL.md', *sorted((skill / 'references').rglob('*.md')), *sorted((skill / 'playbooks').rglob('*.md'))]


def prose_lines(text: str) -> list[tuple[int, str]]:
    rows = []
    fence = ''
    for number, line in enumerate(text.splitlines(), 1):
        match = FENCE.match(line)
        if match:
            marker = match[1]
            if not fence:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence) and not match[2].strip():
                fence = ''
            continue
        if not fence and not line.lstrip().startswith('>'):
            rows.append((number, line))
    return rows


def body_offset(document: Path, text: str) -> tuple[str, int]:
    """SKILL.md는 frontmatter를 떼고 (본문, 뗀 줄 수)를 돌려준다."""
    if document.name != 'SKILL.md' or not text.startswith('---\n'):
        return text, 0
    end = text.find('\n---\n', 3)
    if end < 0:
        return text, 0
    head = text[:end + 5]
    return text[end + 5:], head.count('\n')


def read_terms(skills: dict[str, Path]) -> dict[str, str]:
    owner = skills.get('repo-docs')
    terms = dict(PRODUCT_TERMS)
    if owner is None:
        return terms
    text = (owner / 'references' / 'writing.md').read_text(encoding='utf-8')
    section = text.split('## 용어\n', 1)[1].split('\n## ', 1)[0]
    for _, line in prose_lines(section):
        if not line.startswith('- ') or ' → ' not in line:
            continue
        cells = line[2:].split(' → ', 1)
        if len(cells) != 2:
            continue
        for term in cells[1].split(', '):
            terms[term.split('(')[0]] = cells[0]
    return terms


def check_references(path: Path, text: str, skills: dict[str, Path]) -> list[str]:
    errors = []
    for number, line in prose_lines(text):
        targets = []
        prose = re.sub(r'`[^`]*`', '', line)
        for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)', prose):
            url = urlsplit(link)
            if url.scheme == 'file' or (not url.scheme and link.startswith('/')):
                errors.append(f'참조 링크: {number}: 절대 경로 {link}')
                continue
            if url.scheme or url.netloc or '{' in link:
                continue
            targets.append((path.parent / unquote(url.path) if url.path else path, unquote(url.fragment)))
        for name, relative in re.findall(r'([a-z][a-z0-9-]*) `(references/[^`]+\.md)`', line):
            if name not in skills:
                errors.append(f'참조 링크: {number}: 없는 스킬 {name}')
                continue
            targets.append((skills[name] / relative, ''))
        for name, _ in SKILL_MENTION.findall(prose):
            if name not in skills and f'principle-{name}' not in skills and name not in EXTERNAL_SKILLS:
                errors.append(f'참조 스킬: {number}: 없는 스킬 {name}')
        for target, anchor in targets:
            if not target.is_file():
                errors.append(f'참조 링크: {number}: 없는 파일 {target}')
                continue
            if not anchor:
                continue
            headings = [row.lstrip('#').strip().lower() for _, row in prose_lines(target.read_text(encoding='utf-8')) if row.startswith('#')]
            anchors = {re.sub(r'[^\w\- ]', '', heading.replace('`', '')).replace(' ', '-') for heading in headings}
            if anchor not in anchors:
                errors.append(f'참조 링크: {number}: 없는 절 {target}#{anchor}')
    return errors


def check_markdown(text: str, offset: int = 0) -> list[str]:
    """코드 울타리 언어 표기, 줄 끝 공백. 코드 블록 안 줄도 본다."""
    errors = []
    fence = ''
    for number, line in enumerate(text.splitlines(), 1 + offset):
        if line != line.rstrip():
            errors.append(f'줄 끝 공백: {number}')
        match = FENCE.match(line)
        if not match:
            continue
        marker, info = match[1], match[2].strip()
        if not fence:
            fence = marker
            if not info:
                errors.append(f'코드 울타리: {number}: 언어 표기 없음')
        elif marker[0] == fence[0] and len(marker) >= len(fence) and not info:
            fence = ''
    return errors


def check_prose(text: str, terms: dict[str, str], offset: int = 0) -> list[str]:
    errors = []
    headings = set()
    previous_level, titled = 1, False
    for number, line in prose_lines(text):
        number += offset
        heading = re.match(r'^(#{1,6}) (.+)$', line)
        if heading:
            level, title = len(heading[1]), heading[2]
            if level > previous_level + 1:
                errors.append(f'절 구조: {number}: 제목 단계 생략')
            if level == 1 and titled:
                errors.append(f'절 구조: {number}: # 제목 둘 이상')
            titled = titled or level == 1
            if level == 2 and title in headings:
                errors.append(f'절 구조: {number}: 중복 절 {title}')
            if level == 2:
                headings.add(title)
            previous_level = level
        if re.match(r'^\s*(?:[*+] |\d+\) )', line):
            errors.append(f'목록 기호: {number}: - 또는 1. 사용')
        visible = re.sub(r'`[^`]*`|\]\([^)]+\)', '', line)
        if any(dash in visible for dash in DASHES):
            errors.append(f'엠 대시: {number}')
        # 큰따옴표 안은 인용한 나쁜 예라 제외한다.
        if re.search(r'\*\*[^*\n]+:\*\*', re.sub(r'"[^"]*"', '', visible)):
            errors.append(f'굵은 머리말: {number}: **이름.** 형식 사용')
        # 금지어 정의 자체를 잘못된 용어 사용으로 판정하지 않는다.
        if any(line.startswith(f'- {good} → {bad}') for bad, good in terms.items()):
            continue
        for bad, good in terms.items():
            if re.search(r'(?<![\w])' + re.escape(bad) + r'(?:은|는|이|가|을|를|의|와|과|에|로|도|만|부터|에서|처럼|보다|마다|이면|라면)?(?![\w])', visible):
                errors.append(f'용어 불일치: {number}: {bad} → {good}')
    return errors


def collect_rules(text: str, *, include_intro: bool = False) -> list[tuple[int, str]]:
    rules = []
    in_body = include_intro
    for number, line in prose_lines(text):
        if line.startswith('## '):
            in_body = True
        if not in_body or REFERENCE.search(line):
            continue
        match = re.match(r'^\s*(?:- |\d+\. )(.+)$', line)
        if match:
            rule = match[1]
        elif line.startswith('|') and not re.fullmatch(r'[| :\-]+', line):
            rule = line
        else:
            continue
        # 규범 문장만 비교하여 단순 항목명·표 머리의 중복을 제외한다.
        if len(re.sub(r'\s', '', rule)) >= 20 and (match or re.search(r'금지|필수|우선|만 허용|만 사용|않는다|반드시', rule)):
            rules.append((number, re.sub(r'\s+', ' ', rule).strip().rstrip('.')))
    return rules


def check_script(path: Path) -> list[str]:
    text = path.read_text(encoding='utf-8')
    if path.suffix == '.py':
        tree = ast.parse(text)
        header = ast.get_docstring(tree) or ''
        is_cli = any(isinstance(node, ast.If) and '__name__' in ast.unparse(node.test) for node in tree.body)
    else:
        header = text.split('import ', 1)[0]
        is_cli = 'process.argv' in text
    errors = []
    if is_cli:
        for label in ('인자', '출력'):
            if not re.search(r'(?:^|\n)(?:// )?' + label + r':[ \t]*\S', header):
                errors.append(f'스크립트 {label} 형식: 파일 머리에 {label}: 설명 필수')
    return [f'{error} ({path.name})' for error in errors]


def check_consistency(paths: list[Path]) -> dict[Path, list[str]]:
    """모든 스킬에 같은 검사를 적용하고 스킬 SKILL.md 경로별 위반 목록을 돌려준다."""
    skills = {path.parent.name: path.parent for path in paths}
    terms = read_terms(skills)
    errors = {path: [] for path in paths}
    duplicates = defaultdict(list)
    for path in paths:
        for document in documents(path.parent):
            text = document.read_text(encoding='utf-8')
            body, offset = body_offset(document, text)
            label = document.relative_to(path.parent)
            found = check_markdown(text) + check_prose(body, terms, offset) + check_references(document, text, skills)
            errors[path].extend(f'{error} ({label})' for error in found)
            for line, rule in collect_rules(text, include_intro=document != path):
                duplicates[rule].append((path, f'{label}:{line}'))
        for script in sorted((path.parent / 'scripts').rglob('*')):
            if script.suffix not in ('.py', '.js', '.mjs') or script.name.startswith('test_') or {'__pycache__', 'node_modules'} & set(script.parts):
                continue
            errors[path].extend(check_script(script))
    for rule, locations in duplicates.items():
        if len({path for path, _ in locations}) < 2:
            continue
        owners = ', '.join(f'{path.parent.name}:{line}' for path, line in locations)
        for path, line in locations:
            errors[path].append(f'규칙 복제: {line}: {owners}: {rule}')
    return errors
