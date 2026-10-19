"""skill_check의 frontmatter·본문 구조·Markdown 판정 경계 계약. 기준: references/authoring.md."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import consistency  # noqa: E402
import skill_check  # noqa: E402
import install  # noqa: E402


@pytest.mark.parametrize('name', ['-alpha', 'alpha-', 'alpha--beta', '-', 'Alpha', 'alpha_beta', 'alpha/beta', 'alpha', 'alpha-2', '0', 'a' * 100])
def test_frontmatter_name_matches_installer(tmp_path: Path, name: str) -> None:
    try:
        install._skill_path(tmp_path, name)
    except ValueError:
        valid = False
    else:
        valid = True

    errors = skill_check.check_frontmatter({'name': name, 'description': '"쓸 때 쓴다."'}, name)

    assert (not errors) == valid


@pytest.mark.parametrize('description', [
    '"커밋 메시지를 쓸 때 쓴다."',
    '"\\"X는 어떻게 동작하나\\" 질문에 쓴다. 아키텍처를 설명한다. 동기는 why를 쓴다."',
    '"디버깅할 때 쓴다. 증상을 처음 잘못된 곳까지 거슬러 올라가 고친다."',
])
def test_description_accepts_use_sentence(description: str) -> None:
    assert skill_check.check_description(description) == []


@pytest.mark.parametrize('description, error', [
    (None, 'description: 없음'),
    ('커밋 메시지를 쓸 때 쓴다.', 'description: 큰따옴표 한 줄'),
    ('>-', 'description: 큰따옴표 한 줄'),
    ('"커밋 메시지를 쓸 때 사용."', 'description: 언제 쓰는지 말하는 문장을 "쓴다."로 끝냄'),
    ('"디버깅할 때 적용한다."', 'description: 언제 쓰는지 말하는 문장을 "쓴다."로 끝냄'),
    ('"Use when writing commits. 쓴다."', None),
    ('"Use when writing commit messages."', 'description: 한국어 문장'),
    ('"커밋할 때 쓴다. 템플릿을 채운다"', 'description: 마침표로 끝냄'),
    ('"' + '가' * 1030 + ' 쓴다."', 'description: 1~1024자'),
], ids=lambda value: str(value)[:30])
def test_description_rejects_other_forms(description: str | None, error: str | None) -> None:
    errors = skill_check.check_description(description)
    assert (error in errors) if error else errors == []


@pytest.mark.parametrize('fields, error', [
    ({'name': 'beta', 'description': '"쓸 때 쓴다."'}, 'name: 폴더 이름과 다름'),
    ({'name': 'Alpha', 'description': '"쓸 때 쓴다."'}, 'name: 영어 소문자·숫자·- 형식'),
    ({'name': 'alpha', 'description': '"쓸 때 쓴다."', 'license': 'MIT'}, 'frontmatter: 없는 칸 license'),
    ({'name': 'alpha', 'description': '"쓸 때 쓴다."', 'user-invocable': 'false'},
     'frontmatter: user-invocable false는 disable-model-invocation true와 함께'),
    ({'name': 'alpha', 'description': '"쓸 때 쓴다."', 'disable-model-invocation': 'yes'},
     'frontmatter: disable-model-invocation 값은 true 또는 false'),
])
def test_frontmatter_errors(fields: dict[str, str], error: str) -> None:
    assert error in skill_check.check_frontmatter(fields, 'alpha')


def test_frontmatter_accepts_internal_reference_skill() -> None:
    fields = {'name': 'alpha', 'description': '"디버깅할 때 쓴다."', 'disable-model-invocation': 'true', 'user-invocable': 'false'}
    assert skill_check.check_frontmatter(fields, 'alpha') == []


def test_frontmatter_rejects_block_scalar() -> None:
    fields, _ = skill_check.frontmatter('---\nname: alpha\ndescription: >-\n  여러 줄 설명\n---\n\n# A\n')
    assert 'frontmatter: 한 줄 값만 허용' in skill_check.check_frontmatter(fields, 'alpha')


@pytest.mark.parametrize('body, expected', [
    ('\n# 제목\n\n목표 문단이다.\n\n## 단계\n', []),
    ('\n# 제목\n목표 문단이다.\n', []),
    ('\n목표 문단이다.\n', ['본문 구조: 첫 줄 # 제목']),
    ('\n# 제목\n\n- 범위: 입력 검사\n', ['본문 구조: 제목 다음 한 줄 목표 문단']),
    ('\n# 제목\n\n## 단계\n', ['본문 구조: 제목 다음 한 줄 목표 문단']),
    ('\n# 제목\n\n| a | b |\n', ['본문 구조: 제목 다음 한 줄 목표 문단']),
    ('\n# 제목\n', ['본문 구조: 제목 다음 한 줄 목표 문단']),
])
def test_body_starts_with_title_and_goal(body: str, expected: list[str]) -> None:
    assert skill_check.check_body(body) == expected


def kinds(text: str) -> list[str]:
    errors = consistency.check_markdown(text) + consistency.check_prose(text, dict(consistency.PRODUCT_TERMS))
    return [error.split(':')[0] for error in errors]


@pytest.mark.parametrize('text, kind', [
    ('# 제목\n\n```\ncode\n```\n', '코드 울타리'),
    ('# 제목\n\n문장이다. \n', '줄 끝 공백'),
    ('# 제목\n\n* 항목이다.\n', '목록 기호'),
    ('# 제목\n\n+ 항목이다.\n', '목록 기호'),
    ('# 제목\n\n1) 단계다.\n', '목록 기호'),
    ('# 제목\n\n앞이다 — 뒤다.\n', '엠 대시'),
    ('# 제목\n\n- **답변:** 요약을 쓴다.\n', '굵은 머리말'),
    ('# 제목\n\n### 세부\n', '절 구조'),
    ('# 제목\n\n# 둘째\n', '절 구조'),
    ('# 제목\n\n## 같은 절\n\n## 같은 절\n', '절 구조'),
    ('# 제목\n\nThinkFlow로 그린다.\n', '용어 불일치'),
    ('# 제목\n\n띵스플로우를 쓴다.\n', '용어 불일치'),
])
def test_markdown_violations(text: str, kind: str) -> None:
    assert kind in kinds(text)


@pytest.mark.parametrize('text', [
    '# 제목\n\n```text\n앞 — 뒤\n* 코드 안 목록\n```\n',
    '# 제목\n\n````markdown\n```\n안쪽 울타리\n```\n````\n',
    '# 제목\n\n`a — b`와 `**x:**`는 코드다.\n',
    '# 제목\n\n나쁜 예 "**성능:** 좋다"는 인용이다.\n',
    '# 제목\n\n- **검증.** 결과를 직접 확인한다.\n',
    '# 제목\n\n| 종류 | 뜻 |\n|---|---|\n| a | b |\n',
    '# 제목\n\n명령은 `diagramplay`, 확장자는 `.diagramplay`, 변수는 `DIAGRAMPLAY_PATH`다.\n',
    '# 제목\n\n[DiagramPlay](https://github.com/woonyong-choi/thinkflow)를 쓴다.\n',
    '## 절\n\n참조 문서는 둘째 단계 절로 시작해도 된다.\n',
    '# 제목\n\n예: `a`와 `b`.\n',
])
def test_markdown_passes(text: str) -> None:
    assert kinds(text) == []


def test_skill_mentions_resolve_names(tmp_path: Path) -> None:
    skills = {'git-issue': tmp_path, 'principle-prove-it-works': tmp_path}
    text = '- **git-issue** 스킬, **prove-it-works** 원칙 스킬, **skill-creator** 스킬, **gamma** 스킬\n'
    errors = consistency.check_references(tmp_path / 'SKILL.md', text, skills)
    assert errors == ['참조 스킬: 1: 없는 스킬 gamma']
