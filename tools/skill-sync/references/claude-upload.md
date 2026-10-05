# 선택 어댑터

## Claude 계정 배포

```sh
python3 tools/skill-sync/scripts/deploy.py
python3 tools/skill-sync/scripts/deploy.py --dry-run
python3 tools/skill-sync/scripts/deploy.py --login
```

- 실행 위치: 원본 루트. 다른 위치에서는 스크립트 경로와 `--source {원본}` 지정
- 지원 환경: Python 3.9 이상, Node 22 이상, macOS 시스템 Chrome, 한국어 계정 UI, 전역 `playwright-core`(`npm install -g playwright-core`). 스킬 폴더에 `node_modules` 금지
- 기본 흐름: 원본 검사 `total 0` → Claude Code·Codex 설치(도구 홈 없으면 생성, Antigravity는 기존 홈만) → zip 재생성 → 계정 대조·반영 → 목록 재조회·로컬과 zip의 `SKILL.md` SHA-256 대조 표
- 계정 판정: 이름 없음은 업로드, 영수증 없음·원본 해시 차이·description 차이·계정 갱신 시각 차이는 교체. 같은 이름의 중복은 실패, 원본 밖 스킬은 보존·보고
- 교체: zip 존재 확인 뒤 기존 항목 삭제·업로드. 중단된 항목은 영수증 없이 유지, 원인 해결 뒤 같은 명령 재실행으로 복구
- `--dry-run`: 로컬·zip·계정 변경 목록만 출력, 설치·업로드·영수증 쓰기 없음. 계정 목록을 읽으므로 저장 프로필의 정상 로그인 필요
- 성공 0, 검사·설치·인증·업로드·대조 실패 1, 인자 오류 2. zip 생성 기록 `.repo-skills.json`으로 계정 성공 판정 금지

## 영수증과 인증

- 계정 영수증: `~/.config/skills/claude-account.json`, 권한 600, 원자 교체. 형식: `{"version":1,"skills":{"이름":{"sourceHash":"sha256","skillHash":"sha256","description":"설명","accountUpdatedAt":"계정 시각","verifiedAt":"UTC 시각"}}}}`
- `sourceHash`: 설치 제외 규칙을 적용한 원본 상대 경로·내용 해시. `skillHash`: 원본 `SKILL.md` SHA-256. 업로드 뒤 목록에서 이름·description 재확인한 항목만 저장, 실패한 교체의 이전 영수증 무효화
- 계정 파일 내용 해시의 원격 재측정은 미지원. 영수증은 업로드한 원본과 목록 확인의 기록이며 계정 이름·description·갱신 시각은 매 실행 재조회
- 로그인 프로필: `~/.config/skills/browser-profile`(700). 다른 프로필 복사, 비밀번호·쿠키·토큰 출력과 저장소 저장 금지
- 자동 실행: 화면 밖 일반 Chrome. 로그인 만료·보안 확인 시 진단 PNG 경로와 `--login` 명령 출력 후 실패, 우회·자동 재시도 금지
- 사람의 유일한 단계: `--login`으로 보이는 창에서 로그인·보안 확인 후 창 닫기. 배포 작업은 실행하지 않으며 이후 기본 명령 재실행 필요
- 진단 위치: `~/.config/skills/browser-logs/`. 화면 구조 불일치는 실패, 모델 호출 없이 가짜 계정 어댑터로 시험

## 공식 경로 확인

2026-10-05 확인 결과, [API 문서](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#cross-surface-availability)는 API 업로드와 claude.ai의 분리를 명시한다. [계정 도움말](https://support.claude.com/en/articles/12512180-use-skills-in-claude)은 ZIP UI 업로드를, [Claude Code 문서](https://code.claude.com/docs/en/skills)는 로컬 폴더·플러그인 배포를 안내한다. 개인 계정에 올리는 공식 API·CLI는 확인되지 않아 UI 어댑터를 사용한다.

같은 저장 프로필로 재확인한 headless는 보안 확인 화면에서 중단됐다. 화면 밖 일반 Chrome은 목록 조회에 성공했으나 뒤 실행에서 보안 확인이 다시 나타났다. 따라서 일반 창도 인증 성공을 보장하지 않으며 보안 확인 시 위 인증 절차를 따른다.
