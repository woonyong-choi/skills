# 선택 어댑터

Claude 계정에 스킬을 올리고 교체한 뒤 계정 목록과 로컬 원본을 대조한다. 개인 계정용 공식 API나 CLI가 확인되지 않아 브라우저 UI 어댑터를 쓴다.

## Claude 계정 배포

```sh
python3 tools/skill-sync/scripts/deploy.py
python3 tools/skill-sync/scripts/deploy.py --dry-run
python3 tools/skill-sync/scripts/deploy.py --login
python3 tools/skill-sync/scripts/deploy.py --prune --dry-run
python3 tools/skill-sync/scripts/deploy.py --prune
```

- 원본 루트에서 실행한다. 다른 위치에서는 스크립트 경로와 `--source {원본}`을 지정한다.
- Python 3.9 이상, Node 22 이상, macOS 시스템 Chrome, 한국어 계정 UI, 전역 `playwright-core`(`npm install -g playwright-core`)가 필요하다. 스킬 폴더에 `node_modules`를 두지 않는다.

기본 명령은 다음 순서로 돈다.

1. 원본을 검사해 `total 0`인지 본다.
2. Claude Code와 Codex에 설치한다. 도구 홈이 없으면 만들고, Antigravity는 기존 홈이 있을 때만 설치한다.
3. zip을 다시 만든다.
4. 계정과 대조해 반영한다.
5. 목록을 다시 조회하고, 로컬과 zip의 `SKILL.md` SHA-256 대조 표를 낸다.

- 계정에 이름이 없으면 올린다. 영수증이 없거나, 원본 해시나 description이나 계정 갱신 시각이 다르면 교체한다. 같은 이름이 중복되면 실패한다. 원본에 없는 스킬은 기본으로 그대로 두고 보고한다. `--prune`을 주면 계정 목록에서 "내가 만든" 스킬 중 원본에 없는 것을 모두 지우고 영수증에서도 뺀다. Anthropic·파트너 제공 스킬은 지우지 않는다. 원본에서 지우거나 이름을 바꾼 스킬을 계정에서 정리할 때 쓰며, 먼저 `--prune --dry-run`으로 지울 목록을 확인한다.
- 교체할 때는 zip이 있는지 확인한 뒤 기존 항목을 지우고 올린다. 중단된 항목은 영수증 없이 남긴다. 원인을 고친 뒤 같은 명령을 다시 실행해 복구한다.
- `--dry-run`은 로컬, zip, 계정의 변경 목록만 출력하고 설치, 업로드, 영수증 쓰기를 하지 않는다. 계정 목록을 읽으므로 저장된 프로필이 정상 로그인 상태여야 한다.
- 종료 코드는 성공 0, 검사, 설치, 인증, 업로드, 대조 실패 1, 인자 오류 2다. zip 생성 기록 `.repo-skills.json`으로 계정 배포가 성공했다고 판정하지 않는다.

## 영수증과 인증

- 계정 영수증은 `~/.config/skills/claude-account.json`에 권한 600으로 두고 원자적으로 교체한다. 형식은 다음과 같다.

  ```json
  {"version":1,"skills":{"이름":{"sourceHash":"sha256","skillHash":"sha256","description":"설명","accountUpdatedAt":"계정 시각","verifiedAt":"UTC 시각"}}}
  ```

- `sourceHash`는 설치 제외 규칙을 적용한 원본의 상대 경로와 내용의 해시다. `skillHash`는 원본 `SKILL.md`의 SHA-256이다.
- 올린 뒤 목록에서 이름과 description을 다시 확인한 항목만 영수증에 저장한다. 교체에 실패하면 이전 영수증을 무효로 한다.
- 계정에 올라간 파일 내용의 해시를 원격에서 다시 잴 수는 없다. 영수증은 올린 원본과 목록 확인의 기록이다. 계정의 이름, description, 갱신 시각은 실행할 때마다 다시 조회한다.
- 로그인 프로필은 `~/.config/skills/browser-profile`(700)에 둔다. 다른 프로필을 복사하지 않고, 비밀번호, 쿠키, 토큰을 출력하거나 저장소에 저장하지 않는다.
- 자동 실행은 화면 밖 일반 Chrome에서 한다. 로그인이 만료되거나 보안 확인이 나오면 진단 PNG 경로와 `--login` 명령을 출력하고 실패한다. 우회하거나 자동으로 다시 시도하지 않는다.
- 사람이 하는 단계는 하나뿐이다. `--login`으로 열린 창에서 로그인과 보안 확인을 마치고 창을 닫는다. 이 명령은 배포를 하지 않으므로 그 뒤에 기본 명령을 다시 실행한다.
- headless 창이든 일반 창이든 인증이 성공한다고 가정하지 않는다. 보안 확인이 나오면 위 인증 절차를 따른다.
- 진단 파일은 `~/.config/skills/browser-logs/`에 둔다. 화면 구조가 맞지 않으면 실패한다. 계정 배포는 실제 업로드와 목록 재조회로 검증한다.

## 공식 경로 확인

2026-10-05에 다음을 확인했다.

- [API 문서](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#cross-surface-availability)는 API 업로드와 claude.ai가 따로라고 적는다.
- [계정 도움말](https://support.claude.com/en/articles/12512180-use-skills-in-claude)은 ZIP을 UI로 올리는 방법을 적는다.
- [Claude Code 문서](https://code.claude.com/docs/en/skills)는 로컬 폴더와 플러그인 배포를 적는다.
