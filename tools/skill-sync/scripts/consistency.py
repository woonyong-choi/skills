"""스킬 일관성의 정적 규칙을 검사한다. 기준: ../references/consistency.md."""

from __future__ import annotations

import ast
import importlib.util
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit

PRIORITY = '- 우선순위: 해당 주제의 사용자 지시 → 저장소 규칙 → 이 스킬. 중복 규칙은 머리에 연결한 정본 스킬 적용'
FENCE = re.compile(r'^\s*(`{3,}|~{3,})')
REFERENCE = re.compile(r'\([^)]*[a-z]+(?:-[a-z]+)+[^)]*\)|\[[^]]+\]\([^)]+\)|[a-z][a-z0-9-]* `references/[^`]+\.md`')
COST = re.compile(r'^time O\([^()]+\)(?: [^,]+)?(?:, O\([^()]+\) worst)?, heap O\([^()]+\), stack O\([^()]+\)(?:, (?:alloc|io|tokens) [^,]+)*$')


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


# cost: time O(n), heap O(n), stack O(1), io 1
# vars: n = 용어 정본 글자 수
# basis: estimate
def read_terms(skills: dict[str, Path]) -> dict[str, str]:
    owner = skills.get('repo-docs')
    if owner is None:
        return {}
    text = (owner / 'references' / 'writing.md').read_text(encoding='utf-8')
    section = text.split('## 용어\n', 1)[1].split('\n## ', 1)[0]
    terms = {}
    for _, line in prose_lines(section):
        if not line.startswith('|'):
            continue
        cells = [cell.strip() for cell in line.strip('|').split('|')]
        if len(cells) != 2 or cells[0] == '쓰는 말' or cells[0].startswith('-'):
            continue
        for term in cells[1].split(', '):
            terms[term.split('(')[0]] = cells[0]
    return terms


# cost: time O(n + b), heap O(n + b), stack O(1), io O(f)
# vars: n = 문서 글자 수, b = 링크 대상 문서 글자 수 합계, f = 링크 수
# basis: estimate
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
        # 정본의 금지어 표는 잘못된 용어를 설명하는 정의이며 사용 문장이 아니다.
        if line.startswith('|') and any(line.startswith(f'| {good} | {bad}') for bad, good in terms.items()):
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


def check_cost_format(text: str) -> list[str]:
    errors = []
    lines = text.splitlines()
    in_block = False
    for index, line in enumerate(lines):
        match = re.match(r'^\s*(?:#|//) cost:\s*(.*)', line)
        comment = re.match(r'^\s*(?:#|//) (\w+):\s*(.*)', line)
        if not comment:
            in_block = False
        if not match or in_block:
            continue
        in_block = True
        fields = defaultdict(list)
        for following in lines[index:]:
            comment = re.match(r'^\s*(?:#|//) (\w+):\s*(.*)', following)
            if not comment:
                break
            fields[comment[1]].append(comment[2])
        cost = ', '.join(fields['cost'])
        if not COST.fullmatch(cost) or re.search(r', (?:alloc|io|tokens) 0(?:,|$)', cost):
            errors.append(f'비용 주석 형식: {index + 1}: time, heap, stack 순서와 O 표기')
        if not re.fullmatch(r'estimate|measured .+', ' '.join(fields['basis'])):
            errors.append(f'비용 주석 형식: {index + 1}: basis 누락 또는 형식')
        expressions = ' '.join(re.findall(r'O\(([^)]+)\)', cost))
        variables = set(re.findall(r'\b[A-Za-z]\b', expressions))
        defined = set(re.findall(r'(?:^|, )([A-Za-z])\s*=', ', '.join(fields['vars'])))
        if variables - defined:
            errors.append(f'비용 주석 형식: {index + 1}: vars 누락 {", ".join(sorted(variables - defined))}')
    return errors


# cost: time O(n), heap O(n), stack O(n), io 1
# vars: n = 스크립트 글자 수와 구문 트리 최대 깊이
# basis: estimate
def check_script(path: Path, cost_checker: object) -> list[str]:
    text = path.read_text(encoding='utf-8')
    if path.suffix == '.py':
        tree = ast.parse(text)
        header = ast.get_docstring(tree) or ''
        is_cli = any(isinstance(node, ast.If) and '__name__' in ast.unparse(node.test) for node in tree.body)
    else:
        header = text.split('import ', 1)[0]
        is_cli = 'process.argv' in text
    errors = check_cost_format(text)
    if is_cli:
        for label in ('인자', '출력'):
            if not re.search(r'(?:^|\n)(?:// )?' + label + r':[ \t]*\S', header):
                errors.append(f'스크립트 {label} 형식: 파일 머리에 {label}: 설명 필수')
    errors.extend(f'비용 주석: {line}: {name}: {reason}' for _, line, name, reason in cost_checker.check_file(str(path)))
    return [f'{error} ({path.name})' for error in errors]


# cost: time O(n), heap O(n), stack O(1), io 1
# vars: n = 검사 모듈 글자 수
# basis: estimate
def load_cost_checker() -> object:
    script = Path(__file__).resolve()
    source = script.parents[3] / 'code' / 'code-style'
    installed = script.parents[2] / 'code-style'
    owner = source if source.is_dir() else installed
    path = owner / 'scripts' / 'check_cost_comments.py'
    spec = importlib.util.spec_from_file_location('skill_cost_checker', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# cost: time O(n·t + b + s²), heap O(n + b), stack O(n), io O(f + l)
# vars: n = 전체 글자 수, t = 용어 수, b = 링크 대상 글자 수 합계, s = 가장 긴 스크립트 줄 수, f = 파일 수, l = 링크 수
# basis: estimate
def check_consistency(paths: list[Path]) -> dict[Path, list[str]]:
    skills = {path.parent.name: path.parent for path in paths}
    terms = read_terms(skills)
    errors = {path: [] for path in paths}
    duplicates = defaultdict(list)
    cost_checker = load_cost_checker()
    for path in paths:
        documents = [path, *sorted((path.parent / 'references').rglob('*.md'))]
        for document in documents:
            text = document.read_text(encoding='utf-8')
            label = document.relative_to(path.parent)
            found = check_prose(text, terms) + check_references(document, text, skills)
            errors[path].extend(f'{error} ({label})' for error in found)
            for line, rule in collect_rules(text, include_intro=document != path):
                duplicates[rule].append((path, f'{label}:{line}'))
        for script in sorted((path.parent / 'scripts').rglob('*')):
            if script.suffix not in ('.py', '.js', '.mjs') or script.name.startswith('test_') or '__pycache__' in script.parts:
                continue
            errors[path].extend(check_script(script, cost_checker))
    for rule, locations in duplicates.items():
        if len({path for path, _ in locations}) < 2:
            continue
        owners = ', '.join(f'{path.parent.name}:{line}' for path, line in locations)
        for path, line in locations:
            errors[path].append(f'규칙 복제: {line}: {owners}: {rule}')
    return errors
