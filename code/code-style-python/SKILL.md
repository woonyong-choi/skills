---
name: code-style-python
description: "Python 코드를 쓰거나 검토할 때, Ruff, mypy, pytest 설정을 고칠 때 쓴다."
---

# Code Style: Python

[code-style](../code-style/SKILL.md)을 먼저 적용하고, 이 스킬은 code-style이 언어에 맡긴 항목의 Python 규칙만 정한다. 그 밖에서 code-style과 다르면 code-style을 따른다.

## 이름

- 대소문자는 PEP 8을 따르고 포맷은 `ruff format`으로 맞춘다.
- 함수 시그니처에는 반드시 타입 힌트를 단다.

| 대상 | 규칙 | 예 |
|---|---|---|
| 접근자 | 공개 속성을 그대로 쓴다. 계산이나 검증이 필요해지면 `@property`를 쓴다. `get_x()`, `set_x()`를 쓰지 않는다 | `session.name` |
| 생성 | `__init__`을 쓴다. 다른 생성 방법은 `@classmethod` `from_*`로 둔다 | `Config.from_file(path)` |
| 변환 | 새 객체는 `to_*`, 다른 표현은 `as_*` | `to_dict()`, `as_posix()` |
| 반복자 | 제너레이터 함수 `iter_*` | `iter_sessions()` |
| 상수 | 모듈 최상위에 UPPER_SNAKE_CASE로 둔다 | `MAX_RETRY = 3` |
| 약어 | 클래스 이름에서는 약어 전체를 대문자로, 함수와 변수에서는 소문자로 쓴다 | `HTTPServerError`, `http_client` |
| 비공개 | 앞에 `_` 하나를 붙인다. `__` 이름 변환은 하위 클래스와 이름이 겹칠 때만 쓴다 | `_cache` |
| 단위 | `datetime.timedelta`를 먼저 쓴다 | `timeout: timedelta` |

## 선언 순서

모듈 파일은 다음 순서로 쓴다.

1. 모듈 docstring
2. `from __future__ import ...`
3. `__all__`
4. import. 표준 라이브러리, 서드파티, 같은 프로젝트 순서로 묶고 그룹 사이에 빈 줄을 둔다. 절대 경로로 import하고 와일드카드를 쓰지 않는다.
5. 상수와 `logger`
6. 클래스. 공개 클래스를 먼저 둔다.
7. 함수. 공개 함수, 비공개 함수 순서다.
8. `if __name__ == "__main__":`(실행 스크립트만)

클래스는 다음 순서로 쓴다.

1. 클래스 상수
2. 클래스 속성
3. `__init__`. 인스턴스 속성은 여기서만 정의하고 공개, 비공개 순서로 둔다.
4. 특수 메서드(`__repr__`, `__eq__` 등)
5. 이후는 code-style 타입 순서의 5~10번(`from_*` 팩토리, 프로퍼티, 생명주기, 공개 메서드, 비공개 헬퍼, 검증)을 따른다.

- `dataclass` 필드는 문법 제약 때문에 기본값 없는 필드를 기본값 있는 필드보다 먼저 둔다. 그 안에서는 공개, 비공개 순서로 둔다.
- 불변 필드는 `@dataclass(frozen=True)`나 `Final`로 표시한다.

## 오류와 로그

| 경우 | 처리 |
|---|---|
| 일어날 수 있는 실패 | 예외를 던진다 |
| 코드에 버그가 없으면 일어날 수 없는 경우 | `raise AssertionError("<성립해야 하는 이유>")` |
| 테스트 | `assert`를 써도 된다 |

- 테스트 밖에서 `assert`를 쓰지 않는다. `python -O`에서 사라진다.
- `NotImplementedError`는 추상 메서드에만 쓴다. 본문이 `pass`나 `...`뿐인 미완성 함수를 두지 않는다.
- 라이브러리 패키지는 기준 예외 `class <패키지>Error(Exception)`를 두고 구체 예외가 이를 상속하게 한다. 예외 이름은 `...Error`로 짓는다.
- 원인을 보존한다(`raise ConfigError("failed to read config") from err`).
- `except Exception:`과 `except:`는 실행 스크립트 최상위 처리기에서만 쓴다.
- 예외를 무시할 때는 `contextlib.suppress(<구체 예외>)`와 이유 주석을 쓴다. `except ...: pass`를 쓰지 않는다.
- 실행 스크립트의 `main()`에서 기준 예외를 한 번 잡아 로그를 남기고 종료 코드 1로 끝낸다.
- 오류와 로그 메시지는 소문자로 시작하고 마침표를 찍지 않는다(`invalid literal for int()`).

로그는 다음 규칙을 따른다.

- 표준 `logging`을 쓴다. 저장소가 이미 다른 로그 라이브러리를 정했으면 그것을 쓴다.
- 모듈마다 `logger = logging.getLogger(__name__)`를 두고 루트 logger를 직접 쓰지 않는다.
- 라이브러리 패키지에서는 핸들러와 레벨을 설정하지 않는다. `NullHandler`만 허용한다.
- 실행 스크립트 진입점에서 한 번만 `logging.basicConfig(...)`나 `logging.config.dictConfig(...)`로 설정한다.
- 값은 f-string 대신 지연 포맷으로 넘긴다(`logger.info("session started: %s", session_id)`).
- 구조화 값은 `extra={"session_id": session_id}`로 넘긴다.
- 결과와 진단의 출력 경계는 [code-style 오류와 로그](../code-style/references/errors.md)를 따른다. `basicConfig`의 기본 스트림은 stderr다.

## 공개 범위와 주석

- 비공개가 기본이다. 모듈 밖에서 쓸 것만 `_` 없이 이름 짓고 `__all__`에 적는다.
- 필드는 공개 속성과 `@property`로 다룬다(PEP 8).
- docstring은 필요할 때만 한 줄 요약으로 쓰고(PEP 257) Google 스타일을 따른다. 던지는 예외는 `Raises:` 절에 적는다.

## 테스트

- pytest를 쓴다.
- 테스트는 `tests/` 폴더의 `test_<모듈>.py` 파일에 둔다.
- 이름은 `test_` 뒤에 code-style 형식을 붙인다(`test_parse_empty_input_raises_error`).
- 테스트 데이터는 fixture로 만들고 예외는 `pytest.raises`로 검사한다.

## 린트 설정

- Ruff, mypy, pytest 설정을 만들거나 바꾸거나 감사하기 전에 반드시 [린트 설정](references/lint.md)을 읽는다.
- 함수와 파일 길이, 중첩 깊이, 인지 복잡도, `&&`와 `||`(`and`, `or`) 개수, 이름, 비교 순서, 선언 순서, 로그 레벨은 ruff가 잡지 못하므로 직접 확인한다.
- `FBT`는 위치 인자 bool을 막는다. 그래서 bool 매개변수는 키워드 전용(`*, verbose: bool`)으로만 둔다.

## 검사 명령

경고도 실패로 처리한다.

```sh
ruff format --check .
ruff check .
mypy .
pytest
```
