# Claude Code와 Codex 설치

- 실행 조건: Python 3.9 이상, 표준 라이브러리, 원본 저장소 작업본. 실행 위치: 원본 저장소 루트
- 기본 대상: 현재 사용자 홈. 별도 대상은 `SKILLS_TARGET_HOME`에 지정하여 아래 명령에 전달
- 도구 홈 생성은 설치할 도구 선택. 아래 예시는 Claude Code와 Codex 모두 선택, Antigravity는 기존 도구 홈이 있을 때만 설치

```sh
skills_target="${SKILLS_TARGET_HOME:-$HOME}"
mkdir -p "$skills_target/.claude" "$skills_target/.codex"
python3 tools/skill-sync/scripts/install.py --source . --target-home "$skills_target"
```

- 확인: 종료 코드 0과 도구별 `설치 성공` 또는 `일치`, 마지막 zip 목록 확인
- 같은 명령 재실행: 기존 manifest로 변경된 스킬만 동기화. 비관리 동명 폴더는 보존하고 충돌 보고
