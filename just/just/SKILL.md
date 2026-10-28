---
name: just
description: "사용자가 /just dev(개발 작업)나 /just docs(블로그 등 글쓰기)로 부를 때만 쓴다. dev는 작업 순서표로 재현, 구현, 검증까지 끝내고 편집 전 규칙 확인을 켜고 끈다. docs는 작성자 경험과 근거로 원고를 함께 쓴다."
disable-model-invocation: true
---

# just

`just` 뒤의 첫 낱말로 할 일을 고른다. Codex는 `/` 대신 `$`로 부른다(`$just dev`).

| 부르는 법 | 할 일 |
|---|---|
| `/just dev [요청]`, `/just dev on [요청]` | [dev.md](dev.md)를 읽고 그 절차로 요청을 끝낸다. 훅이 이 세션의 편집 전 규칙 확인을 켠다 |
| `/just dev off` | 훅이 규칙 확인을 껐으므로 다른 일은 하지 않고 "dev 꺼짐" 한 줄로 답한다 |
| `/just docs [요청]`, `/just docs on [요청]` | [docs.md](docs.md)를 읽고 이 세션의 글쓰기에 그 기준을 켠다 |
| `/just docs off` | 글쓰기 기준을 끄고 "docs 꺼짐"으로 답한다. 함께 온 요청은 끈 뒤 처리한다 |
| `/just`만, 또는 모르는 낱말 | 위 표를 짧게 보여 주고 무엇을 할지 묻는다. 설정과 스킬 고르기는 `/just-help`로 안내한다 |

- dev와 docs는 따로 켜고 끈다. 하나를 끄는 요청은 다른 하나를 바꾸지 않는다.
- 새 세션은 둘 다 꺼진 상태다.
