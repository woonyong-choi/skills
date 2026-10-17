---
name: repo-docs-root
description: "AGENTS.md, CLAUDE.md 링크, CHANGELOG, CONTRIBUTING, SECURITY, LICENSE를 쓰거나 갱신할 때 쓴다."
---

# 저장소 루트 문서

저장소 루트와 `.github/`의 문서 파일을 README 단계에 맞춰 만들고 저장소의 사실로 채운다. 공통 규칙은 [repo-docs](../repo-docs/SKILL.md)를 먼저 따른다.

## 쓰지 않을 때

- README와 `llms.txt`는 이 스킬이 맡지 않는다([repo-docs-readme](../repo-docs-readme/SKILL.md), [repo-docs-llms](../repo-docs-llms/SKILL.md)).

## 원칙

- 모든 칸을 저장소의 사실로 채운다. 명령은 CI나 검사 스크립트에 있는 것만 쓴다.
- 도구 지침 파일은 저장소에서 쓰는 도구의 진입 파일만 만든다. 이름과 링크 방식은 저장소 정책이 먼저다.
- `.github/`에 둔 파일을 루트에 겹쳐 두지 않는다.

## 파일

단계는 [repo-docs-readme 단계 표](../repo-docs-readme/SKILL.md#단계)로 판정한다.

| 파일 | 위치 | 언어와 문체 규칙을 정한 스킬 | 설계 | 개발 중 | 실행 가능 | 배포 |
|---|---|---|---|---|---|---|
| `LICENSE` | 루트 | 해당 없음 | 조건부 | 조건부 | 조건부 | 조건부 |
| `AGENTS.md` | 루트 | repo-docs | 조건부 | 조건부 | 조건부 | 조건부 |
| `CLAUDE.md` | 루트 | 해당 없음 | 조건부 | 조건부 | 조건부 | 조건부 |
| `CONTRIBUTING.md` | `.github/` | repo-docs | 없음 | 없음 | 필수 | 필수 |
| `SECURITY.md` | `.github/` | repo-docs | 없음 | 없음 | 필수 | 필수 |
| `CHANGELOG.md` | 루트 | repo-docs | 없음 | 없음 | 없음 | 필수 |

## LICENSE

- 라이선스를 정했을 때만 만든다. 근거는 패키지 선언(`Cargo.toml`, `package.json`, `pyproject.toml`의 `license`)의 SPDX 식별자나 사용자가 정한 라이선스다.
- 선언이 `UNLICENSED`, `proprietary`이거나 없으면 만들지 않고, 라이선스를 마음대로 고르지 않는다.
- 내용은 SPDX 식별자의 공식 원문 그대로 쓰고 연도와 저작권자만 채운다. 저작권자는 기존 저작권 고지나 사용자가 정한 권리자를 쓰고, git 이름으로 짐작하지 않는다.

## CLAUDE.md

- 이 진입 파일을 쓰면 `AGENTS.md`를 가리키는 심볼릭 링크 하나만 둔다(`ln -s AGENTS.md CLAUDE.md`). 링크를 쓸 수 없으면 `@AGENTS.md` 한 줄 import로 쓰고, 도구가 실제로 읽는지 반드시 확인한다.
- 따로 내용을 쓰지 않는다. 에이전트 지침의 원본은 `AGENTS.md` 하나다.

## AGENTS.md

쓰거나 갱신하거나 검토하기 전에 [references/agents.md](references/agents.md)를 반드시 읽는다. 사용자가 승인해 둔 기존 지침 문서를 마음대로 지우지 않는다.

## .github/CONTRIBUTING.md

쓰거나 갱신하거나 검토하기 전에 [references/contributing.md](references/contributing.md)를 반드시 읽는다.

## .github/SECURITY.md

쓰거나 갱신하거나 검토하기 전에 [references/security.md](references/security.md)를 반드시 읽는다.

## CHANGELOG.md

쓰거나 갱신하거나 검토하기 전에 [references/changelog.md](references/changelog.md)를 반드시 읽는다.

## 답변

- 만들거나 고친 파일과 판정한 단계를 적는다.
- 근거가 없어 만들지 않은 파일(라이선스 미정, 비공개 취약점 신고 꺼짐 등)과 이유를 적는다.

## 구분

- 단계 판정과 필요한 도구 문장(빠른 시작 절)은 [repo-docs-readme](../repo-docs-readme/SKILL.md)가 맡는다.
- CONTRIBUTING의 커밋과 PR 절 내용은 **git-branch**, **git-commit**, **git-pull-request** 스킬이 맡는다.
- 이슈가 필요한지와 연결 방법은 **git-issue** 스킬이 맡는다.
