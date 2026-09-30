# saturn

여러 AI 코딩 도구의 세션을 한 화면에서 실행하고 기록하는 터미널 도구

여러 AI 코딩 도구를 함께 쓰면 세션 기록과 맥락이 도구마다 흩어집니다. saturn은 공급자 세션을 한 터미널 화면에서 실행하고 모든 대화를 SQLite에 저장합니다. 각 도구의 기록 기능과 달리 공급자가 바뀌어도 한 기록으로 이어 갑니다.

> [!NOTE]
> 개발 중입니다. 실행할 수 있는 명령은 아직 없습니다.

## 기능

- 세션 실행: 공급자 세션 시작과 중지
- 대화 기록: 모든 입력과 응답의 SQLite 저장

## 구성

구조는 [아키텍처](docs/architecture.md)에 있습니다.

| 구성 요소 | 하는 일 | 위치 |
|---|---|---|
| 엔진 | 공급자 프로세스 실행, 입력 대기열, JSON-RPC 서버 | `crates/saturn-engine` |
| 화면 | 채팅 화면과 입력 | `crates/saturn-tui` |
| 명령 | 엔진과 화면 시작 | `crates/saturn-cli` |

## 로드맵

- 기록 검색: 저장된 대화의 낱말 검색 ([#12](https://github.com/woonyong-choi/saturn/issues/12))
- 하위 에이전트 추적: 공급자가 띄운 하위 에이전트의 부모 작업 아래 기록 ([#15](https://github.com/woonyong-choi/saturn/issues/15))

## 개발

```sh
cargo build --workspace
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
cargo fmt --all --check
```

## 라이선스

[MIT](LICENSE) 라이선스를 따릅니다.
