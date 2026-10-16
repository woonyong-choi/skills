---
name: career-record
description: "경력 원본에 프로젝트·성과를 추가·병합·수정하거나 PR 머지 뒤 경력 기록 여부를 판단할 때 사용."
---

# Career Record

- 우선순위: 사용자 지시 → 저장소 규칙 → 이 스킬. 범위 밖은 명시한 소유 스킬 적용
- 범위: 경력 원본(`<Vault>/career/`)의 형식, 추가·병합·수정·삭제, 등급, PR 머지 뒤 기록 판단, 원본 초안과 빈칸 채우기. JD 없이 동작
- 필요할 때만 읽기: 질문·빈칸·완료 보고 문장 → html-report 작성 규칙과 낯선 말 목록(html-report `references/unfamiliar-words.md`); 그림 원본 작성 → repo-docs-figures `references/syntax.md`

## 경계

- career-record: 원본 추가·병합·수정·등급. 원본 형식의 유일한 정본
- career: 원본 읽기·고르기만, 원본 수정 금지. JD 맞춤 이력서·포트폴리오는 career
- 공고 폴더(`{마감일}-{회사명}-{직군명}/`) 수정 금지

## 명령

원본 파일 작성·수정·검사 전 [원본 형식](references/format.md) 필수 확인

`python3 <이 스킬 폴더>/scripts/record.py <명령>`. Python 3.9+, git-issue 스킬 필요(Vault 해석·설정 폴더). stdout JSON, 종료 0 성공·1 검사 위반 또는 위치 거부·2 인자 오류·3 질문 필요

- `check`: 구조 검사(짝, 8칸 순서, 10줄, 등급, 파일 안 상위 이름, 폐지된 cases·master 절)
- `new-project {소속}[/{팀}]/{프로젝트} --set 속성=값 [--org 구분=재직]`: 새 프로젝트 폴더와 없는 소속.md·팀.md
- `add {프로젝트} --first "{첫 줄}" [--set 칸=값] [--pr {PR 주소}] [--similar "{비슷한 줄}"] [--locations N] [--yes]`
- `merge {프로젝트} --line "{첫 줄}" [--set 칸=값] [--pr {PR 주소}] [--yes]`
- `fill {프로젝트} --line "{첫 줄}" --set 칸=값`: 빈칸 답만, 미확인 칸만
- `edit {프로젝트} --line "{첫 줄}" [--set 칸=값] [--new-first "{새 첫 줄}"]`: 상태 변화·고침, 첫 줄을 바꾸면 묶음 제목도
- `remove {프로젝트} --line "{첫 줄}" [--yes]`: 줄과 짝 묶음 삭제
- `locate --remote {원격} [--author {PR 작성자}]`, `screen {PR JSON} --user {계정}`, `blanks`, `mode [normal|bypass]`, `since`, `stamp`
- `--pr`: 근거 칸에 PR 주소 자동 추가. 등급은 계산값만, `--set 등급` 금지
- 종료 3: 출력 `ask` 문장을 그대로 사용자에게 질문, 답을 받으면 `--yes`로 다시 실행. 파일 0개 상태
- 쓰기 전 검사: 등록 Vault 해석(project_context 함수 직접 호출) → 대상이 `<Vault>/career/` 아래·공고 폴더 밖. 실패면 파일 0개
- 포트폴리오.md 묶음 본문: Write·Edit 도구로 작성 → `check`

## 모드

설정: `<설정 폴더>/career-record.json`(`vault.json`과 같은 폴더, 기본 `~/.config/skills`). `mode`(기본 normal)와 `last_recorded`

```json
{"mode": "bypass"}
```

- 바꾸기: `record.py mode bypass`
- normal: 추가·병합·삭제마다 질문
- bypass: 조건이 맞으면 바로 추가·병합, 작업 보고 끝에 한 줄 `경력 추가: {폴더} "{첫 줄}" (등급)` 또는 `경력 병합: ...`
- bypass에서도 질문: 상·중 줄 삭제, 묶음 있는 줄 삭제, 위치 후보 여럿

## PR 머지 뒤

세션 안 `gh pr merge`(또는 `gh api`의 PUT `pulls/N/merge`) 성공 뒤 Developer Thinking 훅이 안내 출력. 직접 요청("이거 경력에 추가해 줘")도 같은 순서

1. 기계 제외: `gh pr view {번호} --json author,title,files,url > {임시}.json` → `record.py screen {임시}.json --user $(gh api user --jq .login)`. `skip`이면 묻지 않고 끝
2. 기록 조건 셋 모두: 사용자 계정 PR, 동작·결과 변화(기능 추가, 성능 개선, 장애·버그 해결, 구조 변경, 운영 자동화), 검증(테스트, 측정, 운영 관찰). 제외: 문서·오타, 포맷, 의존성 버전만, 동작 변화 없는 이름 변경
3. 위치: `locate --remote $(git remote get-url origin) --author {작성자}` → 저장소 속성 일치 1개면 그 폴더, 여럿이면 질문, 0개면 최근 수정 프로젝트 3개 + `새 프로젝트(소속 선택)`. 개인 계정 저장소는 `개인/` 기본
4. 같은 줄 판정([원본 형식](references/format.md) 같은 줄 판정): 같으면 `merge`, 아니면 `add --similar`(가장 가까운 줄 있을 때)
5. 10줄 가득: 병합 후보 먼저 → 없으면 `add`가 가장 낮은 줄과 비교(모드 규칙)
6. 끝: `stamp`

normal 질문 예:

```text
경력에 추가할까요? → 예시페이/정산팀/정산-이벤트-전환
"실패한 정산 건만 다시 처리하는 도구 구현 (6시간 → 2분)" (등급 중)
비슷한 줄: "정산 배치를 주문 이벤트 처리로 전환" → 병합 / 새 줄 / 건너뛰기
```

놓친 머지 정리("최근 머지된 PR 경력 정리"): `since` 시각 이후 `gh search prs --author @me --merged-at ">={시각}" --json url,repository` → PR마다 위 1~5 → `stamp`. 시각이 없으면 범위 질문

## 초안과 빈칸

- 원본 없음: 기존 이력서·저장소·PR로 이 형식 초안 작성 → 사용자 확인 뒤에만 저장
- 빈칸: `blanks` 출력 그대로 질문(`채워 주세요 (N개)` + 번호 목록 `{폴더} {첫 줄} - {칸}: {쉬운 질문}`)
- 답한 칸만 `fill`, 등급 자동 재계산. 답 없는 칸은 `미확인` 유지
- 옛 형식(master.md 프로젝트 절, `cases/`): 프로젝트 폴더로 옮긴 초안 → 사용자 확인 뒤 이동

## 완료 보고

developer-thinking 작업 보고 틀. 포함: 바뀐 프로젝트 폴더, 추가·병합·삭제 줄과 등급, `check` 결과, 남은 빈칸 수
