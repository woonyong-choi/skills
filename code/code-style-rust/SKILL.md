---
name: code-style-rust
description: "Rust 코드를 쓰거나 검토하거나 리팩터링할 때, rustfmt와 Clippy 설정을 고칠 때 쓴다."
---

# Rust 코드 스타일

[code-style](../code-style/SKILL.md)을 먼저 적용하고, 이 스킬은 code-style이 언어에 맡긴 항목의 Rust 규칙만 정한다. 그 밖에서 code-style과 다르면 code-style을 따른다.

## 이름

- 대소문자는 Rust API Guidelines를 따르고 포맷은 rustfmt로 맞춘다.

| 대상 | 규칙 | 예 |
|---|---|---|
| 접근자 | `get_` 없이 필드 이름을 쓰고 setter는 `set_`을 붙인다 | `name()`, `set_name()` |
| 생성 | `new`, `with_*`, `from_*` | `Session::new`, `Config::from_file` |
| 변환 | 비용 없는 빌림은 `as_`, 복사나 계산은 `to_`, 소유권 이동은 `into_` | `as_str`, `to_string`, `into_inner` |
| 반복자 | `iter`, `iter_mut`, `into_iter` | |
| 약어 | 타입은 `Uuid`, 함수와 변수는 `uuid`처럼 쓴다 | |
| 단위 | `std::time::Duration`을 먼저 쓴다 | `timeout: Duration` |

## 선언 순서

파일은 다음 순서로 쓴다.

1. `//!` 모듈 설명
2. `use`. `std`, 외부 crate, `crate::`와 `super::` 순서로 묶고 그룹 사이에 빈 줄을 둔다.
3. `mod foo;` 선언
4. `const`와 `static`
5. 타입. 각 타입 정의 바로 뒤에 고유 `impl`을 두고, 그다음에 트레잇 `impl`을 둔다.
6. 자유 함수
7. `#[cfg(test)] mod tests`

