---
name: repo-docs-root
description: "AGENTS.md·CLAUDE.md 링크·CHANGELOG·CONTRIBUTING·SECURITY·LICENSE를 작성·갱신할 때 사용."
---

# Repo Docs Root

- 사용자 지시를 먼저 적용. 해당 주제의 사용자 지시가 없으면 작업 대상 저장소의 같은 주제 규칙 파일(예: `AGENTS.md`, `CONTRIBUTING.md`) 적용. 둘 다 없으면 이 스킬 적용. 다른 스킬과 겹치는 규칙은 머리의 연결에 적힌 스킬 중 그 규칙을 정한 스킬 적용
- 기반: repo-docs 먼저 적용. 이 스킬 범위: 루트와 `.github/`의 문서 파일. README와 `llms.txt`는 제외(repo-docs-readme, repo-docs-llms)
- 필요할 때만 읽기: 단계 판정(단계 표), 필요한 도구 문장(설치 절) → repo-docs-readme; CONTRIBUTING 커밋과 PR 절 → git-branch, git-commit, git-pull-request; 이슈 필요 여부와 연결 → git-issue

- 모든 칸: 저장소의 사실로. 명령은 CI나 검사 스크립트에 있는 것만

## 파일

| 파일 | 위치 | 언어·문체 규칙을 정한 스킬 | 설계 | 개발 중 | 실행 가능 | 배포 |
|---|---|---|---|---|---|---|
| `LICENSE` | 루트 | 해당 없음 | 조건부 | 조건부 | 조건부 | 조건부 |
| `AGENTS.md` | 루트 | repo-docs | 필수 | 필수 | 필수 | 필수 |
| `CLAUDE.md` | 루트 | 해당 없음 | 필수 | 필수 | 필수 | 필수 |
| `CONTRIBUTING.md` | `.github/` | repo-docs | 없음 | 필수 | 필수 | 필수 |
| `SECURITY.md` | `.github/` | repo-docs | 없음 | 없음 | 필수 | 필수 |
| `CHANGELOG.md` | 루트 | repo-docs | 없음 | 없음 | 없음 | 필수 |

- `LICENSE`: 라이선스를 정했을 때만. 근거는 패키지 선언(`Cargo.toml`, `package.json`, `pyproject.toml`의 `license`)의 SPDX 식별자나 사용자가 정한 라이선스. `UNLICENSED`, `proprietary`, 선언 없음이면 생성 금지, 임의 선택 금지
- `LICENSE` 내용: SPDX 식별자의 공식 원문 그대로, 연도와 저작권자(기존 저작권 고지 또는 사용자가 지정한 권리자, git 이름으로 자동 추정 금지)만 기입
- `.github/`에 둔 파일의 루트 중복 금지

## CLAUDE.md

- `AGENTS.md`를 가리키는 심볼릭 링크 하나: `ln -s AGENTS.md CLAUDE.md`
- 별도 내용 금지. 에이전트 지침의 원본은 `AGENTS.md` 하나

## AGENTS.md

````text
# {이름}

{한 줄 소개}

설계 문서는 [docs/README.md](docs/README.md)에 있다.

## 구성

| 경로 | 내용 |
|---|---|
| `{경로}` | {내용} |

## 명령

```sh
{빌드 명령}
{테스트 명령}
{린트 명령}
{포맷 검사 명령}
```

## 규칙

- 커밋 전 명령 절의 명령 모두 통과
- 동작, 계약, 설정 변경은 같은 PR에서 설계 문서 갱신
- 새 문서는 `docs/README.md` 문서 목록 안에서만 추가
- {저장소 규칙}
````

