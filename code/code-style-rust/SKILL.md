---
name: code-style-rust
description: "Rust 코드를 작성·검토·리팩터링하거나 rustfmt·Clippy 설정을 고칠 때 사용."
---

# Code Style: Rust

- 우선순위: 해당 주제의 사용자 지시 → 저장소 규칙 → 이 스킬. 중복 규칙은 머리에 연결한 정본 스킬 적용
- 기반: code-style 먼저 적용. 이 스킬 범위: code-style이 언어에 맡긴 부분의 Rust 규칙. 그 밖에서 code-style과 다르면 code-style 우선

## 이름

- 대소문자 표기: Rust API Guidelines. 포맷: rustfmt

| 대상 | 규칙 | 예 |
|---|---|---|
| 접근자 | `get_` 없이 필드 이름. setter는 `set_` | `name()`, `set_name()` |
| 생성 | `new`, `with_*`, `from_*` | `Session::new`, `Config::from_file` |
| 변환 | `as_` 비용 없는 빌림, `to_` 복사·계산, `into_` 소유권 이동 | `as_str`, `to_string`, `into_inner` |
| 반복자 | `iter`, `iter_mut`, `into_iter` | |
| 약어 | 타입은 `Uuid`, 함수·변수는 `uuid` | |
| 단위 | `std::time::Duration` 우선 | `timeout: Duration` |

## 선언 순서

파일:

1. `//!` 모듈 설명
2. `use`. 그룹 순서: `std` → 외부 crate → `crate::`·`super::`. 그룹 사이 빈 줄
3. `mod foo;` 선언
4. `const`·`static`
5. 타입. 각 타입 정의 바로 뒤에 고유 `impl`, 그다음 트레잇 `impl`
6. 자유 함수
7. `#[cfg(test)] mod tests`

- 필드는 struct에, 나머지는 impl에. impl 안은 타입 순서 (code-style 선언 순서)
- struct 필드: 공개 → 비공개 순서만 (Rust 필드는 불변·가변 구분 없음)
- rustfmt: `use` 그룹 안 정렬만. 그룹 나누기와 항목 순서는 직접

## 오류와 로그

| 경우 | 처리 |
|---|---|
| 일어날 수 있는 실패 | `Result` 반환 |
| 코드에 버그가 없으면 일어날 수 없는 경우 | `assert!(조건, "<이유>")`, `expect("<성립해야 하는 이유>")`, `unreachable!("<이유>")` |
| 테스트 | `unwrap`·`expect`·`panic!` 허용 |

- 테스트 밖에서 `unwrap`, `panic!`, `todo!`, `unimplemented!` 금지
- 초안 PR의 미완성 자리표시 예외: code-style 오류와 로그 절
- `expect` 메시지는 성립해야 하는 이유를 `should`로: `expect("config should be loaded before start")`
- 오류·로그 메시지는 소문자로 시작, 마침표 없음: `invalid digit found in string`
- 무시하는 오류는 이유를 주석으로: `let _ = tx.send(event); // 받는 쪽이 이미 종료됨`
- `println!`·`eprintln!`은 프로그램 결과 출력에만. 진단은 `tracing`

라이브러리. 저장소에 이미 정한 다른 라이브러리가 있으면 그것 우선

| crate | 쓰는 곳 | 역할 |
|---|---|---|
| `thiserror` | 라이브러리 crate | 오류 enum 정의 |
| `anyhow` | 실행 파일 crate | 여러 오류를 한 타입으로 받고 문맥 추가 |
| `tracing` | 모든 crate | 로그 기록 |
| `tracing-subscriber` (`env-filter` 기능) | 실행 파일 crate | 로그 출력 설정 |

- 버전: 작업 공간 `Cargo.toml`의 `[workspace.dependencies]`에 한 번만. 각 crate는 `thiserror.workspace = true`처럼 참조. 단일 패키지는 해당 `Cargo.toml`의 `[dependencies]`에 지정
- 라이브러리 crate에 `anyhow`·`tracing-subscriber` 의존성 금지

`thiserror` 코드 예를 대조할 때 [오류·로그 예](references/error-examples.md#thiserror) 필수 확인

- 공개 오류 enum은 모듈마다 하나, 이름은 `<대상>Error`. 공개 함수는 `Result<T, <대상>Error>` 반환
- variant 이름은 실패한 내용: `NotFound`, `Parse`. `Error` 접미사 금지
- 하위 오류는 `#[from]`이나 `#[source]`로 원인에 보존. 메시지에 하위 오류 내용 재기재 금지
- 같은 하위 오류가 여러 상황에서 생기면 `#[from]` 대신 `map_err`로 상황별 variant 사용
- crate 밖에 배포하는 라이브러리의 공개 오류 enum은 `#[non_exhaustive]`

`anyhow` 코드 예를 대조할 때 [오류·로그 예](references/error-examples.md#anyhow) 필수 확인

- 실행 파일 crate의 함수는 `anyhow::Result<T>` 반환. `main`도 `anyhow::Result<()>` 반환
- 문맥은 고정 문자열이면 `.context("...")`, 값이 들어가면 `.with_context(|| format!(...))`
- 새 오류는 `anyhow::bail!("...")`, 조건 검사는 `anyhow::ensure!(조건, "...")`

`tracing` 코드 예를 대조할 때 [오류·로그 예](references/error-examples.md#tracing) 필수 확인

- 값은 메시지에 넣지 않고 필드로: `info!(session_id = %id, "session started")`. `%`는 Display, `?`는 Debug
- 세션·요청처럼 흐름 단위 함수에 `#[instrument]`. 큰 인자와 비밀값은 `skip`
- 레벨: code-style 로그 레벨 표

`tracing-subscriber` 코드 예를 대조할 때 [오류·로그 예](references/error-examples.md#tracing-subscriber) 필수 확인

- 실행 파일 `main` 시작에서 한 번만 설정. 레벨은 `RUST_LOG` 환경 변수로
- 로그·결과 스트림 구분: (code-style 오류와 로그). tracing writer는 stderr 지정 필수

## 공개 범위와 주석

- 비공개 → `pub(crate)` → `pub` 순서로 필요한 만큼만 확대
- 필드는 비공개로 두고 메서드로 접근. 검증 규칙 없는 단순 데이터 묶음만 `pub` 필드 허용
- 주석 기준은 code-style 공개 범위와 주석 절. 문서 주석은 `///`, 파일·모듈 설명은 `//!`
- 문서 주석에 실패 조건을 쓸 때 `# Errors`, panic 조건을 쓸 때 `# Panics`, unsafe 제약을 쓸 때 `# Safety`

## 테스트

- 이름은 snake_case: `parse_empty_input_returns_error`
- 단위 테스트는 같은 파일 끝 `#[cfg(test)] mod tests`, 여러 모듈을 거치는 테스트는 `tests/` 폴더

## 린트 설정

Cargo·Clippy 설정 생성·변경·감사 전 [lint.md](references/lint.md) 필수 확인

- clippy가 못 잡는 것은 직접 확인: 이름, 비교 순서, `&&`·`||` 개수와 섞기, 선언 순서, 로그 레벨
- 중첩 깊이 (code-style 수치 기준) 계산에 `match`·`loop`·`if let`·`while let` 포함
- impl 밖 함수의 중첩은 clippy 허용값과 별도로 code-style 절대 최대 직접 확인

## 검사 명령

경고도 실패 처리

```
cargo fmt --all --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```
