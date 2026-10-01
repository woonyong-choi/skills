---
name: repo-docs-readme
description: "저장소 루트 README.md와 번역본 README.ko.md를 만들거나 갱신할 때 사용. 단계별 필수 절, 절 이름 목록(영어, 한국어), 소개와 작동 방식, 상태, 비교, 로드맵, 번역 규칙"
---

# Repo Docs Readme

- 저장소 안에 같은 역할의 규칙이 있으면 그것 우선. 없으면 이 스킬이 다른 규칙보다 우선
- 기반: repo-docs 먼저 적용. 이 스킬 범위: 루트 `README.md`와 `README.ko.md`의 절 구성과 절 규칙
- 필요할 때만 읽기: 대표 그림, 흐름 그림, 측정 결과 차트, 데모 GIF 제작 → repo-docs-figures; README 갱신 뒤 `llms.txt` 재생성 → repo-docs-llms

- 독자: 처음 온 사람. 답할 질문: 무엇인가, 왜 필요한가, 어떻게 쓰이나, 지금 쓸 수 있나, 어디서 더 보나
- 원본 `README.md`는 영어, 번역본 `README.ko.md`는 한국어 합쇼체(repo-docs 언어)
- 길이: 파일마다 200줄 이내. 세부는 `docs/` 링크
- 그림: 대표 그림 하나, 그 밖 절마다 하나까지

## 입력

작성 전 읽을 입력. 없는 파일은 생략

| 입력 | 쓰는 곳 |
|---|---|
| GitHub 저장소 설명 `gh repo view --json description` | 한 줄 소개 |
| `docs/design/` 문서의 요약과 예시 절 | 소개 문단, 작동 방식 |
| `docs/architecture.md` 코드 지도와 그림 | 대표 그림, 구성 |
| 결정 기록과 `design` 이슈 | 비교, 상태 |
| GitHub 마일스톤 `gh api repos/{소유자}/{저장소}/milestones`와 열린 이슈 | 로드맵 |
| `docs/experiments/README.md`와 채택 판정 보고서 | 측정 결과 |
| GitHub 릴리스 목록 `gh release list` | 단계 |
| 사용법 명령을 실제로 실행한 출력 | 사용법 |
| `docs/README.md` 표 | 문서 |
| CI 설정과 저장소 검사 스크립트 | 개발 |
| `LICENSE`, `.github/CONTRIBUTING.md` | 라이선스, 개발 |

## 단계

선택: 위에서부터 처음 맞는 단계 하나

| 단계 | 조건 |
|---|---|
| 배포 | GitHub 릴리스나 패키지 저장소 배포가 하나 이상 |
| 실행 가능 | `main` 빌드로 사용법의 명령이 실제로 동작 |
| 개발 중 | 구현 상태 기능이 하나 이상 |
| 설계 | 그 밖 |

## 절 이름 목록

머리 뒤에 이 순서로 배치. 필수 표시가 없는 절은 조건이 맞을 때만

| 순서 | 영어 | 한국어 | 설계 | 개발 중 | 실행 가능 | 배포 | 조건 |
|---|---|---|---|---|---|---|---|
| 1 | `How it works` | `작동 방식` | 필수 | 필수 | 선택 | 선택 | 없음 |
| 2 | `Installation` | `설치` | 없음 | 없음 | 필수 | 필수 | 없음 |
| 3 | `Usage` | `사용법` | 없음 | 없음 | 필수 | 필수 | 없음 |
| 4 | `Features` | `기능` | 없음 | 선택 | 선택 | 필수 | 구현 상태 기능이 하나 이상 |
| 5 | `Benchmarks` | `측정 결과` | 선택 | 선택 | 선택 | 선택 | 판정이 채택인 실험 보고서 존재 |
| 6 | `Status` | `상태` | 필수 | 필수 | 필수 | 없음 | 없음 |
| 7 | `Comparison` | `비교` | 선택 | 선택 | 선택 | 선택 | 사용자가 대신 쓸 만한 도구가 있을 때 |
| 8 | `Roadmap` | `로드맵` | 필수 | 필수 | 선택 | 선택 | 결정이나 미정 상태 기능이 하나 이상 |
| 9 | `Documentation` | `문서` | 선택 | 선택 | 선택 | 선택 | `docs/README.md` 존재 |
| 10 | `Development` | `개발` | 없음 | 필수 | 필수 | 필수 | 없음 |
| 11 | `License` | `라이선스` | 선택 | 선택 | 선택 | 선택 | `LICENSE` 존재 |

- 목록에 없는 절: repo-docs 절 구성 3. 번역본에도 같은 자리에 같은 절

## 머리

파일 처음부터 첫 `##` 전까지. 가운데 정렬 블록 하나와 그 뒤 본문

