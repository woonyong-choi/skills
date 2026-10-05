# 정리

머지가 끝나면 저장소 안에서 실행. 먼저 미리보기, 목록 확인 뒤 `--apply`

```sh
python3 <이 스킬 폴더>/scripts/cleanup_merged.py <PR 번호 또는 브랜치>
python3 <이 스킬 폴더>/scripts/cleanup_merged.py <PR 번호 또는 브랜치> --apply
```

- 스크립트 실행 전 skill-sync `references/execution.md` 필수 확인
- 실행 조건: Python 3.9 이상, Git, 인증된 GitHub CLI. 정리 명령은 GitHub 전용 어댑터이며 지정 원격과 gh 대상 저장소 일치 확인
- 입력 정책: `--remote` 기본 origin, 기본 브랜치는 원격 HEAD 조회 또는 `--default-branch` 지정. 조회 실패 시 중단. main·master 보호는 유지하고 `--protect` 반복으로 추가 보호 지정
- 대상: 지정한 GitHub 머지 PR의 로컬 브랜치 worktree, 로컬 브랜치, 원격 브랜치
- PR 마지막 head SHA와 로컬 브랜치 head 일치 필수. 로컬 브랜치가 없거나 SHA가 다르면 `skip:` 이유 출력
- 원격 브랜치가 있으면 같은 SHA인지 확인 후 정리. SHA가 다르면 `skip:` 이유 출력. 원격 브랜치가 이미 없으면 로컬만 정리
- 커밋 안 된 변경이 있는 worktree는 남기고 `skip:` 이유 출력
- 병렬 작업 완료 뒤 `git worktree list`·`git branch`를 저장소의 보호 브랜치·열린 작업 목록과 대조. 다른 작업의 worktree 정리 금지
- 장기 브랜치 알림: 저장소 기간·기준 시각 정책 우선. 없으면 브랜치 최초 고유 커밋 시각부터 7일 경과한 미머지 브랜치 보고. 생성 시각으로 간주 금지
- 이슈 취소 시 PR 닫기, 브랜치 삭제
