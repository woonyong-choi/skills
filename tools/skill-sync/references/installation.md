# Claude Code와 Codex 설치

원본 저장소의 스킬을 Claude Code와 Codex(있으면 Antigravity) 도구 폴더에 설치하고 결과를 확인한다.

## 단계

원본 저장소 루트에서 실행한다. Python 3.9 이상, 표준 라이브러리, 원본 저장소 작업본이 필요하다. 기본 대상은 현재 사용자 홈이고, 다른 대상은 `SKILLS_TARGET_HOME`에 지정해 아래 명령에 넘긴다.

```sh
skills_target="${SKILLS_TARGET_HOME:-$HOME}"
mkdir -p "$skills_target/.claude" "$skills_target/.codex"
python3 tools/skill-sync/scripts/install.py --source . --target-home "$skills_target"
```

- 도구 홈이 있는 도구에만 설치한다. 위 `mkdir`은 Claude Code와 Codex를 고를 때만 쓴다. Antigravity는 기존 홈이 있을 때만 설치한다.
- 종료 코드 0, 도구별 `설치 성공`이나 `일치`, 마지막 zip 재생성 목록을 확인한다. 계정 배포 상태는 설치 명령으로 확인되지 않는다.
- 같은 명령을 다시 실행하면 기존 manifest로 바뀐 스킬만 동기화한다. 관리하지 않는 같은 이름 폴더는 그대로 두고 충돌로 보고한다.
- 지정한 도구만 갱신하려면 `--tool codex --tool claude-code`처럼 반복해 지정한다. 생략하면 기존 도구 홈 전체를 갱신한다. 다른 도구를 바꿀 권한이 없으면 반드시 대상을 좁힌다.

## just do 플러그인

- 플러그인의 설치 ID는 `just-do`다.
- mode를 설치하면 사용자 스킬 설정에 안정된 훅 진입점 `just-do.py`를 설치한다. 런타임 교체와 훅 실행은 공유 잠금으로 조율한다.
- 플러그인 설치와 신뢰 확인은 mode `references/hooks.md`의 설치 절을 따른다.
