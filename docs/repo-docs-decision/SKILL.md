---
name: repo-docs-decision
description: "공개 ADR·설계 결정 기록을 작성·갱신하거나 비공개 판단을 공개 기록으로 다시 쓸 때 사용."
---

# Repo Docs Decision

- 우선순위: 해당 주제의 사용자 지시 → 저장소 규칙 → 이 스킬. 중복 규칙은 머리에 연결한 정본 스킬 적용
- 기반: repo-docs 먼저 적용. 이 스킬 범위: 공개 결정 기록 대상, 파일, 템플릿, 판단 기록 옮기기, 절차
- 필요할 때만 읽기: 비공개 판단 기록에서 옮길 때 → repo-docs-journal; 관련 설계에 결정 링크를 반영할 때 → repo-docs-design

- 결정 기록: 설계 선택지 중 하나를 고른 이유의 공개 기록. 현재 설계는 설계 문서, 판단 과정과 놓친 것은 비공개 판단 기록 담당
- 공개 전환: (repo-docs 문서 목록). 공개 근거로 확인한 사실·식별자만 사용, 비공개 문장은 재작성
- 독자: 미래의 기여자. 답할 질문: 무엇을 정했나, 왜 그것인가, 무엇을 버렸나, 언제 다시 보나
- 언어: `docs/` 작업 언어(repo-docs references/writing.md 언어). 문체: 현재형, 능동태, 완결된 문장(결과 목록 제외)

## 대상

- 판정: 사용자나 연동 개발자에게 약속한 동작·형식, 또는 아키텍처를 선택할 때 적용. 그 선택의 대안별 장단점과 다시 검토할 조건을 남겨야 하는 경우 기록
- 이름·서식·코드 스타일만의 변경, 대안 선택이 없는 작업은 제외

## 파일

- 경로: `docs/decisions/{YYYY-MM-DD}-{주제}.md`. 날짜는 결정한 날, `{주제}`는 영어 소문자 kebab-case
- 목록: `docs/decisions/README.md`
- 저장소 정책에 따라 채택된 기록: 상태, 대체 칸만 수정. 결정이 바뀌면 새 기록
- 영어 작업 언어의 절 이름: `Context`, `Options`, `Decision`, `Consequences`, `Revisit when`

## docs/decisions/README.md

결정 기록 목록 작성·갱신 전 [index.md](references/index.md) 필수 확인

## 템플릿

공개 결정 기록 작성·갱신·검토 전 [decision.md](references/decision.md) 필수 확인

## 판단 기록에서 옮기기

비공개 판단을 공개 결정 기록으로 옮기기 전 [promotion.md](references/promotion.md) 필수 확인

## 작성 절차

1. 대상 표로 기록 여부 판정. 아니면 중단
2. 판단 기록이 있으면 옮기기 표대로. 없으면 재료는 저장소 승인 기록과 변경 근거. 추적기가 없으면 문서 내부 결정 식별자로 연결
3. 채울 사실이 없는 칸이 있으면 저장 금지, 보고([repo-docs references/writing.md 절 구성](../repo-docs/references/writing.md#절-구성))
4. 관련 설계 문서의 기술 선택 표나 해당 절에 이 기록 링크 추가(repo-docs-design)
5. `docs/decisions/README.md`에 행 추가
6. 저장 전 검사 실행(repo-docs)