- 필드는 struct에, 나머지는 impl에 둔다. impl 안은 code-style [선언 순서](../code-style/references/structure.md#선언-순서)의 타입 순서를 따른다.
- Rust 필드는 불변과 가변 구분이 없으므로 struct 필드는 공개, 비공개 순서만 지킨다.
- rustfmt는 `use` 그룹 안의 정렬만 한다. 그룹 나누기와 항목 순서는 직접 지킨다.

## 오류와 로그

| 경우 | 처리 |
|---|---|
| 일어날 수 있는 실패 | `Result`를 돌려준다 |
| 코드에 버그가 없으면 일어날 수 없는 경우 | `assert!(조건, "<이유>")`, `expect("<성립해야 하는 이유>")`, `unreachable!("<이유>")` |
| 테스트 | `unwrap`, `expect`, `panic!`을 써도 된다 |

- 테스트 밖에서 `unwrap`, `panic!`, `todo!`, `unimplemented!`를 쓰지 않는다.
- `expect` 메시지는 성립해야 하는 이유를 `should`로 쓴다(`expect("config should be loaded before start")`).
- 오류와 로그 메시지는 소문자로 시작하고 마침표를 찍지 않는다(`invalid digit found in string`).
- 오류를 무시할 때는 이유를 단다(`let _ = tx.send(event); // 받는 쪽이 이미 종료됨`).
- `println!`은 프로그램 결과에만 쓴다. 진단은 `eprintln!` 대신 `tracing`으로 남긴다.

라이브러리는 다음과 같이 쓴다. 저장소가 이미 다른 라이브러리를 정했으면 그것을 쓴다.

| crate | 쓰는 곳 | 역할 |
|---|---|---|
| `thiserror` | 라이브러리 crate | 오류 enum 정의 |
| `anyhow` | 실행 파일 crate | 여러 오류를 한 타입으로 받고 문맥 추가 |
| `tracing` | 모든 crate | 로그 기록 |
| `tracing-subscriber`(`env-filter` 기능) | 실행 파일 crate | 로그 출력 설정 |

- 버전은 작업 공간 `Cargo.toml`의 `[workspace.dependencies]`에 한 번만 적고, 각 crate는 `thiserror.workspace = true`처럼 참조한다. 단일 패키지는 그 `Cargo.toml`의 `[dependencies]`에 적는다.
- 라이브러리 crate에 `anyhow`와 `tracing-subscriber` 의존성을 두지 않는다.

`thiserror` 코드를 예와 대조할 때는 반드시 [오류와 로그 예](references/error-examples.md#thiserror)를 읽는다.

- 라이브러리 crate의 공개 오류 enum은 모듈마다 하나 두고 이름은 `<대상>Error`로 짓는다. 공개 함수는 `Result<T, <대상>Error>`를 돌려준다.
- variant 이름은 실패한 내용으로 짓는다(`NotFound`, `Parse`). `Error` 접미사를 붙이지 않는다.
- 하위 오류는 `#[from]`이나 `#[source]`로 원인에 보존한다. 메시지에 하위 오류 내용을 다시 쓰지 않는다.
- 같은 하위 오류가 여러 상황에서 생기면 `#[from]` 대신 `map_err`로 상황별 variant를 쓴다.
- crate 밖에 배포하는 라이브러리의 공개 오류 enum에는 `#[non_exhaustive]`를 단다.

`anyhow` 코드를 예와 대조할 때는 반드시 [오류와 로그 예](references/error-examples.md#anyhow)를 읽는다.

- 실행 파일 crate의 함수는 `anyhow::Result<T>`를 돌려준다. `main`도 `anyhow::Result<()>`를 돌려준다.
- 문맥은 고정 문자열이면 `.context("...")`, 값이 들어가면 `.with_context(|| format!(...))`로 단다.
- 새 오류는 `anyhow::bail!("...")`, 조건 검사는 `anyhow::ensure!(조건, "...")`로 쓴다.

`tracing` 코드를 예와 대조할 때는 반드시 [오류와 로그 예](references/error-examples.md#tracing)를 읽는다.

- 값은 메시지에 넣지 않고 필드로 넘긴다(`info!(session_id = %id, "session started")`). `%`는 Display, `?`는 Debug다.
- 세션과 요청처럼 흐름 단위 함수에는 `#[instrument]`를 단다. 큰 인자와 비밀값은 `skip`한다.

`tracing-subscriber` 코드를 예와 대조할 때는 반드시 [오류와 로그 예](references/error-examples.md#tracing-subscriber)를 읽는다.

- 실행 파일 `main` 시작에서 한 번만 설정한다. 레벨은 `RUST_LOG` 환경 변수로 정한다.
- 로그와 결과 스트림의 구분은 [code-style 오류와 로그](../code-style/references/errors.md)를 따른다. tracing writer는 반드시 stderr로 지정한다.

## 공개 범위와 주석

- 비공개, `pub(crate)`, `pub` 순서로 필요한 만큼만 넓힌다.
- 필드는 비공개로 두고 메서드로 다룬다. 검증 규칙이 없는 단순 데이터 묶음만 `pub` 필드를 허용한다.
- 주석을 남기는 경우는 [code-style 공개 범위와 주석](../code-style/references/structure.md#공개-범위와-주석)을 따른다. 공개 API의 문서 주석은 `///`, 공개 모듈의 문서는 `//!`로 쓴다.
- 문서 주석에 실패 조건을 쓸 때는 `# Errors`, panic 조건은 `# Panics`, unsafe 제약은 `# Safety` 절을 쓴다.

## 테스트

- 이름은 snake_case로 짓는다(`parse_empty_input_returns_error`).
- 단위 테스트는 같은 파일 끝의 `#[cfg(test)] mod tests`에 두고, 여러 모듈을 거치는 테스트는 `tests/` 폴더에 둔다.

## 린트 설정

- Cargo와 Clippy 설정을 만들거나 바꾸거나 감사하기 전에 반드시 [린트 설정](references/lint.md)을 읽는다.
- 이름, 비교 순서, `&&`와 `||`의 개수와 섞기, 선언 순서, 로그 레벨은 clippy가 잡지 못하므로 직접 확인한다.
- code-style [수치 기준](../code-style/references/structure.md#수치-기준)의 중첩 깊이를 셀 때 `match`, `loop`, `if let`, `while let`도 넣는다.
- impl 밖 함수의 중첩과 self 없는 함수의 매개변수 수는 clippy 허용값이 1 크다. 그래서 code-style 절대 최대를 직접 확인한다.

## 검사 명령

경고도 실패로 처리한다.

```sh
cargo fmt --all --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```
