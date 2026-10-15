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
