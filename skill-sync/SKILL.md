---
name: skill-sync
description: "스킬을 만들거나 고친 뒤 검사하고 Codex, Claude, Antigravity에 설치할 때 사용. 형식 검사, 설치 스크립트, Claude 계정 zip 업로드"
---

# Skill Sync

- 저장소 안에 같은 역할의 규칙이 있으면 그것 우선. 없으면 이 스킬이 다른 규칙보다 우선
- 범위: 스킬 원본 저장소의 형식 검사, 세 도구 설치, Claude 계정 zip
- 필요할 때만 읽기: 원본 저장소 커밋 → git-commit

- 스킬 원본: 스킬 폴더(`{이름}/SKILL.md`)가 모인 git 저장소 하나. 도구 폴더의 설치본은 복사본
- 스킬 작성 형식: 원본 저장소 `README.md`의 작성 형식 절. 스킬 작성, 수정 전 확인

## 절차

1. 원본 저장소에서 스킬 수정
2. 형식 검사, 출력 `total 0`까지 수정
3. 스킬 연결 줄이나 크기가 바뀌면 원본 저장소 `README.md`의 스킬 연결 표, 크기 표 수정
4. 세 도구에 설치
5. 설치 출력 마지막 줄 `Claude 계정에 올릴 zip`의 파일을 Claude 설정의 스킬 메뉴에 업로드. 브라우저 도구가 있으면 직접 업로드, 없으면 파일 목록 보고
6. 원본 저장소 커밋

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
| Claude 계정(웹, 데스크톱, 원격 세션) | 설정의 스킬 메뉴에 zip 업로드. 업로드 명령과 API 없음(2026-09-30 확인) |

- 도구 폴더가 없는 도구: 설치 제외
- 원본 저장소 찾는 순서: `--source`, 환경 변수 `SKILLS_SOURCE`, 스크립트가 든 git 저장소, 마지막으로 쓴 원본(`~/.config/skills/source`). 모두 없으면 사용자에게 원본 경로 확인
- 관리 범위: 이 스크립트가 설치한 스킬만(도구 폴더의 `.repo-skills.json`). 원본에서 빠진 스킬은 `~/.skill-trash/`로 이동
- 스킬 제거: `install.py --remove {이름}`. 휴지통 폴더로 이동, 영구 삭제 없음
- 바꿀 내용만 확인: `install.py --dry-run`

## 금지

- 설치본 폴더 직접 수정. 다음 설치에서 원본으로 덮어쓰기
- `scripts/`가 있는 스킬을 Claude 저장 카드로 저장. 저장 카드는 SKILL.md만 저장
