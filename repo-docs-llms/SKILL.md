---
name: repo-docs-llms
description: "저장소 루트 llms.txt(선택으로 llms-full.txt)를 만들거나 갱신할 때 사용. llmstxt.org 형식, README와 docs/README.md에서 내용을 옮기는 규칙, gen_llms 스크립트"
---

# Repo Docs Llms

- 저장소 안에 같은 역할의 규칙이 있으면 그것 우선. 없으면 이 스킬이 다른 규칙보다 우선
- 기반: repo-docs 먼저 적용. 이 스킬 범위: 루트 `llms.txt`, `llms-full.txt`의 형식과 생성

- 파일은 `gen_llms` 스크립트로만 생성, 손 작성 금지
- 원본: 루트 `README.md`와 `docs/README.md`. 원본에 없는 글자 추가 금지

## 파일

| 파일 | 내용 | 만드는 조건 |
|---|---|---|
| `llms.txt` | 이름, 한 줄 소개, 소개 문단, 문서 링크 목록 | `docs/README.md` 존재 |
| `llms-full.txt` | `README.md`와 `docs/README.md` 표의 문서 본문을 표 순서대로 이은 것 | 사용자가 요청할 때만. 문서 본문의 복사본이라 기본은 생성 제외 |

## llms.txt 형식

llmstxt.org 형식(2026-09-30 확인)

```text
# {이름}

> {한 줄 소개}

{소개 문단}

## Docs

- [{문서 제목}]({URL}): {내용}

## Optional

- [{문서 제목}]({URL}): {내용}
```

| 자리 | 원본 |
|---|---|
| 이름 | README `#` 제목 |
| 한 줄 소개 | README 제목 다음 첫 문단. 언어 전환 줄 제외 |
| 소개 문단 | 한 줄 소개 다음 문단 |
| 문서 | `docs/README.md` 표의 행 중 `experiments/`, `decisions/`가 아닌 행. 같은 순서 |
| Optional | `docs/README.md` 표의 `experiments/`, `decisions/` 행과 `CHANGELOG.md`(링크 글자는 그 파일의 `#` 제목, 설명 없음) |
| URL | `https://raw.githubusercontent.com/{소유자}/{저장소}/main/docs/{파일}`. 원문 마크다운 주소 |

- `## Docs`, `## Optional`: 영어 제목 고정. `Optional`은 형식이 정한 이름으로 건너뛰어도 되는 문서라는 뜻

## 만들기

실행 위치: 저장소 루트

```sh
python3 <이 스킬 폴더>/scripts/gen_llms.py
```

- `llms-full.txt`도 만들 때: `--full`

- `<이 스킬 폴더>`: 이 SKILL.md가 있는 폴더. 스크립트 본문은 읽지 않고 실행만. Windows에서 `python3`가 없으면 `py -3`
- 입력 검사: `README.md`, `docs/README.md`, 표의 모든 문서가 저장소 안 `.md`이고 git 제외 대상이 아닐 때만 생성. 심볼릭 링크는 실제 경로로 판정, 대소문자만 바꾼 경로도 git 제외 판정으로 차단. 하나라도 어긋나면 파일을 쓰지 않고 중단
- 코드 블록 안 표 행: 목록에서 제외

- 실행 뒤 확인: `llms.txt` 링크 수와 `docs/README.md` 표 행 수 일치(`CHANGELOG.md` 행 제외)
- `llms-full.txt`의 파일 구분 줄 `<!-- {경로} -->`: 형식의 일부, repo-docs 검사 대상 제외

## 갱신

- README, `docs/README.md` 수정 PR: `gen_llms` 재실행, 결과 함께 커밋(git-pull-request)
- `llms-full.txt`가 있는 저장소의 문서 본문 수정 PR: `--full`로 재생성
