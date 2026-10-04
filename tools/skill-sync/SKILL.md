---
name: skill-sync
description: "스킬 원본의 형식·참조를 검사하거나 요청한 도구 설치·Claude 계정 배포를 수행할 때 사용."
---

# Skill Sync

- 사용자 지시를 먼저 적용. 해당 주제의 사용자 지시가 없으면 작업 대상 저장소의 같은 주제 규칙 파일(예: `AGENTS.md`, `CONTRIBUTING.md`) 적용. 둘 다 없으면 이 스킬 적용. 다른 스킬과 겹치는 규칙은 머리의 연결에 적힌 스킬 중 그 규칙을 정한 스킬 적용
- 범위: 스킬 원본 저장소의 형식 검사, 세 도구 설치, Claude 계정 zip
- 필요할 때만 읽기: 원본 저장소 커밋 → git-commit

- 스킬 원본: 스킬 폴더(`{분류}/{이름}/SKILL.md` 또는 `{이름}/SKILL.md`)가 모인 git 저장소 하나. 도구 폴더의 설치본은 복사본
- 분류 폴더: `git`, `code`, `docs`, `design`, `tools`. 설치 대상에서는 분류 없이 기존 스킬 이름 유지. 같은 이름의 원본이 둘 이상이면 오류
- 작성 규약 위치: 대상 원본 저장소가 지정한 파일을 입력으로 확인. 이 저장소에서는 README 작성 형식 절 적용

## 절차

1. 원본 저장소에서 스킬 수정
2. 형식 검사, 출력 `total 0`까지 수정
3. 함께 읽을 스킬과 읽는 조건은 각 `SKILL.md` 머리에서 확인. 이 연결로 자동 생성한 목록이 있으면 그 목록의 생성 절차를 실행해 갱신
4. 요청한 도구에 설치, 대상별 성공·충돌·실패와 종료 코드 확인
5. 계정 배포를 요청한 경우에만 공식 배포 방식 확인 후 6~7번 진행. 요청이 없으면 8번으로 이동. 업로드할 파일은 설치 출력 마지막 줄 `Claude 계정에 올릴 zip`의 목록 사용
6. 브라우저 도구가 있으면 Claude 설정의 스킬 메뉴에서 업로드. 같은 이름의 스킬을 교체할 때는 아래 지원 환경에서 `node <이 스킬 폴더>/scripts/claude_upload.mjs --replace {이름,...}` 실행
7. 업로드할 수 없으면 업로드할 파일 목록과 실행하지 못한 이유 보고
8. 원본 저장소 커밋

```sh
python3 <이 스킬 폴더>/scripts/skill_check.py <원본 저장소>
python3 <이 스킬 폴더>/scripts/install.py
```

- `<이 스킬 폴더>`: 이 SKILL.md가 있는 폴더. 스크립트 본문은 읽지 않고 실행만. Windows에서 `python3`가 없으면 `py -3`

## 설치

| 도구 | 위치 |
|---|---|
| Codex | `~/.codex/skills/` |
| Antigravity | `~/.gemini/config/skills/` |
| Claude Code | `~/.claude/skills/` |
| Claude 계정(웹, 데스크톱, 원격 세션) | 실행 때 확인한 공식 배포 방식 사용. 아래 UI 스크립트는 지원 환경에 한정 |

- 도구 폴더가 없는 도구: 설치 제외
- 원본 저장소 찾는 순서: `--source`, 환경 변수 `SKILLS_SOURCE`, 스크립트가 든 git 저장소, 마지막으로 쓴 원본(`~/.config/skills/source`). 모두 없으면 사용자에게 원본 경로 확인
- 관리 범위: 이 스크립트가 설치한 스킬만(도구 폴더의 `.repo-skills.json`). manifest에 없는 같은 이름 폴더는 충돌로 남기고 설치 제외. 원본에서 빠진 manifest 항목은 대상 폴더를 `~/.skill-trash/`로 이동, Claude 배포 zip과 manifest 항목 정리
- 스킬 제거: `install.py --remove {이름}`. 설치 목록 파일 `.repo-skills.json`에 있는 단일 스킬 이름만 허용. 대상이 도구 설치 폴더 바로 아래에 있고 심볼릭 링크가 아닌지 확인한 뒤 휴지통 이동과 목록 갱신. 원본에 남아 있으면 다음 동기화 때 재설치
- 바꿀 내용만 확인: `install.py --dry-run`
- Claude 계정에 업로드할 zip 생성 폴더: `--dist {폴더}`. 기본은 원본 저장소의 `dist/claude`. 도구 설치 폴더의 홈 경로는 실행 환경의 `HOME` 사용
- skill_check: frontmatter 형식, 이름과 폴더 일치, 머리에서 연결한 스킬의 존재 여부 검사. `agents/openai.yaml`의 필수 필드와 스킬 호출 이름도 검사. 목록·표의 끝말은 README 작성 형식 기준으로 검사. 종료 코드: 위반 1, 입력 오류 2, 전체 통과 0

## Claude 계정 업로드 스크립트

- 지원 환경: macOS의 시스템 Chrome(`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`), 한국어 계정 UI. 다른 환경은 이 스크립트의 검증 대상 밖
- 요구 조건: Node, 전역 `playwright-core`(`npm install -g playwright-core`, 스킬 폴더에 `node_modules` 금지), 시스템 Chrome
- 인자: `--upload {이름,...}` 업로드, `--delete {이름,...}` 삭제, 없으면 계정에 없는 zip 목록만 보고. 업로드와 삭제 뒤 스킬 목록을 다시 읽어 확인. `--source {원본}`
- 같은 이름 스킬 교체: `--replace {이름,...}`. 계정에 있으면 삭제(확인 대화상자까지) 뒤 업로드. zip이 없으면 삭제 전에 중단, 업로드 확인 실패 시 목록 재확인 경고와 복구용 zip 경로 출력
- 프로필: `~/.config/skills/browser-profile`(권한 700). 로그인 쿠키가 남음. 다른 Chrome 프로필 복사 금지. 비밀번호 저장 없음
- 흐름: 현재 스크립트는 화면 밖 Chrome 창 사용. 로그인·보안 확인이 필요하면 진단 화면 저장 뒤 자동화 중단, 보안 확인 우회 금지
- 업로드 확인: 현재 UI 스크립트는 실제 스킬 행이 로드된 계정만 지원. 스킬이 없는 계정의 최초 업로드와 계정에 하나만 남은 스킬의 교체는 미지원으로 보고 후 중단. 각 업로드 뒤 상세 화면에서 목록으로 복귀, 이름과 갱신 시각 확인. 전체 작업 뒤 목록 재조회로 각 이름과 경과 시각 확인
- 화면 구조가 다르거나 버튼을 못 찾으면 못 찾은 항목과 스크린샷 경로를 출력하고 실패 코드로 종료. 진단 파일은 `~/.config/skills/browser-logs/`에만
- 삭제는 `--delete` 또는 `--replace`로 명시한 이름만. 원본에 없는 계정 스킬 자동 삭제 금지
- 화면 탐색용 `--probe [--click {글자|btn:이름}]`: 화면 글자와 컨트롤 목록 출력

## 금지

- 설치본 폴더 직접 수정. 다음 설치에서 원본으로 덮어쓰기
- `scripts/`가 있는 스킬을 Claude 저장 카드로 저장. 저장 카드는 SKILL.md만 저장
