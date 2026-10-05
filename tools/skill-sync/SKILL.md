---
name: skill-sync
description: "스킬 원본의 형식·참조를 검사하거나 요청한 도구 설치·Claude 계정 배포를 수행할 때 사용."
---

# Skill Sync

- 우선순위: 해당 주제의 사용자 지시 → 저장소 규칙 → 이 스킬. 중복 규칙은 머리에 연결한 정본 스킬 적용
- 범위: 스킬 원본 저장소의 형식 검사, 세 도구 설치, Claude 계정 zip
- 필요할 때만 읽기: 원본 저장소 커밋 → git-commit

- 스킬 원본: 스킬 폴더(`{분류}/{이름}/SKILL.md` 또는 `{이름}/SKILL.md`)가 모인 git 저장소 하나. 도구 폴더의 설치본은 복사본
- 제공 탐색기의 지원 입력: 원본 루트 바로 아래 스킬과 다음 다섯 분류 바로 아래 스킬만. 다른 분류는 `--source`로 해당 폴더 지정. 실험·시험 fixture는 탐색 제외
- 분류 폴더: `git`, `code`, `docs`, `design`, `tools`. 설치 대상에서는 분류 없이 기존 스킬 이름 유지. 같은 이름의 원본이 둘 이상이면 오류
- 작성 규약 위치: 대상 원본 저장소가 지정한 파일을 입력으로 확인. 이 저장소에서는 [스킬 작성 형식](references/authoring.md) 적용

## 절차

1. 요청 범위 결정. 검사만 요청하면 읽기 전용 검사와 결과 보고 후 종료
2. 수정 요청 시 원본 수정과 형식 검사, 출력 `total 0` 확인
3. 함께 읽는 스킬의 연결과 조건 교차 확인. 자동 생성 목록이 있으면 해당 생성 절차로 갱신
4. 설치 요청이 있으면 지정 도구에 설치하고 대상별 성공·충돌·실패와 종료 코드 확인
5. 계정 배포 요청이 있으면 공식 배포 방식 확인 후 선택 어댑터 적용. 업로드 목록은 설치 출력의 `Claude 계정에 올릴 zip` 사용
6. 업로드 불가 시 파일 목록과 실행하지 못한 이유 보고
7. 커밋 요청이 있으면 원본 저장소 커밋

```sh
python3 <이 스킬 폴더>/scripts/skill_check.py <원본 저장소>
python3 <이 스킬 폴더>/scripts/install.py
```

- 스크립트 실행 전 [실행 경로·Windows 명령](references/execution.md) 필수 확인

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
- Claude 계정에 업로드할 zip 생성 폴더: `--dist {폴더}`. 기본은 원본 저장소의 `dist/claude`. 설치·원본 포인터·휴지통의 홈 경로는 `--target-home {폴더}`로 지정, 생략 시 현재 사용자 홈 사용
- Claude 계정 zip 구성: 루트 스킬 폴더의 `SKILL.md` 하나만 포함. `SKILL.md`가 있는 하위 폴더는 그 안의 파일까지 제외, 나머지 보조 파일은 기존 제외 규칙에 따라 포함. 세 도구 폴더 설치본은 기존 구성 유지
- zip 검사: 기존 zip의 `SKILL.md` 개수·위치와 캐시 파일 확인, 위반 시 재생성. 새 zip도 같은 검사 후 교체, 위반 시 설치 실패(종료 코드 1)
- 검사 의존 스킬: 검사 스크립트와 같은 원본 루트의 `code/code-style/scripts/check_cost_comments.py`를 우선 사용, 없으면 평탄한 설치 루트의 `code-style/scripts/check_cost_comments.py` 사용. 검사 대상 root와 별개인 실행 위치 기준 의존, 누락 시 입력 오류. 참조 링크는 원본형과 평탄한 설치형 양쪽에서 확인
- skill_check: frontmatter·description 형식, 이름과 폴더 일치, 머리 참조·절 구조·용어·규칙 복제·스크립트 인자와 출력·비용 주석 검사. 판정 기준과 자동 검사 한계: [일관성 검사 기준](references/consistency.md). `agents/openai.yaml`의 필수 필드와 스킬 호출 이름도 검사. 목록·표의 끝말은 스킬 작성 형식 기준으로 검사. 종료 코드: 위반 1, 입력 오류 2, 전체 통과 0

### Claude Code와 Codex 설치

도구 설치 실행 전 [installation.md](references/installation.md) 필수 확인

## 선택 어댑터

Claude 계정 업로드·삭제·교체 또는 UI 탐색 전 [claude-upload.md](references/claude-upload.md) 필수 확인

## 금지

- 설치본 폴더 직접 수정. 다음 설치에서 원본으로 덮어쓰기
- `scripts/`가 있는 스킬을 Claude 저장 카드로 저장. 저장 카드는 SKILL.md만 저장