| 절 | 규칙 |
|---|---|
| 한 줄 소개 | `AGENTS.md` 언어의 README 한 줄 소개와 같은 글자(한국어면 `README.ko.md`) |
| 구성 | `docs/architecture.md` 코드 지도 표의 `위치`와 `하는 일` 칸을 같은 순서로 복사, 마지막에 경로 `docs/`, 내용 `설계 문서` 행 추가. 저장소 밖 경로(`~/`, 절대 경로) 행 제외 |
| 명령 | CI나 저장소 검사 스크립트에 실제로 있는 명령만, 빌드, 테스트, 린트, 포맷 검사 순서. README 개발 절이 있으면 같은 명령, 같은 순서. 명령이 하나도 없으면(설계 단계 포함) 명령 절과 규칙 첫째 항목 삭제 |
| 설계 문서 문장 | `docs/README.md`가 있을 때만. 없으면 규칙 셋째 항목도 삭제 |
| 규칙 | 앞 세 항목 고정(첫째, 셋째는 위 조건). `{저장소 규칙}`은 `docs/architecture.md` 불변 조건 절의 항목마다 조건 문장을 명사구로 줄여 옮기기: `설정 파일은 서버만 고친다` → `설정 파일은 서버만 수정`. 없으면 그 줄 제외 |

- 필요한 명령·경로·규칙을 보존하고, 다른 문서가 정의한 내용을 반복한 부분은 그 문서의 해당 절 링크로 대체
- 도구별 설정(모델, 권한, 훅) 금지
- 에이전트 이름, 도구 이름으로 규칙 분리 금지

## .github/CONTRIBUTING.md

````text
# Contributing

{How to contribute to the project}

## Before you start

{Issue creation conditions from the repository's issue policy}

## Development environment

{Required tools}

```sh
{Checkout command}
{Build command}
```

## Checks

All of the following checks must pass before opening a pull request.

```sh
{Test command}
{Lint command}
{Format check command}
```

## Commits and pull requests

{Branch and commit formats from the repository policy}
{Issue links and closing conditions from the issue policy}

## Documentation

{Documentation changes required for behavior, contract, and configuration changes}
````

| 절 | 규칙 |
|---|---|
| 시작 전에 | 이슈 생성·연결은 git-issue 기준. 이슈 템플릿 링크는 실제 디렉터리가 있을 때만 |
| 개발 환경 | 필요한 도구 문장은 README 설치 절 규칙과 동일 |
| 커밋과 PR | 저장소가 쓰는 git 규칙(git-branch, git-commit, git-pull-request)의 형식과 예 복사 |
| 문서 | `docs/README.md`가 있을 때만 |

## .github/SECURITY.md

````text
# Security policy

## Supported versions

| Version | Security updates |
|---|---|
| {Confirmed version range} | {Supported or unsupported} |

## Reporting a vulnerability

Do not disclose vulnerabilities in public issues. Use {verified private reporting channel}.
Include the affected version, reproduction steps, and expected impact.

## Response process

| Step | Deadline |
|---|---|
| Acknowledgment | {Confirmed deadline} |
| Assessment | {Confirmed deadline} |
| Fix release | {Confirmed deadline} |
````

- 지원 버전: 실제 유지보수 정책에서 확인한 범위만 기입
- 기한: 사용자가 정한 값만, 미정이면 저장 없이 보고
- 비공개 신고: 실제 운영되는 경로 확인 후 안내. 임의 경로·주소 생성 금지

## CHANGELOG.md

````text
# Changelog

Notable changes by version. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [Semantic Versioning](https://semver.org/).

## {버전} - {YYYY-MM-DD}

### {분류}

- {변경} ([#{번호}]({PR URL}))
````

| 커밋 type | 분류 |
|---|---|
| `feat` 새 기능 | 추가 |
| `feat` 기존 동작 변경, `perf` | 변경 |
| 사용 중단 표시 | 사용 중단 |
| 기능 제거 | 제거 |
| `fix` | 수정 |
| 보안 수정 | 보안 |

- 분류 순서: 위 표 순서. 항목이 없는 분류는 제목까지 제외
- 릴리스 PR에서 지난 태그 뒤 머지된 PR마다 항목 하나. 글자는 PR 제목의 설명 부분. 사용자 동작·호환·보안 영향이 없는 내부 변경만 제외, 커밋 type만으로 제외 금지
- 호환이 깨지는 변경: 항목 앞에 `호환 깨짐:`
- 버전: 최신이 위