가운데 정렬 블록: `<p align="center">`와 `<h1 align="center">`로, 이 순서

1. 로고: 로고 파일이 있을 때만. `<picture>`로 다크 모드용 `docs/assets/logo-dark.png`와 기본 `docs/assets/logo-light.png`, 폭 `width="160"`, 대체 글 `{제품 이름} logo`
2. 제목: `<h1 align="center">{제품 이름}</h1>`. 제품 표기 그대로(저장소 이름이 소문자여도 `Saturn`). 문서의 제목은 이것 하나
3. 한 줄 소개: 한 문장, 영어 120자 이내. 무엇인지와 범주 하나. GitHub 저장소 설명과 같은 글자(마침표 제외)
4. 언어 전환 줄(repo-docs 언어). HTML 블록 안이라 `<a href="README.ko.md">한국어</a>` 형식
5. 절 이동 링크: 언어 전환 줄 다음 줄(`<br>`로 구분). 이 README의 `##` 절 중 3~5개를 `<a href="#{앵커}">{절 이름}</a>`로, ` · `로 연결. HTML 블록 안이라 Markdown 링크 대신 `<a>`

본문: 가운데 정렬 블록 뒤, 이 순서

1. 소개 문단: 한 문단, 세 문장. 1 문제(누가 무엇을 할 때 무엇이 어려운가), 2 해결(제품이 무엇을 어떻게 하나), 3 차이(비교 대상과 무엇이 다른가). 비교 대상이 없으면 3 삭제
2. 단계 알림: `> [!NOTE]`와 단계별 고정 문장. 배포 단계 제외
3. 대표 그림

| 단계 | 영어 알림 | 한국어 알림 |
|---|---|---|
| 설계 | `Design stage. There is no runnable code yet.` | `설계 단계입니다. 실행할 수 있는 코드는 아직 없습니다.` |
| 개발 중 | `In development. There is no runnable command yet.` | `개발 중입니다. 실행할 수 있는 명령은 아직 없습니다.` |
| 실행 가능 | `In development. There are no releases; build from source.` | `개발 중입니다. 배포판은 없고 소스에서 빌드해 실행합니다.` |

| 단계 | 대표 그림 | 대체 글 |
|---|---|---|
| 설계, 개발 중 | 제품이 하는 일을 보여 주는 흐름 그림(순서 그림), 없으면 `docs/assets/architecture.svg` | `Design: {그림이 보여 주는 결론}`, 한국어 `설계: {결론}` |
| 실행 가능, 배포 | 데모 GIF `docs/assets/demo.gif` | `{데모가 보여 주는 결론}` |

- 소개 문단: 현재 범위만. 장기 목표와 확장 계획은 로드맵
- 한 줄 소개와 소개 문단의 용어: 업계 원어(repo-docs 용어). 프로젝트 고유 용어는 소개에 쓰지 않음, 쓰면 같은 문장에서 풀이
- 데모에 결정이나 미정 상태 기능이 보이면 합성 데이터로 녹화(repo-docs 자리표시)

## 절 규칙

### 작동 방식

- 사용 장면 하나를 번호 목록 3~7단계로. 단계마다 한 문장, 사용자가 보는 것과 제품이 하는 일
- 설계, 개발 중 단계: 첫 문장 `The following is the designed behavior.`, 한국어 `아래는 설계한 동작입니다.`
- 마지막에 자세한 설계 문서 링크 한 문장

### 설치

- 필요한 도구 문장, 설치 명령 블록. 실제로 실행해 확인한 명령만
- 실행 가능 단계: 소스 설치 명령 하나. Rust는 `cargo install --git https://github.com/{소유자}/{저장소} --locked`
- 배포 단계: 배포된 경로의 설치 명령만, 한 줄에 하나. 순서는 `cargo install`, `brew install`, 그 밖

### 사용법

- 사용 예 1~5개, `###` 제목은 동작 명사구. 첫 예는 처음 실행하는 명령
- 명령 블록 하나, 출력 블록 하나. 출력은 실제 실행 결과 복사, 20줄 초과면 앞 20줄과 `...` 한 줄
- 화면이 뜨는 명령: 출력 블록 제외
- `docs/cli.md`가 있으면 마지막에 링크 한 문장

### 기능

- 구현 상태 기능만. `- {기능}: {하는 일}` 한 줄씩
- 기능 이름: 설계 문서 제목과 같은 글자

### 측정 결과

- README의 수치: 이 절에만
- 결과 문장 1~3개. 한 문장에 수치 하나와 보고서 링크. 수치는 보고서의 `results/summary.json` 값 그대로
- 차트: 채택 판정 보고서의 `results/figures/` 그림 하나. 예시 데이터 차트 금지

### 상태

