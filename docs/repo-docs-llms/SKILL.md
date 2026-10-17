---
name: repo-docs-llms
description: "README와 문서 목록에서 llms.txt, llms-full.txt를 만들거나 갱신할 때 쓴다."
---

# LLM 문서 색인

루트 `llms.txt`와 `llms-full.txt`를 `gen_llms` 스크립트로 만들고 README, 문서 목록과 맞춘다. 공통 규칙은 [repo-docs](../repo-docs/SKILL.md)를 먼저 따르고, 이 스킬은 두 파일의 형식과 생성을 맡는다.

## 원칙

- 두 파일은 `gen_llms` 스크립트로만 만든다. 손으로 쓰지 않는다.
- 머리는 `README.en.md`에서, 없으면 `README.md`에서 가져온다. 문서 링크는 `docs/README.md` 목록에서 가져온다.
- 원본에 없는 글자를 더하지 않고 목록의 제목과 설명을 번역하지 않는다.

## 파일

| 파일 | 내용 | 만드는 조건 |
|---|---|---|
| `llms.txt` | 이름, 한 줄 소개, 소개 문단, 문서 링크 목록 | `docs/README.md`가 있을 때 |
| `llms-full.txt` | `README.md`와 `docs/README.md` 목록 문서의 본문을 목록 순서대로 이은 것 | 문서 본문의 복사본이라 사용자가 요청할 때만 |

- 색인 생성물의 구조와 원본 대응을 검토할 때는 [references/output-format.md](references/output-format.md)를 반드시 읽는다.

## 만들기

스크립트를 실행하기 전에 skill-sync `references/execution.md`를 반드시 읽는다. 저장소 루트에서 실행한다.

```sh
python3 <이 스킬 폴더>/scripts/gen_llms.py
```

- `llms-full.txt`도 만들 때는 `--full`을 붙인다.
- Python 3.9 이상, 표준 라이브러리, Git이 필요하다. 실패하면 stderr에 이유를 쓰고 종료 코드 1로 끝난다. 인자 오류는 2다.
- `--remote`는 기본이 origin이고 기본 브랜치는 원격 HEAD로 조회한다. 조회할 수 없으면 확인한 값을 `--branch`로 준다. main으로 고정해 대신하지 않는다.
- URL 자동 구성은 github.com에서만 된다. 다른 호스트는 `--raw-base-url`로 원문 루트 URL을 준다.
- `README.md`, `README.en.md`, `docs/README.md`, 목록의 모든 문서는 저장소 안 `.md` 파일만 받는다. 심볼릭 링크는 실제로 가리키는 경로로 판정한다.
- 공개 여부는 repo-docs 비공개 작업 파일 절을 따른다. 빼면 `.local`만 막는다. 저장소가 다른 비공개 폴더를 쓰면 `--private-dir`를 되풀이해 그 이름을 준다. 이 옵션은 기본값을 대신한다. 대소문자, 중첩 URL 인코딩, 심볼릭 링크의 실제 경로, git 제외 검사를 그대로 둔다.
- 입력 검사가 하나라도 실패하면 파일을 쓰지 않고 멈춘다. README 제목, 한 줄 소개, 소개 문단이 빠진 경우도 실패다.
- 목록은 `- [제목](경로): 답하는 것` 줄을 위에서부터 순서대로 읽는다. 들여 쓴 하위 줄도 같은 순서로 읽고, 출력에는 들여쓰기 없이 한 줄씩 쓴다. 분류 제목(`## 시작` 등)은 읽지 않는다.
- 코드 블록 안의 문서 줄은 목록에서 뺀다.
- 링크 없는 목록 줄과 콜론 뒤 설명이 없는 목록 줄은 줄 번호와 함께 종료 코드 1로 끝난다. 표만 있고 목록 줄이 없으면 `docs/README.md가 목록 형식이 아님`으로 종료 코드 1로 끝난다.
- 실행한 뒤 `llms.txt` 링크 수가 `docs/README.md` 목록 링크 줄 수와 같은지 확인한다. `CHANGELOG.md`가 있으면 하나를 더한다.
- `llms-full.txt`의 파일 구분 줄 `<!-- {경로} -->`는 형식의 일부라 repo-docs 검사에서 뺀다.

## 갱신

- README(영어판 포함)나 `docs/README.md`를 고치는 PR에서는 `gen_llms`를 다시 실행하고 결과를 함께 커밋한다(**git-pull-request** 스킬).
- `llms-full.txt`가 있는 저장소에서 문서 본문을 고치는 PR은 `--full`로 다시 만든다.

## 답변

- 만들거나 고친 파일 경로와 링크 수를 적는다.
- 입력 검사가 실패했으면 실패 이유와 줄 번호를 적는다.

## 구분

- 생성물을 함께 커밋했는지 PR에서 확인하는 일은 **git-pull-request** 스킬이 맡는다.
- 문서 목록 `docs/README.md`의 형식은 [repo-docs-design](../repo-docs-design/SKILL.md)가 맡는다.
