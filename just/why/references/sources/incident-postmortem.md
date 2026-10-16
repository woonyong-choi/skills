# 장애와 포스트모템 맥락

- **Linear.** `incident`, `sev-*`, `postmortem-action-item`, `reliability` 라벨이 붙은 티켓을 찾는다.
- **Slack.** 대상 코드가 추가된 날짜 즈음의 `#sev-*`, `#incident-*` 채널을 검색한다.
- **Git.** "fix for incident", "add defensive check" 같은 메시지의 커밋, "revert" 뒤에 "re-apply with..."가 오는 커밋은 강한 신호다.
