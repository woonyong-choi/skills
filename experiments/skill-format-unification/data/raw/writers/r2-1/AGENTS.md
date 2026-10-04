# sample-app

여러 AI 코딩 도구의 세션을 한 화면에서 실행하고 기록하는 터미널 도구

## 구성

| 경로 | 내용 |
|---|---|
| `crates/sample-app-engine` | 엔진 |
| `crates/sample-app-tui` | 화면 |
| `crates/sample-app-cli` | 명령 |
| `docs/` | 설계 문서 |

## 명령

```sh
cargo build --workspace
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
cargo fmt --all --check
```

## 규칙

- 커밋 전 명령 절의 명령 모두 통과
- 동작, 계약, 설정 변경은 같은 PR에서 설계 문서 갱신
- 새 문서는 `docs/README.md` 문서 목록 안에서만 추가
- 기록 저장소 저장: 엔진만
