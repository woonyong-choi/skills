---
name: repo-docs-note
description: "개발 중 단일 실행 관측이나 자료 요약을 짧은 기록으로 남길 때 사용."
---

# Repo Docs Note

- 우선순위: 해당 주제의 사용자 지시 → 저장소 규칙 → 이 스킬. 중복 규칙은 머리에 연결한 정본 스킬 적용
- 기반: repo-docs 먼저 적용. 이 스킬 범위: 짧은 개발 기록. 정한 설계(repo-docs-design), 고른 이유(repo-docs-decision), 판단 과정(repo-docs-journal), 측정(repo-docs-experiment)은 범위 밖

- 한 기록 = 종류 하나, 주제 하나. 섞이면 분리

## 종류

| 종류 | 판정 기준 | 폴더 |
|---|---|---|
| insight | 직접 실행해 안 것: 오류 원인, 예상과 다른 동작 | `docs/notes/insights/` |
| reference | 문서나 소스를 읽어 안 것: 도구, API, 명령, 설정 | `docs/notes/references/` |

## 파일

- 이름: `{주제}.md`. 주제는 영어 소문자 kebab-case: `tokio-spawn-detached.md`
- 같은 주제 파일이 있으면 그 파일 수정
- 목록 파일 금지. 폴더 = 목록

## insight

단일 실행 관측인 insight 작성·갱신 전 [insight.md](references/insight.md) 필수 확인

## reference

자료 요약인 reference 작성·갱신 전 [reference.md](references/reference.md) 필수 확인

## 공통 규칙

| 자리 | 규칙 |
|---|---|
| `date` | 마지막 수정 날짜 |
| `tags` | 기록을 다시 찾는 데 사용하는 기술이나 모듈 이름, 영어 소문자 |
| insight 제목 | 결론이 보이는 문장 `-다`, 마침표 없음: `tokio::spawn 작업은 JoinHandle을 버려도 계속 돈다` |
| reference 제목 | 명사구: `GitHub API 요청 한도` |
| 결론 | 제목 바로 아래 결론과 적용 조건 |
| 근거 | 실제 실행한 명령과 출력만. 실패 원인과 결과를 식별하는 구간 및 전체 원자료 경로 보존, 생략 구간 표시 |
| 내용 | 항목별 동일 속성을 조회할 때 표, 순서나 개별 설명이면 목록 |
| 확인하지 않은 것 | 없으면 절 생략 |

- 주제·결론·재현 근거·적용·미확인 조건 보존. 독립 주제가 섞인 경우만 분리, 줄 수 초과만으로 분리 금지

## 갱신

- 사실이 바뀌면 그 줄과 `date` 수정
- 이전 내용이 틀렸으면 결론 문단 끝에 `{YYYY-MM-DD}에 {틀린 내용}을 고쳤다.` 한 문장 추가
