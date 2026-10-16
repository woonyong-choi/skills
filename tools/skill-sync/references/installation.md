# Claude Code와 Codex 설치

- 실행 조건: Python 3.9 이상, 표준 라이브러리, 원본 저장소 작업본. 실행 위치: 원본 저장소 루트
- 기본 대상: 현재 사용자 홈. 별도 대상은 `SKILLS_TARGET_HOME`에 지정하여 아래 명령에 전달
- 도구 홈이 있는 도구만 설치. 아래 `mkdir`는 Claude Code·Codex 선택, Antigravity는 기존 홈이 있을 때만

```sh
skills_target="${SKILLS_TARGET_HOME:-$HOME}"
mkdir -p "$skills_target/.claude" "$skills_target/.codex"
python3 tools/skill-sync/scripts/install.py --source . --target-home "$skills_target"
```

- 확인: 종료 코드 0과 도구별 `설치 성공` 또는 `일치`, 마지막 zip 재생성 목록 확인. 계정 배포 상태는 설치 명령에서 미확인
- 같은 명령 재실행: 기존 manifest로 변경된 스킬만 동기화. 비관리 동명 폴더는 보존하고 충돌 보고
- 지정 도구만 갱신: `--tool codex --tool claude-code`처럼 반복 지정. 생략 시 기존 도구 홈 전체, 다른 도구 변경 권한이 없으면 대상 제한 필수
- Developer Thinking 플러그인(설치 ID `work-continuity`): git-issue 설치 시 사용자 스킬 설정에 안정된 훅 진입점 설치. 런타임 교체와 훅 실행은 공유 잠금으로 조율. 플러그인 정의 갱신·신뢰 확인은 git-issue `references/continuity-hosts.md`의 설치 절 적용
