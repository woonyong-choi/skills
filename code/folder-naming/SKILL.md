---
name: folder-naming
description: "저장소의 새 폴더 구조·이름을 정하거나 요청받은 폴더 이름을 바꿀 때 사용."
---

# Folder Naming

- 사용자 지시를 먼저 적용. 해당 주제의 사용자 지시가 없으면 작업 대상 저장소의 같은 주제 규칙 파일(예: `AGENTS.md`, `CONTRIBUTING.md`) 적용. 둘 다 없으면 이 스킬 적용. 다른 스킬과 겹치는 규칙은 머리의 연결에 적힌 스킬 중 그 규칙을 정한 스킬 적용
- 범위: 새로 만드는 폴더, 이름 변경을 요청받은 폴더의 구조와 이름. 기존 폴더는 요청 없이 변경 금지

## 구조

기존 빌드·패키지 관리자 구조는 유지한다. 아래 구조와 기술 종류 폴더 금지는 기존 제약이 없는 새 제품 폴더 설계에만 적용

```
<프로젝트>/
├── assets/
├── docs/
├── <프로젝트>-<제품>/
│   ├── core/
│   └── cli/
└── <프로젝트>-protocol/
```

- 제외: 도구가 만들거나 요구하는 폴더 (`target`, `node_modules`, `build`, `.idea`, `.vscode`, `.cargo` 등)
- 패키지, 모듈이 하나뿐인 저장소: 언어 기본 구조(`src/` 등) 그대로

## 종류별 이름

| 종류 | 형식 | 예 |
|---|---|---|
| 루트 소스 | `<프로젝트>-<제품·실행 단위>` | `<프로젝트>-server`, `<프로젝트>-web`, `<프로젝트>-desktop`, `<프로젝트>-protocol` |
| 루트 비소스 | 아래 이름 우선, 없으면 언어·도구 관례 이름. 접두사 없음 | `assets`, `docs`, `scripts`, `tools`, `examples`, `config`, `.github` |
| 모듈 | 역할·도메인 명사, 접두사 없음 | `core`, `engine`, `cli`, `tui`, `api`, `auth`, `store` |
| 외부 서비스 | 연결 폴더 아래 서비스 이름 | `providers/codex`, `adapters/s3` |

## 모듈 이름

모듈 안 하위 폴더도 같은 규칙.

| 규칙 | 예 |
|---|---|
| 같은 종류 여럿이면 복수형 | `providers`, `sessions`, `judges` |
| 역할 하나면 단수형 | `queue`, `store`, `config` |
| 외부 서비스 이름은 연결 폴더 안에서만 | `providers/claude` O, `claude-handler` X |

## 금지

| 금지 | 이유 | 대신 |
|---|---|---|
| `utils`, `common`, `misc`, `helpers`, `etc` | 내용 파악 불가 | 역할 이름 (`time`, `paths`) |
| `new`, `old`, `temp`, `v2`, `backup` | 상태는 git이 관리 | 삭제 또는 브랜치 |
| `crates`, `packages`, `libs`, 루트 `src` | 기술 종류 기준 묶기 | `<프로젝트>-<제품>` |
| 경로 안 이름 반복 (`<프로젝트>-server/<프로젝트>-core`) | 중복 | `<프로젝트>-server/core` |
| 대문자·공백·밑줄 | 표기 혼용 | 소문자 kebab-case |

언어가 강제하는 표기(Rust 모듈 snake_case, Java package 등)는 그 언어 우선.

## 배포 이름

패키지·crate 이름: 폴더와 별개로 `<프로젝트>-<모듈>`. 언어·레지스트리 표기 관례 우선 (Python `<프로젝트>_<모듈>` 등).

| 폴더 | 패키지·crate |
|---|---|
| `<프로젝트>-server/core` | `<프로젝트>-core` |
| `<프로젝트>-server/cli` | `<프로젝트>-cli` |

## 이름 바꿀 때

1. `git mv`로 이동(이력 유지)
2. 빌드 설정(Cargo.toml, package.json, settings.gradle 등) 경로 수정
3. README, 문서 경로 수정
4. 빌드, 테스트 통과 확인
5. 동작 변경과 섞지 않고 한 커밋: `refactor(repo): 소스 폴더 이름 변경`
