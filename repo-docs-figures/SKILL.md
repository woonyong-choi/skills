---
name: repo-docs-figures
description: "문서 그림(구조도, 순서도, 상태도, 데이터 관계도, 차트, 데모 GIF)을 만들거나 고칠 때 사용. D2, Vega-Lite, VHS 템플릿, 색표, 대체 글, render_figures 변환"
---

# Repo Docs Figures

- 저장소 안에 같은 역할의 규칙이 있으면 그것 우선. 없으면 이 스킬이 다른 규칙보다 우선
- 기반: repo-docs 먼저 적용. 이 스킬 범위: 그림 원본 형식과 변환. 그림을 넣는 자리는 종류별 스킬 담당

- 원본과 만든 그림 함께 커밋. 만든 그림의 손 수정 금지
- 변환: 이 스킬의 `render_figures` 스크립트로만. 저장소에 별도 변환 스크립트 금지

## 도구

| 그림 | 도구 | 원본 | 결과 | 설치 |
|---|---|---|---|---|
| 구조도, 순서도, 상태도, 데이터 관계도 | D2 | `{이름}.d2` | `{이름}.svg` | `brew install d2` |
| 실험 차트 | Vega-Lite v5와 vl-convert | `{이름}.vl.json` | `{이름}.svg` | `pip install vl-convert-python` |
| 터미널 데모 | VHS | `{이름}.tape` | `{이름}.gif` | `brew install vhs` |
| 글꼴 | Noto Sans CJK KR, D2Coding | 해당 없음 | 해당 없음 | `brew install --cask font-noto-sans-cjk-kr font-d2coding` |

- 위치: `docs/assets/`, 실험 차트는 `docs/experiments/{실험}/results/figures/`
- mermaid, 손으로 그린 이미지, 스크린샷 편집본 금지
- D2 손그림 모드(`--sketch`, `sketch: true`) 금지

## 색표

- D2와 Vega-Lite 공통 색. 원본에 색 직접 기재 금지, `render_figures`가 삽입
- 예외: VHS 테이프의 `Theme`, `MarginFill`은 템플릿 값 그대로

| 역할 | 색 | D2 키 | Vega-Lite |
|---|---|---|---|
| 바탕 | `#ffffff` | `N7` | `background` |
| 글자 | `#0b0b0b` | `N1` | 제목 |
| 보조 글자 | `#52514e` | `N2` | 축 글자 |
| 격자 | `#e6e5e1` | `N5` | `gridColor` |
| 핵심 1 | `#2a78d6` | `B2` | 첫 계열, 막대 |
| 핵심 1 진하게 | `#1d4f91` | `B1` | 히트맵 최댓값 |
| 핵심 1 옅게 | `#edf3fb` | `B5` | 히트맵 최솟값 |
| 핵심 2 | `#eb6834` | `AA2` | 둘째 계열, 기준선 |
| 핵심 2 옅게 | `#fbe1d5` | `AA4` | 해당 없음 |

- 계열은 둘까지. 셋 이상이면 차트 분리
- 상태 색(성공, 실패) 금지. 판정은 글자로

## 대체 글

- 그림이 보여 주는 결론 한 문장. 마침표 없음. 문체는 그 문서 파일의 문체
- 그림 이름, 종류 금지. 예: `아키텍처 그림` 대신 `사용자 요청은 서버에 저장된 뒤 작업자로 간다`
- 자리표시 그림: repo-docs 자리표시 표의 표시를 앞에 추가. 예: `설계:`, `합성 데이터:`, `예시 데이터:`

## D2

- 라벨: 한국어. 연결 라벨은 주고받는 것 명사구
- 식별자: 영어 소문자 kebab-case, 문서 표의 `식별자` 칸과 동일. 표에 식별자가 없는 외부 요소는 이름을 소문자 kebab-case로 변환. 예: `GitHub API` → `github-api`
- 선: 문서의 구성 요소 표, 외부 요소 표, 실행 흐름에 적힌 연결만. 한 쌍에 선 하나, 방향은 요청이 가는 쪽
- 도형: 아래 표만. 다른 `style`, 색, 아이콘 금지

| 대상 | D2 |
|---|---|
| 사용자 | `shape: person` |
| 이 시스템 | 이름이 `system`인 묶음 `{ }` |
| 구성 요소, 모듈 | 기본 사각형 |
| 외부 프로그램, 외부 서비스 | `style.stroke-dash: 4` |
| 파일, 데이터베이스(구성 요소여도) | `shape: cylinder` |
| 테이블 | `shape: sql_table` |
| 메시지 순서 | `shape: sequence_diagram` |

### 맥락 그림

```text
direction: right
user: {사용자} {shape: person}
system: {이름}
{외부 id}: {외부 프로그램} {style.stroke-dash: 4}
{데이터 id}: {파일이나 데이터} {shape: cylinder}
user -> system: {주고받는 것}
system -> {외부 id}: {주고받는 것}
system -> {데이터 id}: {주고받는 것}
```

### 구성 요소 그림