- 한 문단, 두세 문장: 지금 있는 것, 아직 없는 것, 호환 약속
- 호환 약속 예: `Formats and commands may change without notice before 1.0.`
- 설계 단계: 있는 것은 공개 설계 문서와 결정 기록뿐이라고 명시

### 비교

- 사용자가 대신 쓸 만한 도구 1~4개. 항목마다 한두 문장: 무엇이 다른가, 그 도구가 더 나은 경우
- 외부 도구의 기능 주장: 확인한 날짜(repo-docs 사실 상태)
- 비교 대상을 깎아내리는 표현 금지

### 로드맵

- 단계(마일스톤) 순서 번호 목록. 항목: `{단계 이름}: {그 단계에 들어가는 기능, 쉼표로 연결}. ({상태})`
- 상태 글자: 영어 `in progress`, `next`, `later`, 한국어 `진행 중`, `다음`, `나중`
- GitHub 마일스톤이 있으면 단계 이름은 마일스톤 이름, 항목 끝에 마일스톤 링크
- 구현되면 로드맵에서 삭제, 기능 절에 추가
- 설계 문서의 기능 목록 복사 금지. 독자가 순서와 진행을 알 수 있게 묶기

### 문서

- `docs/README.md` 표의 행 중 독자가 먼저 볼 것 3~6개, 같은 순서, 끝에 `docs/README.md` 링크. 형식 `- [{문서 제목}]({경로}): {답하는 것}`
- 문서 제목: 작업 언어가 README 언어와 같으면 같은 글자, 다르면 README 언어로 번역
- 작업 언어가 영어가 아니면 절 첫 문장에 표시: `The design documents are written in Korean.`
- `.local` 링크 금지

### 개발

- 명령: CI나 저장소 검사 스크립트에 실제로 있는 것만, 빌드, 테스트, 린트, 포맷 검사 순서
- 기여 문장: `.github/CONTRIBUTING.md`가 있을 때만

### 라이선스

- `[{SPDX 식별자}](LICENSE)` 한 문장. 두 라이선스면 `{A} 또는 {B}`

## 표본

설계 단계 영어 원본의 절 구성. 글자 복사 대상 아님(repo-docs 절 구성 7)

````text
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/logo-dark.png">
    <img src="docs/assets/logo-light.png" alt="Tally logo" width="160">
  </picture>
</p>

<h1 align="center">Tally</h1>

<p align="center">
  A terminal tool that collects to-dos from many repositories into one list.
</p>

<p align="center">
  English | <a href="README.ko.md">한국어</a><br>
  <a href="#how-it-works">How it works</a> · <a href="#status">Status</a> · <a href="#roadmap">Roadmap</a> · <a href="#documentation">Documentation</a>
</p>

Developers who maintain several repositories lose track of issues spread across them. Tally pulls open issues from every repository into one local list and keeps it in sync. Unlike the per-repository issue pages, it shows everything in one place without switching tabs.

> [!NOTE]
> Design stage. There is no runnable code yet.

![Design: Tally fetches issues from GitHub and stores them in a local database](docs/assets/architecture.svg)

## How it works

The following is the designed behavior.

1. You run `tally add` in each repository you want to track.
2. Tally fetches open issues and stores them in a local database.
3. You run `tally` to see one list sorted by last update.

The full design is in [Sync](docs/design/sync.md).

## Status

The design documents and decision records are public. There is no code yet. Formats and commands may change without notice before 1.0.

## Roadmap

1. Local list: add repositories, fetch issues, show one list. (in progress)
2. Sync: refresh on a schedule, mark closed issues. (next)

## Documentation

The design documents are written in Korean.

- [Architecture](docs/architecture.md): code map and invariants
- [All documents](docs/README.md)
````

## 번역

- `README.ko.md`: `README.md`와 절, 순서, 목록 항목 수, 그림, 링크 일대일(repo-docs 언어)
- 문장: 뜻 유지, 자연스러운 한국어 합쇼체. 낱말 단위 직역 금지
- 절 제목: 절 이름 목록의 한국어 글자. 단계 알림: 고정 한국어 문장
- 가운데 정렬 블록: 한 줄 소개를 한국어로 번역, 절 이동 링크의 글자와 앵커는 한국어 절 제목 기준
- 대체 글: 한국어로 번역, 표시 `설계:`, `합성 데이터:`
- 원본과 번역본은 같은 PR에서 수정

## 갱신

- 아래 사건이 생기면 입력을 다시 읽고 두 파일 함께 수정. 수정 뒤 `llms.txt` 재생성(repo-docs-llms)

사건:

- 단계 변경
- 기능의 첫 구현, 결정, 폐기
- 마일스톤 변경
- 실험 보고서 판정의 채택 머지
- 구성 요소, 설치 명령, 사용 명령, 문서 목록 변경
