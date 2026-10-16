---
name: repo-docs-readme
description: "저장소 루트 README.md와 영어판 README.en.md를 작성·갱신할 때 사용."
---

# Repo Docs Readme

- 우선순위: 사용자 지시 → 저장소 규칙 → 이 스킬. 범위 밖은 명시한 소유 스킬 적용
- 기반: repo-docs 먼저 적용. 이 스킬 범위: 루트 `README.md`와 `README.en.md`의 종류, 절 구성과 절 규칙, 이미지
- 필요할 때만 읽기: 흐름·구조 그림, 데모 GIF 제작 → repo-docs-figures; README 갱신 뒤 `llms.txt` 재생성 → repo-docs-llms; 포트폴리오형 원본 → career-record `references/format.md`

- 독자·답할 질문: repo-docs 문서 목록. 언어: repo-docs 언어. 영어판: 아래 영어판 절
- 길이: 필수 정보와 핵심 사용 흐름 보존, 독립적으로 조회하는 세부는 `docs/` 링크
- 그림: 절의 질문에 답하는 그림만 배치, 같은 정보를 되풀이하는 그림 제외

## 종류

- 오픈소스형: 남이 설치해 쓰는 저장소
- 포트폴리오형: 내가 한 일을 보여 주는 저장소. 절 순서는 경력 원본 `포트폴리오.md` 묶음 절 순서(해결한 문제 → 설계 결정 → 구현 → 결과)와 일치, 원본 절을 그대로 이동
- 틀: [template.md](references/template.md)에서 종류 하나 선택. 절 이름·순서 그대로, 아래 조건이 없는 절은 생략

## 입력

작성 전 읽을 입력. 없는 파일은 생략. GitHub 명령은 GitHub 저장소에만, 다른 환경은 대응 근거 사용

입력 → 쓰는 곳:

- GitHub 저장소 설명 `gh repo view --json description` → 한 줄 소개
- `docs/design/` 요약과 예시 절, `docs/architecture.md` → 작동 방식·구현
- 결정 기록과 `design` 이슈 → 해결하는 문제·설계 결정
- 열린 상위 이슈 → 상태의 다음 할 것
- 판정과 한계를 확인한 실험 보고서 → 상태의 측정 결과·결과
- GitHub 릴리스 목록 `gh release list` → 단계
- 실제로 실행한 명령과 출력 → 빠른 시작·실행
- `docs/README.md` 목록 → 문서
- CI 설정과 저장소 검사 스크립트 → 개발
- `LICENSE`, `.github/CONTRIBUTING.md` → 라이선스, 개발

## 단계

선택: 위에서부터 처음 맞는 단계 하나

단계 → 조건:

- 배포 → GitHub 릴리스나 패키지 저장소 배포가 하나 이상
- 실행 가능 → 저장소에서 확인한 기본 브랜치 빌드로 빠른 시작의 명령이 실제로 동작
- 개발 중 → 구현 상태 기능이 하나 이상
- 설계 → 그 밖

## 오픈소스형 절 규칙

- 머리: 로고는 파일이 있을 때만. 한 줄 소개는 저장소 설명과 같은 글자(마침표 제외). 뱃지는 license·CI·배포 버전 중 있는 것. 언어 전환 줄은 영어판이 있을 때만(영어판 절). 절 이동 링크는 처음 찾을 절만
- 데모 GIF: 실행되는 제품이 있을 때만, 머리 바로 아래
- 단계 알림: `> [!NOTE]`와 아래 고정 문장. 배포 단계면 생략
- 빠른 시작: 실행 가능·배포 단계만. 실제로 실행해 확인한 설치·첫 실행 명령만
- 해결하는 문제: 프로젝트 고유 용어는 같은 문장에서 풀이. 대신 쓸 도구는 깎아내리지 않고 더 나은 경우만
- 작동 방식: 입력부터 결과까지 번호 목록, 흐름 그림 한 장, 설계 문서 링크. 설계·개발 중 단계는 첫 문장 `아래는 설계한 동작입니다.`(영어판 `The following is the designed behavior.`)
- 상태: 있는 것 / 아직 없는 것 / 다음 할 것(상위 이슈 링크) / 측정 결과(있을 때). 측정 수치는 보고서 `results/summary.json` 값 그대로와 조건, 유리한 판정만 선택 금지. 호환 약속 한 문장(예: `1.0 전에는 형식과 명령이 예고 없이 바뀔 수 있습니다.`). 설계 단계는 있는 것이 공개 설계 문서와 결정 기록뿐이라고 명시
- 문서: `docs/README.md`가 있을 때만. 그 목록의 시작 분류 문서 줄을 같은 제목·같은 설명 그대로, 끝에 전체 문서 목록 링크. 작업 언어가 한국어이면 영어판 문서 절 첫 문장 `The design documents are written in Korean.`(README.md에는 없음)
- 개발: CI·검사 스크립트에 있는 명령만, 빌드 → 테스트 → 린트 → 포맷. `.github/CONTRIBUTING.md`가 있으면 링크
- 라이선스: `[{SPDX 식별자}](LICENSE)` 한 줄. 두 라이선스면 `{A} 또는 {B}`

