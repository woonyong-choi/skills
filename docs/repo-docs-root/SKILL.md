---
name: repo-docs-root
description: "AGENTS.md·CLAUDE.md 링크·CHANGELOG·CONTRIBUTING·SECURITY·LICENSE를 작성·갱신할 때 사용."
---

# Repo Docs Root

- 우선순위: 해당 주제의 사용자 지시 → 저장소 규칙 → 이 스킬. 중복 규칙은 머리에 연결한 정본 스킬 적용
- 기반: repo-docs 먼저 적용. 이 스킬 범위: 루트와 `.github/`의 문서 파일. README와 `llms.txt`는 제외(repo-docs-readme, repo-docs-llms)
- 필요할 때만 읽기: 단계 판정(단계 표), 필요한 도구 문장(설치 절) → repo-docs-readme; CONTRIBUTING 커밋과 PR 절 → git-branch, git-commit, git-pull-request; 이슈 필요 여부와 연결 → git-issue

- 모든 칸: 저장소의 사실로. 명령은 CI나 검사 스크립트에 있는 것만

## 파일

| 파일 | 위치 | 언어·문체 규칙을 정한 스킬 | 설계 | 개발 중 | 실행 가능 | 배포 |
|---|---|---|---|---|---|---|
| `LICENSE` | 루트 | 해당 없음 | 조건부 | 조건부 | 조건부 | 조건부 |
| `AGENTS.md` | 루트 | repo-docs | 조건부 | 조건부 | 조건부 | 조건부 |
| `CLAUDE.md` | 루트 | 해당 없음 | 조건부 | 조건부 | 조건부 | 조건부 |
| `CONTRIBUTING.md` | `.github/` | repo-docs | 없음 | 필수 | 필수 | 필수 |
| `SECURITY.md` | `.github/` | repo-docs | 없음 | 없음 | 필수 | 필수 |
| `CHANGELOG.md` | 루트 | repo-docs | 없음 | 없음 | 없음 | 필수 |

- `LICENSE`: 라이선스를 정했을 때만. 근거는 패키지 선언(`Cargo.toml`, `package.json`, `pyproject.toml`의 `license`)의 SPDX 식별자나 사용자가 정한 라이선스. `UNLICENSED`, `proprietary`, 선언 없음이면 생성 금지, 임의 선택 금지
- `LICENSE` 내용: SPDX 식별자의 공식 원문 그대로, 연도와 저작권자(기존 저작권 고지 또는 사용자가 지정한 권리자, git 이름으로 자동 추정 금지)만 기입
- `.github/`에 둔 파일의 루트 중복 금지

도구 지침 파일은 저장소에서 사용하는 도구의 진입 파일만 생성한다. 이름·링크 방식은 저장소 정책 우선

## CLAUDE.md

- 이 진입 파일을 사용하는 경우 `AGENTS.md`를 가리키는 심볼릭 링크 하나: `ln -s AGENTS.md CLAUDE.md`
- 별도 내용 금지. 에이전트 지침의 원본은 `AGENTS.md` 하나

## AGENTS.md

`AGENTS.md` 작성·갱신·검토 전 [agents.md](references/agents.md) 필수 확인

## .github/CONTRIBUTING.md

`.github/CONTRIBUTING.md` 작성·갱신·검토 전 [contributing.md](references/contributing.md) 필수 확인

## .github/SECURITY.md

`.github/SECURITY.md` 작성·갱신·검토 전 [security.md](references/security.md) 필수 확인

## CHANGELOG.md

`CHANGELOG.md` 작성·갱신·검토 전 [changelog.md](references/changelog.md) 필수 확인