```text
direction: right
user: {사용자} {shape: person}
system: {이름} {
  {id}: {구성 요소}
  {id} -> {id}: {주고받는 것}
}
{외부 id}: {외부 프로그램} {style.stroke-dash: 4}
user -> system.{id}: {주고받는 것}
system.{id} -> {외부 id}: {주고받는 것}
```

- 외부 요소: 맥락 그림과 같은 식별자와 이름
- 맥락 그림: 외부 요소 표의 행만. 이 시스템의 구성 요소인 파일과 데이터베이스는 구성 요소 그림에만

### 순서 그림

```text
shape: sequence_diagram
{id}: {참여자}
{id} -> {id}: {메시지}
```

- 참여자: 왼쪽부터 처음 메시지를 보내는 순서. 메시지는 명사구나 메서드 이름

### 상태 그림

```text
direction: down
{상태}
{상태} -> {상태}: {사건}
```

- 상태 이름: 상태 표의 `상태` 칸과 동일

### 데이터 그림

```text
direction: right
{테이블}: {
  shape: sql_table
  {열}: {타입} {constraint: primary_key}
  {열}: {타입} {constraint: foreign_key}
}
{테이블}.{열} -> {테이블}.{열}
```

- 열: `data.md` 테이블 절과 같은 이름, 같은 순서

## Vega-Lite

- `config` 금지. `render_figures`가 색표와 글꼴 삽입

| 보여 줄 것 | 차트 | 표시 |
|---|---|---|
| 조건별 비율과 신뢰구간 | `bar`와 `errorbar` | 채택 기준선은 `rule` |
| 같은 입력에서 두 방식 비교 | 덤벨(점 둘과 잇는 선) | 방식 A 핵심 1, 방식 B 핵심 2 |
| 연속값 분포 | 상자 그림 | 조건마다 상자 하나 |
| 두 변수의 관계 | 산점도 | 점 크기 고정 |
| 판정 교차표 | 히트맵 | 칸 안에 개수 |
| 순서나 시간에 따른 변화 | 선 | 점 표시 |

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "title": {"text": "{무엇을 쟀는지}", "subtitle": "n={n}. {기준선 설명}"},
  "width": 420,
  "height": 220,
  "data": {"values": []},
  "mark": "bar",
  "encoding": {}
}
```

- 값: `results/summary.json`에서 `03-analyze`가 삽입. 손 기재 금지
- 제목은 명사구. 부제는 표본 수와 기준선 설명. 예시 데이터 차트의 부제는 `예시 데이터.`로 시작
- 축 제목에 단위: `오분류율(%)`, `지연(ms)`
- 막대 축은 0에서 시작. y축 둘 금지
- 신뢰구간은 `errorbar`, 기준선은 `rule`만. 두 마크의 색과 점선은 `render_figures`가 결정
- 계열 색: `color` 인코딩으로만 구분. 첫 값이 핵심 1, 둘째 값이 핵심 2
- 비율에는 신뢰구간 함께 표시(repo-docs-experiment 통계 규칙)

## VHS

```text
Output docs/assets/{이름}.gif
Set Shell "bash"
Set FontFamily "D2Coding"
Set FontSize 18
Set Width 1200
Set Height 600
Set Theme "Catppuccin Mocha"
Set Padding 24
Set Margin 30
Set MarginFill "#2a78d6"
Set BorderRadius 12
Set WindowBar Colorful
Set TypingSpeed 60ms
Hide
Type "export PS1='$ ' && {준비 명령} && clear"
Enter
Show
Type "{명령}"
Enter
Sleep {초}s
```

- 20초 이내, 3MB 이하
- 준비 명령(빌드, 합성 데이터 준비): `Hide`와 `Show` 사이
- 사용자 이름, 홈 경로, 키, 실제 사용자 데이터의 화면 노출 금지
- 합성 데이터를 쓰면 화면에 `합성 데이터` 글자 표시, 대체 글 앞에 `합성 데이터:` 추가
- 실행 위치: 저장소 루트. `Output`은 저장소 루트 기준 경로

## 변환

- 저장소 루트에서 아래 명령 실행. 인자가 없으면 git이 추적하는 모든 원본 변환

```sh
python3 <이 스킬 폴더>/scripts/render_figures.py docs/assets/architecture.d2
```

- `<이 스킬 폴더>`: 이 SKILL.md가 있는 폴더. 스크립트 본문은 읽지 않고 실행만. Windows에서 `python3`가 없으면 `py -3`
- 색표와 Vega-Lite 설정 값: 스크립트 안. 이 스킬의 색표 절과 같은 값

- 실패하면 원본 수정 뒤 재실행. 만든 그림 수정 금지
- D2 SVG에는 라틴 글꼴만 포함. 한글은 보는 쪽 시스템 글꼴로 표시
- 변환 뒤 그림을 열어 글자 겹침, 잘림, 빈 영역 눈으로 확인

## 검사

1. 원본마다 같은 이름의 결과 파일
2. `render_figures` 재실행 뒤 `git diff`에 VHS 결과 밖의 변경 없음
3. 문서의 모든 그림에 결론 문장 대체 글
4. `.d2`, `.vl.json` 원본에 색, `config`, `sketch` 없음
5. README 그림: 대표 그림, 측정 결과 차트, 구성 그림 하나씩까지(repo-docs-readme)