단계 → 알림 → 영어판 알림:

- 설계 → `설계 단계입니다. 실행할 수 있는 코드는 아직 없습니다.` → `Design stage. There is no runnable code yet.`
- 개발 중 → `개발 중입니다. 실행할 수 있는 명령은 아직 없습니다.` → `In development. There is no runnable command yet.`
- 실행 가능 → `개발 중입니다. 배포판은 없고 소스에서 빌드해 실행합니다.` → `In development. There are no releases; build from source.`

## 포트폴리오형 절 규칙

- 머리: 한 줄 소개는 무엇을 하는 시스템인지와 규모 숫자 하나. 뱃지는 실제로 쓴 핵심 기술 4~6개, 이름과 버전
- 결과: 측정하지 않은 값 기재 금지
- 실행: 실제로 돌아가는 명령. 비공개 의존이 있으면 이유 한 문장
- 기간·역할·인원 요약 표 금지

## 이미지·아이콘

두 종류 공통. 형식·위치·크기·용량은 규격: repo-docs-figures 규격 절. 종류 → 넣는 자리:

- 로고 → 로고 파일이 있을 때 머리. `<picture>`로 테마별
- 데모 GIF → 실행되는 화면이 있을 때 머리 바로 아래
- 스크린샷 → GIF가 필요 없는 정지 화면. 라이트·다크 `<picture>`(repo-docs-figures 스크린샷)
- 흐름·구조 그림 → 작동 방식·구현 절에 한 장

- 대체 글: repo-docs-figures 대체 글 절. 모형·합성 화면이면 대체 글과 캡션에 `모형`(repo-docs 자리표시)
- 아이콘: shields.io 뱃지의 공식 로고(`logo=` 값)에만. 절 제목·목록·본문에 아이콘·이모지 금지

## 영어판

- `README.en.md`: `README.md`와 절 순서·내용·이미지·뱃지 동일. 절 이름은 아래 영어 대응
- 언어 전환 줄: `README.md`는 `한국어 | [English](README.en.md)`, `README.en.md`는 `[한국어](README.md) | English`. 가운데 정렬 블록 안이라 `<a href>` 형식
- `README.md`를 바꾸는 PR에서 `README.en.md`도 수정. 한쪽만 바뀐 PR 금지
- 문체: `README.md` 합쇼체, `README.en.md` 평이한 영어 현재형
- 대조: 주체·동작·조건·부정·수치 보존. 대체 글과 절 이동 링크 글자·앵커는 각 언어 기준
- 절 이름 대응: 빠른 시작 → Quick start, 해결하는 문제 → Why, 작동 방식 → How it works, 상태 → Status, 문서 → Documentation, 개발 → Development, 라이선스 → License, 문제와 제약 → Problem and constraints, 설계 결정 → Design decisions, 구현 → Implementation, 결과 → Results, 실행 → Running

## 갱신

아래 사건이 생기면 입력을 다시 읽고 `README.md`와 영어판 함께 수정. 뒤이은 `llms.txt`: repo-docs-llms 갱신

- 단계 변경
- 기능의 첫 구현, 결정, 폐기
- 상위 이슈 변경
- 사용자 판단에 필요한 실험 보고서·판정·한계 변경
- 구성 요소, 설치 명령, 사용 명령, 문서 목록 변경
