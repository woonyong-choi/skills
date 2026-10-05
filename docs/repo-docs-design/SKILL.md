---
name: repo-docs-design
description: "저장소 아키텍처·기능 설계·용어·문서 안내를 작성·갱신할 때 사용."
---

# Repo Docs Design

- 우선순위: 해당 주제의 사용자 지시 → 저장소 규칙 → 이 스킬. 중복 규칙은 머리에 연결한 정본 스킬 적용
- 기반: repo-docs 먼저 적용. 이 스킬 범위: 새 기능을 넣는 자리, 설계 문서 네 종류(`docs/README.md`, `architecture.md`, `design/{주제}.md`, `glossary.md`)의 절 구성, 코드로 옮기는 규칙
- 필요할 때만 읽기: 코드에 들어간 인터페이스 문서(프로토콜, 명령, 화면, 데이터, 설정, 오류) → repo-docs-spec; 타입으로 드러나지 않는 실패 조건·제약을 코드 주석으로 옮길 때 → code-style; 맥락, 구성 요소, 순서, 상태 그림 → repo-docs-figures; 대안 선택 근거 기록 → repo-docs-decision; 설계 값 측정 → repo-docs-experiment; 문서 동반 확인 → git-pull-request

## 새 기능을 넣는 자리

| 새로 정할 것 | 넣는 자리 |
|---|---|
| 기능의 목적, 동작, 요구사항 | `design/{주제}.md` |
| 구성 요소와 경계, 깨면 안 되는 조건 | `architecture.md` |
| 프로젝트 고유 용어 | `glossary.md` 표의 행 |
| 코드에 들어간 메시지, 명령, 키, 테이블, 설정 키, 오류 코드 | repo-docs-spec 문서 |
| 선택지 중 하나를 고른 이유 | `decisions/{날짜}-{주제}.md` (repo-docs-decision) |
| 측정이 필요한 값 | `experiments/{실험}/` (repo-docs-experiment), 그 전에는 `미해결 질문` |
| 구조와 흐름 그림 | 그림 원본과 위치(repo-docs-figures 도구와 파일) |

## 공통 규칙

- 설계 문서: 설계한 동작을 현재형으로. 진행 상황, 날짜, 담당자 금지. 상태는 상태 표 한 칸에만
- 현재 설계만. 바뀐 이력, 옛 설계 금지. 버린 선택지는 `대안` 절 한 줄과 결정 기록 링크
- 정해지지 않은 것: `미해결 질문` 절에 질문과 저장소 추적 링크. 추적기가 없으면 문서 내부 질문 식별자·결정 근거 연결. 본문에 확정처럼 쓰기 금지
- 같은 사실은 한 파일에만. 다른 파일은 링크
- 파일 분리: 각 문서가 다른 독자 질문에 답하고, 한쪽의 설명을 바꿔도 다른 쪽 설명을 함께 바꿀 필요가 없는지 검토. 줄 수만으로 분할 금지
- `> [!WARNING]` 알림: 어기면 데이터나 동작을 잃는 규칙에만(repo-docs references/writing.md 서식)

## 요구사항

- 문서의 요구 범위와 검증 범위 일치
- 문서·표를 자동 생성하는 경우, 원본이 요구사항을 올바르게 설명하는지 먼저 확인. 생성된 문서·표가 그 원본과 일치하는지는 별도로 확인
- 추가 기능: 생략 시 기존 의미를 유지하는 사례 지정

## docs/README.md

`docs/README.md` 작성·갱신·검토 전 [index.md](references/index.md) 필수 확인

## architecture.md

`architecture.md` 작성·갱신·검토 전 [architecture.md](references/architecture.md) 필수 확인

## design/{주제}.md

`design/{주제}.md` 작성·갱신·검토 전 [design.md](references/design.md) 필수 확인

## glossary.md

`glossary.md` 작성·갱신·검토 전 [glossary.md](references/glossary.md) 필수 확인

## 코드로 옮기기

| 내용 | 계약이 코드에 들어가기 전 | 들어간 뒤 |
|---|---|---|
| 목적, 흐름, 규칙과 이유 | 설계 문서 | 설계 문서 |
| 타입으로 드러나는 함수와 타입의 입출력 | 설계 문서 상세 설계 | 코드의 타입 정의. 설계 문서는 요약과 링크 |
| 타입으로 드러나지 않는 실패 조건, 제약 | 설계 문서 상세 설계 | 코드 문서 주석 (code-style 공개 범위와 주석) |
| 메시지, 명령, 설정, 테이블, 오류 코드 | 설계 문서 상세 설계 | spec 문서 |
| 할 일 | 이슈 | 이슈와 `TODO(#{번호})` |
| 동작 예시와 완료 조건 | 설계 문서 예시, 이슈 | 테스트. 요구사항 표 `검증 계획` 교체 |

- 동작·계약·설정 변경의 문서 동반 기준: (git-pull-request 문서 동반)
- 설계 문서 상태: 요구사항 표의 필수 동작이 repo-docs 사실 상태의 `구현` 근거를 충족하면 `구현`
