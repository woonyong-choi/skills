"""스킬 일관성의 정적 규칙을 검사한다. 기준: ../references/consistency.md."""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit

PRIORITY = '- 우선순위: 사용자 지시 → 저장소 규칙 → 이 스킬. 범위 밖은 명시한 소유 스킬 적용'
FENCE = re.compile(r'^\s*(`{3,}|~{3,})')
REFERENCE = re.compile(r'\([^)]*[a-z]+(?:-[a-z]+)+[^)]*\)|\[[^]]+\]\([^)]+\)|[a-z][a-z0-9-]* `references/[^`]+\.md`')


def prose_lines(text: str) -> list[tuple[int, str]]:
    rows = []
    fence = ''
    for number, line in enumerate(text.splitlines(), 1):
        match = FENCE.match(line)
        if match:
            marker = match[1]
            if not fence:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = ''
            continue
        if not fence and not line.lstrip().startswith('>'):
            rows.append((number, line))
    return rows


def read_terms(skills: dict[str, Path]) -> dict[str, str]:
    owner = skills.get('repo-docs')
    if owner is None:
        return {}
    text = (owner / 'references' / 'writing.md').read_text(encoding='utf-8')
    section = text.split('## 용어\n', 1)[1].split('\n## ', 1)[0]
    terms = {}
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
            if url.scheme or url.netloc or '{' in link:
                continue
            targets.append((path.parent / unquote(url.path) if url.path else path, unquote(url.fragment)))
        for name, relative in re.findall(r'([a-z][a-z0-9-]*) `(references/[^`]+\.md)`', line):
            if name not in skills:
                errors.append(f'참조 링크: {number}: 없는 스킬 {name}')
                continue
            targets.append((skills[name] / relative, ''))
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


def check_prose(text: str, terms: dict[str, str]) -> list[str]:
    errors = []
    headings = set()
    previous_level = 1
    for number, line in prose_lines(text):
        heading = re.match(r'^(#{1,6}) (.+)$', line)
        if heading:
            level, title = len(heading[1]), heading[2]
            if level > previous_level + 1:
                errors.append(f'절 구조: {number}: 제목 단계 생략')
            if level == 2 and title in headings:
                errors.append(f'절 구조: {number}: 중복 절 {title}')
            if level == 2:
                headings.add(title)
            previous_level = level
        if re.fullmatch(r'\s*\|[| :\-]+\|\s*', line):
            errors.append(f'지시 형식: {number}: 표 대신 조건별 목록 사용')
        # 금지어 정의 자체를 잘못된 용어 사용으로 판정하지 않는다.
        if any(line.startswith(f'- {good} → {bad}') for bad, good in terms.items()):
            continue
        visible = re.sub(r'`[^`]*`|\]\([^)]+\)', '', line)
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
        if len(re.sub(r'\s', '', rule)) >= 20 and (match or re.search(r'금지|필수|우선|만 허용|만 사용', rule)):
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


def check_consistency(paths: list[Path], linkable: list[Path] | None = None) -> dict[Path, list[str]]:
    """paths는 문체·규칙 검사 대상, linkable은 참조 링크로 가리킬 수 있는 추가 스킬(형식만 검사하는 스킬 포함)"""
    skills = {path.parent.name: path.parent for path in paths}
    terms = read_terms(skills)
    targets = {**{path.parent.name: path.parent for path in linkable or []}, **skills}
    errors = {path: [] for path in paths}
    duplicates = defaultdict(list)
    for path in paths:
        documents = [path, *sorted((path.parent / 'references').rglob('*.md'))]
        for document in documents:
            text = document.read_text(encoding='utf-8')
            label = document.relative_to(path.parent)
            found = check_prose(text, terms) + check_references(document, text, targets)
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
