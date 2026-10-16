### 워크트리와 시뮬레이터 정리

1. 스냅샷을 찍고 점검한다. `df -h /`를 기록한 뒤 `<just-mode 스킬 폴더>/scripts/worktree-audit.sh [-b <pr-base-ref>] [repo-path]`를 실행한다(principle-build-the-lever). `-b`가 없으면 `MERGED`를 `origin/HEAD` 기준으로 확인하므로, PR이 다른 브랜치를 향하면 `-b origin/<branch>`를 넘긴다. 경로는 손으로 치지 않고 `git worktree list`에서 읽는다. 손으로 친 `myrepo-worktrees/x`는 `.claude/worktrees/x`처럼 다른 곳에 있는 워크트리를 놓친다(principle-encode-lessons-in-structure). 스크립트는 워크트리마다 크기, 나이, 머지 상태, 커밋 안 된 작업, PR 상태, 그 워크트리를 건드린 가장 최근 대화로 분류하고 분류 칸을 제안한다. 대화 기록 훑기는 느리므로 백그라운드로 돌린다.
2. 분류 칸은 조언이지 허락이 아니다. 실제 기준은 지금 그 워크트리를 쓰는 세션이다(principle-prove-it-works). 후보마다 최근 대화 기록에서 그 워크트리 경로를 쓰는 세션이 있는지([호스트 대응표](../references/hosts.md)의 대화 기록 위치) 확인하고, 사용자가 알려 준 진행 중 세션과도 대조한다. 도구가 진행 중 세션이 쓰던 워크트리를 `safe`로 표시한 적이 있으므로, 사용 중인 세션 확인이 이긴다.
3. 지우기 전에 사용 여부를 검증한다. `verify-recent-chat` 줄과 의심스러운 것마다 서브에이전트를 병렬 분배해 대화 기록을 읽고, 그 세션이 진행 중인지와 어떤 워크트리를 건드리는지 보고하게 한다(principle-guard-the-context-window, 대화 기록은 양이 많다). 진행 중인 세션은 백그라운드 서브에이전트로 arena와 재현용 트리를 형제 워크트리에 만든다. 그 이름이 세션 목록에 보이지 않아도 사용 중이다. 서브에이전트마다 일에 맞는 역할([역할별 모델](../references/models.md))과 추론 수준을 SKILL.md의 서브에이전트 절에 따라 고른다.
4. 되돌릴 수 없는 손실 앞에서 멈춘다. `wip:N`은 추적 중인 파일의 커밋 안 된 수정 N개다. diff를 보여 주고 먼저 결정을 받는다. 깨끗한 워크트리는 지워도 브랜치에서 되살릴 수 있지만 커밋 안 된 작업은 사라진다. `scratch:N`은 추적 안 된 버릴 파일이라 지워도 되지만 파일 이름은 밝힌다. SKILL.md의 자율 절에 따라, 깨끗하고 머지됐고 사용 중이 아니면 진행한다. `wip`과 사용 중이면 멈춘다.
5. 확인된 집합을 지운다. 경로마다 `git worktree remove --force <path>`. 무시된 빌드 결과물 때문에 폴더가 남으면 `rm -rf`로 지운 뒤 `git worktree prune`. 브랜치 ref는 남으므로 커밋은 잃지 않는다. `df -h /`와 다시 나열한 목록으로 확인한다.
6. 그 밖에 공간을 되찾을 곳. 패키지 캐시(pnpm, uv, brew, yarn). macOS일 때는 시뮬레이터가 보통 다음으로 큰 몫이다. `xcrun simctl --set testing delete all`(XCTestDevices 복제본), `xcrun simctl delete unavailable`, 그리고 옛 런타임은 `xcrun simctl runtime list` 뒤 `runtime delete <id>`. 더 필요하면 macOS일 때 Xcode `DerivedData`와 `iOS DeviceSupport`. 사용자가 남기라고 한 캐시는 지우지 않는다.

코드 리뷰가 실수를 잡아 주지 않는 상태에서 사용자 상태를 지우는 유일한 플레이북이다. 그래서 위의 게이트(통과해야 다음으로 가는 검사)가 리뷰다.

**답변:** 전후 `df -h /`와 되찾은 공간, 지운 워크트리, 남겨 둔 것마다 이유 한 줄(어느 세션이 사용 중인지, 또는 커밋 안 된 작업).
