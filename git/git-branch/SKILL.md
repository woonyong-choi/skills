---
name: git-branch
description: "Git 브랜치 생성·PR 생성·머지·릴리스·머지 후 정리를 실행할 때 사용."
---

# Git Branch

- 우선순위: 사용자 지시 → 저장소 규칙 → 이 스킬. 범위 밖은 명시한 소유 스킬 적용
- 범위: 브랜치 구조, 작업 단위, 브랜치 이름, PR 생성, 머지, 릴리스
- 필요할 때만 읽기: 작업 선택, 시작 전 막힘 확인 → git-issue 다음 작업; 커밋 메시지, PR 제목, squash 메시지 작성 → git-commit; PR 본문 작성 → git-pull-request; 검사 범위·증거 확인 → code-style; PR 생성·머지 → git-issue `references/project-status.md` 필수 확인

## 구조

- 원격·기본 브랜치·보호 브랜치: 저장소 설정과 원격 HEAD 조회로 확인. 운영 정책이 없으면 영구 브랜치 하나와 짧은 작업 브랜치 사용. 기존 기본 이름은 `origin`·`main`, 확인 없이 적용 금지
- 기본 브랜치: 항상 빌드, 테스트 통과 상태. 반영은 PR로만

## 혼자·팀

기준: 저장소 쓰기 권한이 있는 사람 수. 1명이면 혼자, 2명 이상이면 팀. AI 에이전트 제외.

항목 → 혼자 → 팀:

- PR → 필수 → 필수
- 머지 전 리뷰 승인 → 일반 변경은 없음, 계약 승인은 git-pull-request 검토 규칙 → 작성자가 아닌 사람 1명과 같은 계약 승인 규칙
- 검증 → CI 있으면 CI 통과, 없으면 로컬 빌드·테스트·포맷·린트 통과 → 혼자와 동일

## 작업 단위

이슈로 추적하는 작업 하나 = 브랜치 하나 = PR 하나 = 작업 주체 하나.

- 작업 이슈 연결·작은 후속 작업 재사용 기준: (git-issue 과업 연결과 기록)
- 작업 주체: 이슈 담당자와 bind된 과업. 재개·인계는 이슈·작업본·기록 일치와 기존 작업자의 동시 수정 여부 대조, 세션 ID 변경만으로 다른 주체 판정 금지
- `experiment` 이슈의 사전 등록 PR 여부와 결과 연결: repo-docs-experiment 흐름
- 서로 독립된 추적 작업이면 이슈부터 분리
- 큰 작업: 브랜치가 아니라 이슈를 하위 이슈로 분할. 하위 이슈마다 브랜치 하나

## 이름

`type/이슈번호-scope-설명`

- 작은 후속 정리도 기존 이슈 번호 (git-issue 과업 연결과 기록)
- type, scope: 커밋과 같은 단어 (git-commit 형식, scope). 브랜치 type은 커밋 type, 이슈 종류와 별개(`build` 이슈의 기능 추가 → `feat`)
- 설명: 영어 소문자 kebab-case, 2~5단어

예 → 뜻:

- `feat/{번호}-api-add-endpoint` → 해당 이슈, api에 엔드포인트 추가
- `fix/{번호}-ui-panel-height` → 해당 이슈, ui 영역 높이 오류
- `docs/{번호}-readme-install` → 해당 이슈, README 설치 방법
- `docs/{번호}-repo-comment-cleanup` → 기존 이슈의 후속 주석 정리
- `v1` → 지난 메이저 수정 브랜치 (예외 형식, 릴리스 절)

## 시작 전 확인

1. git-issue 다음 작업 순서로 이슈 선택
2. `git fetch {원격} --prune`
3. 이슈 작업이면 같은 이슈 번호 브랜치: `git branch -a --list "*/{번호}-*"`
4. 이슈 작업이면 같은 이슈 번호 열린 PR: `gh pr list --state open --search "{번호} in:title,body"`
5. 사용 중인 worktree: `git worktree list`
6. 이슈 작업이면 담당자: 비어 있으면 자기 계정 지정, 다른 사람이면 중단

- 이슈 작업에서 3~5에 같은 이슈가 나오면 새 브랜치 금지
- 사용자가 그 브랜치를 이어서 하라고 지정했으면 이어서 작업, 아니면 중단하고 보고

## 작업 중

- 분기: 최신 기본 브랜치에서 `git switch --no-track -c {브랜치} {원격}/{기본 브랜치}`
- 저장소 정책이 병렬 작업을 허용하고 병렬 실행을 요청받은 경우: 에이전트마다 이슈 하나, 브랜치 하나, worktree 하나. `git worktree add --no-track ../{저장소}.wt/{브랜치의 / 를 - 로} -b {브랜치} {원격}/{기본 브랜치}`
- 병렬 작업 시 같은 생성물·빌드 단위(crate, 패키지)의 검사 담당은 하나. 다른 에이전트는 자기 파일만 수정, 검사 실패 보고. 읽기 검토·독립 조사는 병행 허용
- 검사 시작·종료 시 대상 HEAD 대조, 변경 여부 기록
- 임시 폴더, 저장소 사본, 두 번째 clone 금지. 검사는 자기 worktree에서만
- PR 작업 요청에 자기 작업 브랜치 push 포함. 커밋 요청만으로 push 금지
- 기본 브랜치 변경 반영: `git merge {원격}/{기본 브랜치}`

## PR

- 제목·scope 선택: (git-commit 형식, scope)
- 이슈 연결: git-issue 닫기 절
- 머지 전: `git merge {원격}/{기본 브랜치}` 후 변경된 입력에 대한 검사 실행. 증거 재사용 조건: (code-style 검증)

## 머지

- squash merge만
- squash 메시지: git-commit 형식. 첫 줄은 PR 제목(번호 직접 기재 금지, ` (#{PR 번호})`는 GitHub 기본값), 본문은 PR의 `왜 필요한가`(비우기 금지), 꼬리말은 PR 본문과 같은 `Closes:`·`Refs:`
- GitHub의 자동 커밋 목록 삭제. 작성 표시: (git-commit 금지)
- AI 몫: PR 생성까지. 머지는 요청이 있을 때만
- 머지 후 자기 브랜치 삭제: 원격, 로컬, worktree. 정리 스크립트로 한 번에(정리 절)

## 정리

머지 후 정리 또는 이슈 취소 정리 전 [cleanup.md](references/cleanup.md) 필수 확인

## 릴리스

릴리스·백포트·태그 작업 전 [release.md](references/release.md) 필수 확인

## 금지

- 기본 브랜치·`v{major}` 직접 commit·push
- 같은 이슈 브랜치 중복 생성, 다른 이슈 작업 섞기
- 다른 주체의 브랜치 작업(commit, push 포함)
- 요청 없는 rebase·force push
- 요청 없는 태그·브랜치 보호 설정 변경
