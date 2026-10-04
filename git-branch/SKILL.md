---
name: git-branch
description: "Git 작업 브랜치를 만들거나 PR 생성·머지·릴리스·머지 후 정리를 수행할 때 사용."
---

# Git Branch

- 저장소 안에 같은 역할의 규칙이 있으면 그것 우선. 없으면 이 스킬이 다른 규칙보다 우선
- 범위: 브랜치 구조, 작업 단위, 브랜치 이름, PR 생성, 머지, 릴리스
- 필요할 때만 읽기: 작업 선택, 시작 전 이슈 우선순위와 막힘 확인 → git-issue; 커밋 메시지, PR 제목, squash 메시지 작성 → git-commit; PR 본문 작성 → git-pull-request

## 구조

- 영구 브랜치: `main` 하나. 나머지는 짧은 작업 브랜치
- `main`: 항상 빌드, 테스트 통과 상태. 반영은 PR로만

## 혼자·팀

기준: 저장소 쓰기 권한이 있는 사람 수. 1명이면 혼자, 2명 이상이면 팀. AI 에이전트 제외.

| 항목 | 혼자 | 팀 |
|---|---|---|
| `main` 직접 push | 금지 | 금지 |
| PR | 필수 | 필수 |
| 머지 전 리뷰 승인 | 없음 | 작성자가 아닌 사람 1명 |
| 검증 | CI 있으면 CI 통과, 없으면 로컬 빌드·테스트·포맷·린트 통과 | 혼자와 동일 |

## 작업 단위

이슈로 추적하는 작업 하나 = 브랜치 하나 = PR 하나 = 작업 주체 하나.

- 독립 추적이 필요 없는 형식, 주석, 죽은 코드, 문서 동기화 정리: 이슈 없이 PR 허용 (git-issue 닫기)
- 작업 주체: 사람은 이슈 담당자(assignee), 같은 계정을 쓰는 AI 에이전트는 그 브랜치를 만든 에이전트
- `experiment` 이슈의 사전 등록 PR 여부와 결과 연결: repo-docs-experiment 흐름
- 서로 독립된 추적 작업이면 이슈부터 분리
- 큰 작업: 브랜치가 아니라 이슈를 하위 이슈로 분할. 하위 이슈마다 브랜치 하나

## 이름

`type/이슈번호-scope-설명` 또는 `type/scope-설명`

- 이슈를 추적하면 첫 형식, 이슈 없는 작은 정리는 둘째 형식
- type, scope: 커밋과 같은 단어 (git-commit type, scope)
- 설명: 영어 소문자 kebab-case, 2~5단어

| 예 | 뜻 |
|---|---|
| `feat/12-engine-rpc-server` | 12번 이슈, engine에 RPC 서버 추가 |
| `fix/31-tui-live-area-height` | 31번 이슈, tui 실행 영역 높이 버그 |
| `docs/40-readme-install` | 40번 이슈, README 설치 방법 |
| `docs/repo-comment-cleanup` | 이슈 없는 주석 정리 |
| `release/v0.1` | 릴리스 브랜치 (예외 형식) |

## 시작 전 확인

1. 착수 가능한 이슈 중 git-issue 우선순위 순서 확인
2. `git fetch origin --prune`
3. 이슈 작업이면 같은 이슈 번호 브랜치: `git branch -a --list "*/{번호}-*"`
4. 이슈 작업이면 같은 이슈 번호 열린 PR: `gh pr list --state open --search "{번호} in:title,body"`
5. 사용 중인 worktree: `git worktree list`
6. 이슈 작업이면 담당자: 비어 있으면 자기 계정 지정, 다른 사람이면 중단

- 이슈 작업에서 3~5에 같은 이슈가 나오면 새 브랜치 금지
- 사용자가 그 브랜치를 이어서 하라고 지정했으면 이어서 작업, 아니면 중단하고 보고

## 작업 중

