---
name: repo-docs-llms
description: "README와 문서 목록에서 llms.txt·llms-full.txt를 생성·갱신할 때 사용."
---

# Repo Docs Llms

- 우선순위: 해당 주제의 사용자 지시 → 저장소 규칙 → 이 스킬. 중복 규칙은 머리에 연결한 정본 스킬 적용
- 기반: repo-docs 먼저 적용. 이 스킬 범위: 루트 `llms.txt`, `llms-full.txt`의 형식과 생성
- 필요할 때만 읽기: 생성물 동반 PR 확인 → git-pull-request

- 파일은 `gen_llms` 스크립트로만 생성, 손 작성 금지
- 원본: 루트 `README.md`와 `docs/README.md`. 원본에 없는 글자 추가 금지

## 파일

| 파일 | 내용 | 만드는 조건 |
|---|---|---|
| `llms.txt` | 이름, 한 줄 소개, 소개 문단, 문서 링크 목록 | `docs/README.md` 존재 |
| `llms-full.txt` | `README.md`와 `docs/README.md` 표의 문서 본문을 표 순서대로 이은 것 | 사용자가 요청할 때만. 문서 본문의 복사본이라 기본은 생성 제외 |

## llms.txt 형식

색인 생성물의 구조·원본 대응을 검토할 때 [output-format.md](references/output-format.md) 필수 확인

## 만들기

실행 위치: 저장소 루트

```sh
python3 <이 스킬 폴더>/scripts/gen_llms.py
```

- `llms-full.txt`도 만들 때: `--full`

- 스크립트 실행 전 skill-sync `references/execution.md` 필수 확인
- 원격: `--remote` 기본 origin, 기본 브랜치는 원격 HEAD 조회. 조회할 수 없으면 `--branch`로 확인한 값 지정. main 고정 대체 금지
- 자동 URL 구성은 github.com 전용. 다른 호스트는 `--raw-base-url`로 원문 루트 URL 지정
- 입력 위치: `README.md`, `docs/README.md`, 표의 모든 문서는 저장소 안 `.md` 파일만 허용. 심볼릭 링크는 실제로 가리키는 경로로 판정
- 공개 여부: 저장소 비공개 경로 정책 적용. `--private-dir` 반복으로 차단 폴더 이름 지정, 생략 시 `.local`·`archive`. 대소문자·중첩 URL 인코딩·심볼릭 링크의 실제 경로·git 제외 검사 유지
- 입력 검사에 하나라도 실패하면 파일을 쓰지 않고 중단
- 코드 블록 안 표 행: 목록에서 제외

- 실행 뒤 확인: `llms.txt` 링크 수와 `docs/README.md` 표 행 수 일치(`CHANGELOG.md` 행 제외)
- `llms-full.txt`의 파일 구분 줄 `<!-- {경로} -->`: 형식의 일부, repo-docs 검사 대상 제외

## 갱신

- README, `docs/README.md` 수정 PR: `gen_llms` 재실행, 결과 함께 커밋(git-pull-request)
- `llms-full.txt`가 있는 저장소의 문서 본문 수정 PR: `--full`로 재생성
