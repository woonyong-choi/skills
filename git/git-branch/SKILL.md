---
name: git-branch
description: "Git 브랜치를 만들거나 PR 생성, 머지, 릴리스, 머지 뒤 정리를 실행할 때 쓴다."
---

# Git 브랜치

이슈 하나를 짧은 작업 브랜치 하나로 만들고, PR과 squash 머지로 기본 브랜치에 반영한 뒤 정리한다.

## 구조

- 원격, 기본 브랜치, 보호 브랜치는 저장소 설정과 원격 HEAD 조회로 확인한다. 흔한 기본 이름은 `origin`과 `main`이지만 확인 없이 쓰지 않는다.
- 운영 정책이 없으면 영구 브랜치 하나와 짧은 작업 브랜치를 쓴다.
- 기본 브랜치는 늘 빌드와 테스트가 통과하는 상태로 둔다. 기본 브랜치에는 PR로만 반영한다.

## 혼자와 팀

저장소 쓰기 권한이 있는 사람이 1명이면 혼자, 2명 이상이면 팀이다. AI 에이전트는 세지 않는다.

| 항목 | 혼자 | 팀 |
|---|---|---|
| PR | 반드시 연다 | 반드시 연다 |
| 머지 전 리뷰 승인 | 일반 변경은 필요 없다. 계약 승인은 [git-pull-request 검토](../git-pull-request/SKILL.md#검토)를 따른다 | 작성자가 아닌 사람 1명의 승인이 필요하다. 계약 승인은 혼자와 같다 |
| 머지 조건 | [git-pull-request 머지 조건](../git-pull-request/SKILL.md#머지-조건)을 따른다 | 혼자와 같다 |

## 작업 단위

- 작은 일은 이슈 하나, 브랜치 하나, PR 하나, 작업 주체 하나로 진행한다.
- 큰 일은 브랜치가 아니라 이슈를 하위 이슈로 나눈다. 하위 이슈마다 브랜치와 PR을 하나씩 두고 쌓는 스택으로 진행하며, 아래 PR부터 차례로 머지한다. 스택 진행은 **just-mode** 스킬 `playbooks/shipping.md`를 따른다.
- 서로 독립된 추적 작업이면 이슈부터 나눈다.
- 작업에 이슈를 연결하는 기준과 작은 후속 작업이 기존 이슈를 다시 쓰는 기준은 [git-issue 과업 연결과 기록](../git-issue/SKILL.md#과업-연결과-기록)을 따른다.
- 작업 주체는 이슈 담당자와 bind된 과업이다. 재개나 인계 때는 이슈, 작업본, 기록이 서로 맞는지와 기존 작업자가 동시에 고치고 있는지 대조한다. 세션 ID가 바뀐 것만으로 다른 주체라고 판정하지 않는다.
- `experiment` 이슈에서 사전 등록 PR을 열지와 결과를 어떻게 잇는지는 **repo-docs-experiment** 스킬의 흐름을 따른다.

## 이름

브랜치 이름은 `type/이슈번호-scope-설명` 형식이다.

- 작은 후속 정리도 기존 이슈 번호를 쓴다([git-issue 과업 연결과 기록](../git-issue/SKILL.md#과업-연결과-기록)).
- type과 scope는 커밋과 같은 낱말을 쓴다([git-commit 형식](../git-commit/SKILL.md#형식), [scope](../git-commit/SKILL.md#scope)). 브랜치 type은 커밋 type이고 이슈 종류와 별개다. `build` 이슈에서 기능을 더하면 `feat`이다.
- 설명은 영어 소문자 kebab-case로 2~5단어를 쓴다.

| 예 | 뜻 |
|---|---|
| `feat/{번호}-api-add-endpoint` | 해당 이슈에서 api에 엔드포인트를 더한다 |
| `fix/{번호}-ui-panel-height` | 해당 이슈에서 ui 영역 높이 오류를 고친다 |
| `docs/{번호}-readme-install` | 해당 이슈에서 README 설치 방법을 고친다 |
| `docs/{번호}-repo-comment-cleanup` | 기존 이슈의 후속 주석 정리다 |
| `v1` | 지난 메이저 수정 브랜치다. 예외 형식이며 [릴리스](#릴리스) 절을 본다 |

## 시작 전 확인

1. [git-issue 다음 작업](../git-issue/SKILL.md#다음-작업) 순서로 이슈를 고른다.
2. `git fetch {원격} --prune`을 실행한다.
3. 이슈 작업이면 같은 이슈 번호의 브랜치를 찾는다: `git branch -a --list "*/{번호}-*"`.
4. 이슈 작업이면 같은 이슈 번호의 열린 PR을 찾는다: `gh pr list --state open --search "{번호} in:title,body"`.
5. 쓰고 있는 worktree를 본다: `git worktree list`.
6. 이슈 작업이면 담당자를 본다. 비어 있으면 자기 계정을 지정하고, 다른 사람이면 멈춘다.

이슈 작업에서 3~5단계에 같은 이슈가 나오면 새 브랜치를 만들지 않는다. 사용자가 그 브랜치를 이어서 하라고 했으면 이어서 작업하고, 아니면 멈추고 보고한다.

## 작업 중

- 최신 기본 브랜치에서 새 worktree로 분기한다. 워크트리 방식은 **just-mode** 스킬 `playbooks/opening-a-pr.md`를 따른다.

  ```sh
  git worktree add --no-track ../{저장소}.wt/{브랜치의 / 를 - 로} -b {브랜치} {원격}/{기본 브랜치}
  ```

- 스택의 위 PR은 바로 아래 PR의 브랜치에서 분기하고, PR base도 그 브랜치로 둔다.
- 병렬로 실행할 때(사용자 요청, just 자율 실행, orchestrate)는 에이전트마다 이슈 하나, 브랜치 하나, worktree 하나를 쓴다.
- 병렬 작업에서 같은 생성물이나 빌드 단위(crate, 패키지)의 검사는 에이전트 하나만 맡는다. 다른 에이전트는 자기 파일만 고치고 검사 실패를 보고한다. 읽기 검토와 독립 조사는 함께 해도 된다.
- 검사를 시작할 때와 끝낼 때 대상 HEAD를 대조하고 바뀌었는지 기록한다.
- 임시 폴더, 저장소 사본, 두 번째 clone을 만들지 않는다. 검사는 자기 worktree에서만 한다.
- 작업이 끝나면 커밋, 자기 작업 브랜치 push, PR 생성까지 직접 한다. 사용자가 늘 허락해 두었다. 사용자에게 git 명령을 넘기지 않는다.
- 기본 브랜치의 변경은 자기 작업 브랜치를 `git rebase {원격}/{기본 브랜치}`로 그 위에 옮겨 받고, `git push --force-with-lease`로 올린다. 다시 rebase하는 때는 **just-mode** 스킬 `playbooks/shipping.md`가 정한다.

## PR

- PR을 만들거나 머지하기 전에 git-issue `references/project-status.md`를 반드시 읽는다.
- 제목과 scope는 [git-commit 형식](../git-commit/SKILL.md#형식)과 [scope](../git-commit/SKILL.md#scope)를 따른다. 본문은 [git-pull-request](../git-pull-request/SKILL.md)가 정한다.
- 이슈 연결은 [git-issue 닫기](../git-issue/SKILL.md#닫기)를 따른다.
- 머지 전에 기본 브랜치 위로 rebase했으면 바뀐 입력으로 검사를 다시 돌린다. 이전 증거를 다시 쓸 수 있는 조건은 **principle-prove-it-works** 스킬을 따른다.

## 머지

- squash 머지만 쓴다.
- squash 메시지의 정본은 이 절이다. PR 본문 전체를 squash 본문으로 쓰지 않는다. 형식은 [git-commit 형식](../git-commit/SKILL.md#형식)을 따른다.
  - 첫 줄은 `{PR 제목} (#{PR 번호})`다. PR 제목에는 번호를 적지 않는다. `--subject`로 넘기면 GitHub가 번호를 붙이지 않으므로 squash 첫 줄에만 직접 붙인다.
  - 본문은 PR의 `왜 필요한가`이며 비우지 않는다. 꼬리말은 PR 본문과 같은 `Closes #번호`나 `Refs #번호`다.
  - GitHub가 자동으로 넣는 커밋 목록은 넣지 않는다. 작성 표시는 [git-commit 하지 않는 것](../git-commit/SKILL.md#하지-않는-것)을 따른다.
- 머지는 첫 줄과 본문을 지정해 실행한다. 본문은 표준 입력으로 넘기고 임시 파일을 만들지 않는다.

  ```sh
  gh pr merge {PR 번호} --squash --delete-branch --subject '{첫 줄}' --body-file -
  ```
- 머지 조건의 정본은 [git-pull-request 머지 조건](../git-pull-request/SKILL.md#머지-조건)이다. 조건을 채우면 squash 머지와 정리까지 직접 한다. 사용자가 보류하라고 한 PR만 기다린다. 도구 권한에 막히면 막힌 단계, 이유, 사용자가 실행할 한 줄 명령을 보고한다.
- 머지 뒤 훅이 "경력 원본에 남길 성과인가" 확인을 한 줄로 안내한다. 남길 성과면 **hanger** 스킬로 기록한다. 훅이 보지 못하는 머지(웹 화면, MCP 도구)는 머지한 에이전트가 같은 확인을 직접 한다.
- 머지한 뒤 자기 브랜치를 원격, 로컬, worktree에서 지운다([정리](#정리) 절).

## 정리

- 머지한 뒤에는 자기 worktree와 브랜치만 지운다. `git worktree remove {경로}`, `git branch -D {브랜치}`를 실행한다. 다른 작업의 worktree와 브랜치는 지우지 않는다.
- 원격 작업 브랜치는 머지 뒤 `gh pr merge --squash --delete-branch`나 `git push {원격} --delete {브랜치}`로 지운다.
- **just-mode** 스킬 `playbooks/worktree-cleanup.md`의 점검(`worktree-audit.sh`)과 지우는 순서는 사용자가 공간 확보나 대청소를 요청할 때만 쓴다.
- 이슈를 취소하면 PR을 닫고 브랜치를 직접 지운다.

## 릴리스

릴리스, 백포트, 태그 작업 전에 [references/release.md](references/release.md)를 반드시 읽는다.

## 하지 않는 것

- 기본 브랜치와 `v{major}`에 직접 commit하거나 push하지 않는다.
- 같은 이슈의 브랜치를 두 번 만들지 않고, 다른 이슈의 작업을 섞지 않는다.
- 다른 주체의 브랜치에서 작업(commit, push 포함)하지 않는다.
- 공유 브랜치(기본 브랜치, 다른 사람이나 다른 에이전트가 쓰는 브랜치)를 강제 push하거나 기록을 다시 쓰지 않는다. 꼭 필요하면 just-mode의 항상 멈출 일로 보고 멈춘다. 자기 작업 브랜치의 rebase, amend, `--force-with-lease` push는 [작업 중](#작업-중) 절과 [git-commit 하지 않는 것](../git-commit/SKILL.md#하지-않는-것)을 따른다.
- 요청 없이 태그나 브랜치 보호 설정을 바꾸지 않는다.

## 답변

- 만든 브랜치, PR 번호와 주소, 머지했으면 squash 커밋의 짧은 해시를 적는다.
- 같은 이슈의 브랜치나 PR이 있어 멈췄으면 찾은 브랜치와 PR을 적는다.
- 권한에 막혔으면 막힌 단계, 이유, 사용자가 실행할 한 줄 명령을 적는다.

## 구분

- 다음 작업 고르기와 시작 전 막힘 확인은 [git-issue 다음 작업](../git-issue/SKILL.md#다음-작업)이 맡는다.
- 커밋 메시지, PR 제목, squash 메시지의 형식은 [git-commit](../git-commit/SKILL.md)이 맡는다.
- PR 본문, 검토, 머지 조건은 [git-pull-request](../git-pull-request/SKILL.md)가 맡는다.
- 검사 범위와 증거는 **principle-prove-it-works** 스킬이 맡는다.
- PR 스택의 머지 순서는 **just-mode** 스킬 `playbooks/shipping.md`가 맡는다. 공간 확보와 대청소는 `playbooks/worktree-cleanup.md`가 맡는다.