- 분기: 최신 `main`에서 `git switch -c {브랜치} origin/main`
- 병렬 에이전트: 에이전트마다 이슈 하나, 브랜치 하나, worktree 하나. `git worktree add ../{저장소}.wt/{브랜치의 / 를 - 로} -b {브랜치} origin/main`
- 같은 생성물·빌드 단위(crate, 패키지)의 검사 담당은 하나. 다른 에이전트는 자기 파일만 수정, 검사 실패 보고. 읽기 검토·독립 조사는 병행 허용
- 검사 시작·종료 시 대상 HEAD 대조, 변경 여부 기록
- 임시 폴더, 저장소 사본, 두 번째 clone 금지. 검사는 자기 worktree에서만
- 자기 작업 브랜치 push 허용
- `main` 변경 반영: `git merge origin/main`

## PR

- 제목: 커밋 첫 줄 형식. 여러 모듈이면 가장 많이 바뀐 모듈, 저장소 전반이면 `repo`
- 이슈 연결: git-issue 닫기 절
- 머지 전: `git merge origin/main` 후 빌드, 테스트, 포맷, 린트 재실행
- 본문에 AI 흔적 금지

## 머지

- squash merge만
- squash 메시지: 첫 줄은 PR 제목, 본문과 꼬리말은 커밋 규칙, 이슈 연결이 있으면 PR 본문과 같은 `Closes: #{번호}` 또는 `Refs: #{번호}`
- GitHub가 자동으로 붙이는 커밋 목록, `Co-Authored-By` 줄 삭제
- AI 몫: PR 생성까지. 머지는 요청이 있을 때만
- 머지 후 자기 브랜치 삭제: 원격, 로컬, worktree. 정리 스크립트로 한 번에(정리 절)

## 정리

머지가 끝나면 저장소 안에서 실행. 먼저 미리보기, 목록 확인 뒤 `--apply`

```sh
python3 <이 스킬 폴더>/scripts/cleanup_merged.py <PR 번호 또는 브랜치>
python3 <이 스킬 폴더>/scripts/cleanup_merged.py <PR 번호 또는 브랜치> --apply
```

- `<이 스킬 폴더>`: 이 SKILL.md가 있는 폴더. 스크립트 본문은 읽지 않고 실행만. Windows에서 `python3`가 없으면 `py -3`
- 대상: 지정한 GitHub 머지 PR의 로컬 브랜치 worktree, 로컬 브랜치, 원격 브랜치
- PR 마지막 head SHA가 로컬·원격 브랜치 head와 모두 같을 때만 정리. 하나라도 다르거나 없으면 `skip:` 이유 출력
- 커밋 안 된 변경이 있는 worktree는 남기고 `skip:` 이유 출력
- 병렬 작업을 모두 머지한 뒤 확인: `git worktree list`에 `main` 하나, `git branch`에 `main`과 열린 PR 브랜치만
- 브랜치 생성 후 7일 넘게 머지 안 되면 사용자에게 보고
- 이슈 취소 시 PR 닫기, 브랜치 삭제

## 릴리스

- 태그: `main`에 `v{major}.{minor}.{patch}`. 요청이 있을 때만
- 지난 버전을 고쳐야 할 때만 해당 태그에서 `release/v{major}.{minor}` 생성
- 수정 순서: `main`에 먼저 PR로 반영 → 원 이슈를 참조하는 백포트 이슈 생성, 그 이슈 브랜치를 `release/*`에서 분기해 PR → 머지 후 새 태그
- 급한 수정도 `fix/` 브랜치 + PR. 예외 없음

## 금지

- `main`·`release/*` 직접 commit·push
- 같은 이슈 브랜치 중복 생성, 다른 이슈 작업 섞기
- 다른 주체의 브랜치 작업(commit, push 포함)
- 요청 없는 rebase·force push
- 요청 없는 머지·태그·브랜치 보호 설정 변경
