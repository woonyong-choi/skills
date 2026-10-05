---
name: code-style-python
description: "Python 코드를 작성·검토하거나 Ruff·mypy·pytest 설정을 고칠 때 사용."
---

# Code Style: Python

- 우선순위: 해당 주제의 사용자 지시 → 저장소 규칙 → 이 스킬. 중복 규칙은 머리에 연결한 정본 스킬 적용
- 기반: code-style 먼저 적용. 이 스킬 범위: code-style이 언어에 맡긴 부분의 Python 규칙. 그 밖에서 code-style과 다르면 code-style 우선

## 이름

- 대소문자 표기: PEP 8. 포맷: `ruff format`
- 모든 함수 시그니처에 타입 힌트 필수

| 대상 | 규칙 | 예 |
|---|---|---|
| 접근자 | 공개 속성 그대로. 계산·검증이 필요해지면 `@property`. `get_x()`·`set_x()` 금지 | `session.name` |
| 생성 | `__init__`. 다른 생성 방법은 `@classmethod` `from_*` | `Config.from_file(path)` |
| 변환 | `to_*` 새 객체, `as_*` 다른 표현 | `to_dict()`, `as_posix()` |
| 반복자 | 제너레이터 함수 `iter_*` | `iter_sessions()` |
| 상수 | 모듈 최상위, UPPER_SNAKE_CASE | `MAX_RETRY = 3` |
| 약어 | 클래스 이름은 약어 전체 대문자, 함수·변수는 소문자 | `HTTPServerError`, `http_client` |
| 비공개 | 앞에 `_` 하나. `__` 이름 변환은 하위 클래스와 이름이 겹칠 때만 | `_cache` |
| 단위 | `datetime.timedelta` 우선 | `timeout: timedelta` |

## 선언 순서

모듈 파일:

1. 모듈 docstring
2. `from __future__ import ...`
3. `__all__`
4. import. 그룹 순서: 표준 라이브러리 → 서드파티 → 같은 프로젝트, 그룹 사이 빈 줄. 절대 경로 import. 와일드카드 금지
5. 상수·`logger`
6. 클래스. 공개 먼저
7. 함수. 공개 → 비공개
8. `if __name__ == "__main__":` (실행 스크립트만)

클래스:

1. 클래스 상수
2. 클래스 속성
3. `__init__`. 인스턴스 속성은 여기서만 정의. 공개 → 비공개
4. 특수 메서드 (`__repr__`, `__eq__` 등)
5. 이후는 code-style 타입 순서의 6~10 (프로퍼티 → 생명주기 → 공개 → 비공개 헬퍼 → 검증)

- `dataclass` 필드는 기본값 없는 필드 → 기본값 있는 필드 (문법 제약). 같은 안에서 공개 → 비공개
- 불변 필드는 `@dataclass(frozen=True)`나 `Final`로 표시

## 오류와 로그

| 경우 | 처리 |
|---|---|
| 일어날 수 있는 실패 | 예외 발생 |
| 코드에 버그가 없으면 일어날 수 없는 경우 | `raise AssertionError("<성립해야 하는 이유>")` |
| 테스트 | `assert` 허용 |

- 테스트 밖에서 `assert` 금지 (`python -O`에서 사라짐)
- `NotImplementedError`는 추상 메서드에만. 본문이 `pass`·`...`뿐인 미완성 함수 금지
- 라이브러리 패키지는 기준 예외 `class <패키지>Error(Exception)`를 두고 구체 예외는 이를 상속. 이름은 `...Error`
- 원인 보존: `raise ConfigError("failed to read config") from err`
- `except Exception:`·`except:`는 실행 스크립트 최상위 처리기에서만. `except ...: pass` 금지
- 실행 스크립트의 `main()`에서 기준 예외를 한 번 잡아 로그 기록 후 종료 코드 1로 종료
- 오류·로그 메시지는 소문자로 시작, 마침표 없음: `invalid literal for int()`
- 예외 무시 시 처리: (code-style 오류와 로그)

로그:

- 표준 `logging`. 저장소에 이미 정한 다른 라이브러리가 있으면 그것 우선
- 모듈마다 `logger = logging.getLogger(__name__)`. 루트 logger 직접 사용 금지
- 라이브러리 패키지: 핸들러·레벨 설정 금지. `NullHandler`만 허용
- 실행 스크립트 진입점에서 한 번만 `logging.basicConfig(...)`나 `logging.config.dictConfig(...)`로 설정
- 값은 f-string 대신 지연 포맷으로: `logger.info("session started: %s", session_id)`
- 구조화 값은 `extra={"session_id": session_id}`
- 출력 경계: (code-style 오류와 로그). `basicConfig` 기본 스트림은 stderr

## 공개 범위와 주석

- 비공개가 기본. 모듈 밖에서 쓸 것만 `_` 없이 이름 짓고 `__all__`에 기재
- 필드 접근은 공개 속성과 `@property`로 (PEP 8)
- docstring은 code-style 주석 기준대로 필요할 때만. 쓰면 한 줄 요약 (PEP 257)
- docstring 형식은 Google 스타일. 발생하는 예외는 `Raises:` 절

## 테스트

- pytest
- 위치: `tests/` 폴더, 파일은 `test_<모듈>.py`
- 이름: `test_` + code-style 형식: `test_parse_empty_input_raises_error`
- 테스트 데이터는 fixture로 만들고 예외 검사는 `pytest.raises`

## 린트 설정

Ruff·mypy·pytest 설정 생성·변경·감사 전 [lint.md](references/lint.md) 필수 확인

- ruff가 못 잡는 것은 직접 확인: 함수·파일 길이, 중첩 깊이, 인지 복잡도, `&&`·`||`(`and`·`or`) 개수, 이름, 비교 순서, 선언 순서, 로그 레벨
- `FBT`는 위치 인자 bool을 금지 → bool 매개변수는 키워드 전용(`*, verbose: bool`)만

## 검사 명령

경고도 실패 처리

```
ruff format --check .
ruff check .
mypy .
pytest
```
