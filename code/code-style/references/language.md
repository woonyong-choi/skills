## 언어별 스킬

- 작업 언어의 스킬이 있으면 함께 적용. 없으면 이 스킬과 그 언어의 공식 스타일 가이드
- 이름: `code-style-<언어>`. 절 이름은 이 스킬과 같게, 공통 규칙 재기술 금지

언어별 스킬이 정하는 항목. 그 밖의 차이: 언어별 스킬 쪽 수정 대상 오류

- 대소문자 표기와 포맷
- 언어 관례가 있는 이름 형식: 접근자, 생성, 변환, 반복자
- 문법이 언어마다 다른 것: 오류 값·예외·단언, 공개 범위 키워드, 필드 접근 방식(접근 메서드·프로퍼티), 문서 주석 형식, import·모듈 선언
- 오류·로그 메시지의 대소문자·마침표
- 선언 순서에서 언어 문법·공식 규칙 때문에 달라지는 부분: 불변·가변 구분이 없는 필드, 공식 규칙이 위치를 정한 항목(Kotlin companion object 등), import 정렬 도구의 순서
- 테스트 위치
- 라이브러리 기본값: 로그, 오류 타입
- 린터 설정과 검사 명령
- CSS만: 선택자, 값과 단위, 반응형·접근성

언어 → 스킬 → 다루는 것:

- Rust → `code-style-rust` → 이름 형식, 오류 처리(thiserror·anyhow), 로그(tracing), 공개 범위·문서 주석, 파일 구성, 테스트 위치, clippy 설정·검사 명령
- Kotlin → `code-style-kotlin` → 이름 형식, 오류 처리, 로그(SLF4J), 공개 범위·KDoc, 파일·클래스 구성, 테스트 위치, detekt·ktlint 설정·검사 명령
- Python → `code-style-python` → 이름 형식, 예외 처리, 로그(logging), 공개 범위·docstring, 모듈·클래스 구성, 테스트 위치, ruff·mypy 설정·검사 명령
- JavaScript → `code-style-javascript` → 이름 형식, 모듈(ESM), 오류 처리, 로그, 공개 범위·JSDoc, 테스트 위치(node:test), ESLint·Prettier 설정·검사 명령
- CSS → `code-style-css` → class 이름, 파일 구성, 속성 순서, 선택자, 값과 단위, 반응형·접근성, Stylelint 설정·검사 명령. 함수·오류·로그 항목은 해당 없음
