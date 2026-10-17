---
name: repo-docs-spec
description: "구현된 protocol, CLI, UI, data, configuration, errors의 형식과 값을 문서로 남길 때 쓴다."
---

# 구현 명세

사용자와 연동 개발자가 찾아보는 인터페이스 문서에 구현된 형식과 값을 코드와 같은 글자로 적는다. 공통 규칙은 [repo-docs](../repo-docs/SKILL.md)를 먼저 따르고, 이 스킬은 인터페이스 문서의 템플릿과 항목 규칙을 맡는다.

## 원칙

- 문서를 만들지는 repo-docs 문서 목록의 만드는 조건으로 정한다.
- 인터페이스 문서는 찾아보는 문서다. 형식을 이해하는 데 필요한 설명과 항목을 담고, 고른 이유는 설계 문서에 둔다.
- 코드에서 만들 수 있는 내용(명령 도움말, 스키마, 기본값)은 코드와 같은 글자로 쓴다. 코드가 바뀌면 같은 PR에서 고친다.
- 항목은 문서마다 정한 순서로 놓고, 정하지 않은 곳은 알파벳순으로 놓는다.

## 템플릿

쓰거나 갱신하거나 검토하기 전에 그 문서의 템플릿을 반드시 읽는다.

| 문서 | 템플릿 |
|---|---|
| `docs/protocol.md` | [references/protocol.md](references/protocol.md) |
| `docs/cli.md` | [references/cli.md](references/cli.md) |
| `docs/ui.md` | [references/ui.md](references/ui.md) |
| `docs/data.md` | [references/data.md](references/data.md) |
| `docs/configuration.md` | [references/configuration.md](references/configuration.md) |
| `docs/errors.md` | [references/errors.md](references/errors.md) |

## 답변

- 쓰거나 고친 문서와 그 내용의 근거가 된 코드 경로를 적는다.

## 구분

- 데이터 그림을 만들거나 바꾸는 일은 [repo-docs-figures](../repo-docs-figures/SKILL.md)가 맡는다.
- 요구와 검증 범위, 생성한 표의 의미, 기능을 뺐을 때의 호환 사례는 [repo-docs-design 요구사항 절](../repo-docs-design/SKILL.md#요구사항)이 맡는다.
