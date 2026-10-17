---
name: repo-docs-decision
description: "공개 ADR이나 설계 결정 기록을 쓰거나 갱신할 때, 결정 기록의 판단을 공개 기록으로 다시 쓸 때 쓴다."
---

# 공개 결정 기록

설계 선택지 중 하나를 고른 이유를 공개 결정 기록(`docs/decisions/`)으로 남긴다. 공통 규칙은 [repo-docs](../repo-docs/SKILL.md)를 먼저 따르고, 이 스킬은 기록 대상, 파일, 템플릿, 결정 기록에서 옮기기, 절차를 맡는다.

## 대상

| 기록하는 것 | 기록하지 않는 것 |
|---|---|
| 사용자나 연동 개발자에게 약속한 동작이나 형식, 또는 아키텍처를 고르는 선택 중 대안별 장단점과 다시 검토할 조건을 남겨야 하는 것 | 이름, 서식, 코드 스타일만 바꾸는 일과 대안 선택이 없는 작업 |

## 독자와 문체

- 독자는 미래의 기여자다. 무엇을 정했나, 왜 그것인가, 무엇을 버렸나, 언제 다시 보나에 답한다.
- 현재형, 능동태, 완결된 문장으로 쓴다. 영향 목록만 명사구로 쓴다.
- 지금의 설계는 설계 문서가, 단계별 판단 과정은 저장소 `.local/decisions/`의 결정 기록이 맡는다. 공개 결정 기록은 고른 이유만 남긴다.
- 비공개 설계서를 공개로 옮길 때는 repo-docs 비공개 작업 파일 절을 따른다.

## 파일

- 경로는 `docs/decisions/{YYYY-MM-DD}-{주제}.md`다. 날짜는 결정한 날이고 `{주제}`는 영어 소문자 kebab-case로 쓴다.
- 목록은 `docs/decisions/README.md`에 둔다. 목록을 쓰거나 갱신하기 전에 [references/index.md](references/index.md)를 반드시 읽는다.
- 공개 결정 기록을 쓰거나 갱신하거나 검토하기 전에 [references/decision.md](references/decision.md)를 반드시 읽는다.
- 저장소 정책에 따라 결정된 기록은 상태와 대체 칸만 고친다. 결정이 바뀌면 새 기록을 쓴다.
- 작업 언어가 영어인 저장소의 절 이름은 `Context`, `Options`, `Decision`, `Consequences`, `Revisit when`이다.

## 단계

1. 대상 절로 기록할지 판정한다. 대상이 아니면 멈춘다.
2. 결정 기록이 있으면 옮기기 전에 [references/promotion.md](references/promotion.md)를 반드시 읽고 그 대응대로 옮긴다. 없으면 저장소 승인 기록과 변경 근거를 재료로 쓴다. 추적기가 없으면 문서 안 결정 식별자로 잇는다.
3. 채울 사실이 없는 칸이 있으면 저장하지 않고 보고한다.
4. 이 기록의 링크를 설계 문서 상태 표의 `관련 결정` 칸에 넣는다. 기술 선택이면 `architecture.md` 기술 선택 표에도 넣는다([repo-docs-design](../repo-docs-design/SKILL.md)).
5. `docs/decisions/README.md`에 행을 더한다.
6. repo-docs 저장 전 검사를 실행한다.

## 답변

- 쓴 공개 결정 기록과 고친 목록, 설계 문서 경로를 적는다.
- 채우지 못해 저장하지 않은 칸이 있으면 그 칸과 빠진 사실을 적는다.

## 구분

- 지금의 설계와 동작은 [repo-docs-design](../repo-docs-design/SKILL.md)가 맡는다.
- 작업 중 단계별 판단은 `.local/decisions/<과업>.tsv` 결정 기록에 남기고, 그 형식은 just **show-me-your-work** 스킬이 맡는다.
