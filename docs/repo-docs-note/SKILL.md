---
name: repo-docs-note
description: "개발 중 한 번의 실행에서 관측한 것이나 자료 요약을 짧은 기록으로 남길 때 쓴다."
---

# Repo Docs Note

개발 중에 알게 된 것을 `docs/notes/` 아래 짧은 기록 하나로 남긴다. 공통 규칙은 [repo-docs](../repo-docs/SKILL.md)를 먼저 따르고, 이 스킬은 짧은 개발 기록만 맡는다.

## 쓰지 않을 때

- 정한 설계는 [repo-docs-design](../repo-docs-design/SKILL.md)에 쓴다.
- 고른 이유는 [repo-docs-decision](../repo-docs-decision/SKILL.md)에 쓴다.
- 단계별 판단은 저장소 `.local/decisions/`의 결정 기록에 쓴다.
- 측정은 [repo-docs-experiment](../repo-docs-experiment/SKILL.md)로 한다.

## 종류

| 종류 | 판정 기준 | 폴더 |
|---|---|---|
| insight | 직접 실행해 안 것(오류 원인, 예상과 다른 동작) | `docs/notes/insights/` |
| reference | 문서나 소스를 읽어 안 것(도구, API, 명령, 설정) | `docs/notes/references/` |

- 기록 하나에는 종류 하나, 주제 하나만 담는다. 독립된 주제가 섞이면 나누고, 줄 수만으로 나누지 않는다.
- insight를 쓰거나 갱신하기 전에 [references/insight.md](references/insight.md)를 반드시 읽는다.
- reference를 쓰거나 갱신하기 전에 [references/reference.md](references/reference.md)를 반드시 읽는다.

## 파일

- 이름은 `{주제}.md`이고 주제는 영어 소문자 kebab-case로 쓴다(`tokio-spawn-detached.md`).
- 같은 주제 파일이 있으면 그 파일을 고친다.
- 목록 파일을 만들지 않는다. 폴더가 곧 목록이다.

## 공통 규칙

| 자리 | 규칙 |
|---|---|
| `date` | 마지막으로 고친 날짜 |
| `tags` | 기록을 다시 찾을 때 쓰는 기술이나 모듈 이름. 영어 소문자 |
| insight 제목 | 결론이 보이는 `-다` 문장이고 마침표를 찍지 않는다(`tokio::spawn 작업은 JoinHandle을 버려도 계속 돈다`) |
| reference 제목 | 명사구(`GitHub API 요청 한도`) |
| 결론 | 제목 바로 아래에 결론과 적용 조건을 쓴다 |
| 근거 | 실제로 실행한 명령과 출력만 쓴다. 실패 원인과 결과를 알아볼 수 있는 구간과 전체 원자료 경로를 남기고, 생략한 구간은 표시한다 |
| 내용 | 항목마다 같은 속성을 찾아볼 때는 표, 순서나 개별 설명이면 목록으로 쓴다 |
| 확인하지 않은 것 | 없으면 절을 뺀다 |

- 주제, 결론, 재현 근거, 적용 조건, 확인하지 않은 조건을 빠뜨리지 않는다.

## 갱신

- 사실이 바뀌면 그 줄과 `date`를 고친다.
- 이전 내용이 틀렸으면 결론 문단 끝에 `{YYYY-MM-DD}에 {틀린 내용}을 고쳤다.` 한 문장을 더한다.

## 답변

- 쓰거나 고친 기록의 경로와 종류를 적는다.
