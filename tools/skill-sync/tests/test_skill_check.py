"""skill_check 끝말 검사의 명사·조사 오탐 경계와 평서형·명사형 탐지 유지 계약."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import skill_check  # noqa: E402


# cost: time O(w), heap O(w), stack O(1)
# vars: w = 줄 길이
# basis: estimate
def flagged(line: str) -> list[str]:
    return [word for _, word in skill_check.bad_endings([line], 0)]


@pytest.mark.parametrize('line', [
    '- 읽을 파일: 루트 지침',
    '- 회사 방침',
    '- 검사 단위: 파일마다',
    '- 비교 기준: 이전 값보다',
    '- 출력 대상: 표준 출력 스트림',
    '- 처리 단위: 프레임',
    '- 주소 형식: URL 스킴',
    '- 인자: 정렬 람다',
    '- 예시 단어: 바다',
    '- 설치 위치: 런타임',
    '- 필요한 것: 도움',
    '- 알고리듬',
    '- 남은 힘',
    '| 단위 | 파일마다 |',
    '| 대상 | 표준 출력 스트림 |',
    '파일마다 다른 값, 이전보다 큰 값',
    '정렬 람다, 바다.',
])
def test_noun_and_particle_endings_pass(line: str) -> None:
    assert flagged(line) == []


@pytest.mark.parametrize('line, word', [
    ('- 입력 저장한다', '저장한다'),
    ('- 결과가 저장된다', '저장된다'),
    ('- 엔진이 읽는다', '읽는다'),
    ('- 기본값이다', '기본값이다'),
    ('- 값이 있다', '있다'),
    ('- 값이 없다', '없다'),
    ('- 바꾸지 않다', '않다'),
    ('- 이미 받았다', '받았다'),
    ('- 이미 읽었다', '읽었다'),
    ('- 이미 하였다', '하였다'),
    ('- 확인이 필요하다', '필요하다'),
    ('- 앞과 같다', '같다'),
    ('- 측정 결과다', '결과다'),
    ('- 기준으로 삼다', '삼다'),
    ('| 동작 | 저장한다 |', '저장한다'),
    ('- 입력 저장함', '저장함'),
    ('- 값 있음', '있음'),
    ('- 저장 완료됨', '완료됨'),
    ('- 이름 바꿈', '바꿈'),
    ('- 문이 닫힘', '닫힘'),
    ('- 이름 씀', '씀'),
    ('엔진이 저장한다, 그다음 읽는다.', '저장한다'),
    ('값은 결과다. 다음 줄', '결과다'),
])
def test_declarative_and_nominal_endings_fail(line: str, word: str) -> None:
    assert word in flagged(line)


# #64: authoring.md의 `-ㅁ`형 금지를 줄 끝·줄 중간에 같게 적용, 강조 표시 안 끝말 검사
@pytest.mark.parametrize('line, word', [
    ('- 설정이 바뀜', '바뀜'),
    ('- 목록에 들어감', '들어감'),
    ('- 작업이 끝남', '끝남'),
    ('- 결과를 보냄', '보냄'),
    ('- 두 칸으로 나뉨', '나뉨'),
    ('- 결과를 기록함. 다음 단계 진행', '기록함'),
    ('- 값이 바뀜; 이어서 저장', '바뀜'),
    ('- 결과가 *강조된다*', '강조된다'),
    ('- 결과가 **기록됨**', '기록됨'),
    ('- 결과가 _바뀜_', '바뀜'),
    # #68: 아님은 않음과 같은 서술 끝(아니다)이라 금지
    ('- 이 단계 대상 아님. 다음 줄', '아님'),
    ('- 스크립트 대상 아님', '아님'),
    ('- 기본값 아님', '아님'),
])
def test_nominal_endings_fail_at_line_end_and_mid_line(line: str, word: str) -> None:
    assert word in flagged(line)


@pytest.mark.parametrize('line', [
    '- 원인: 잡음',
    '- 촬영 재료: 필름',
    '- 국가: 캐나다',
    '- 국가: 캐나다. 다음 줄',
    '- 신호 잡음. 다음 줄',
    '- 상태 없음. 다음 줄',
    '- 사용자 홈',
    '- 검사 순서: I/O·잠금',
])
def test_nominal_nouns_pass(line: str) -> None:
    assert flagged(line) == []


@pytest.mark.parametrize('description, expected', [
    ('작업할 때 사용.', []),
    ('작업할 때 사용. 다른 작업 제외.', ['description 사용. 뒤 글자']),
])
def test_description_ends_with_use(tmp_path: Path, description: str, expected: list[str]) -> None:
    skill = tmp_path / 'sample'
    (skill / 'agents').mkdir(parents=True)
    (skill / 'agents' / 'openai.yaml').write_text(
        'interface:\n  display_name: "S"\n  short_description: "s"\n  default_prompt: "$sample 처리"\n', encoding='utf-8')
    (skill / 'SKILL.md').write_text(
        f'---\nname: sample\ndescription: "{description}"\n---\n\n# Sample\n', encoding='utf-8')
    errors = [e for e in skill_check.check(str(skill / 'SKILL.md'), ['sample']) if e.startswith('description')]
    assert errors == expected
