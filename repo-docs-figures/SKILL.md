---
name: repo-docs-figures
description: "문서 그림·차트·데모 GIF를 만들거나 고칠 때 사용. mutoscope, SVG 변환·검사, 대체 글, VHS"
---

# Repo Docs Figures

- 저장소 안에 같은 역할의 규칙이 있으면 그것 우선. 없으면 이 스킬이 다른 규칙보다 우선
- 기반: repo-docs 먼저 적용. 이 스킬 범위: 그림 원본 형식, 변환, 검사, 대체 글. 그림을 넣는 자리는 종류별 스킬 담당

- 원본·입력 JSON·만든 그림 함께 커밋. 만든 그림의 손 수정 금지
- 문서 기본: 움직이는 SVG. 움직임이 필요 없는 그림: `--static`으로 정지 SVG

## 도구와 파일

| 그림 | 도구 | 원본 | 산출물 |
|---|---|---|---|
| 구조도, 순서도, 상태도, 데이터 관계도, 차트 | mutoscope | `docs/assets/{이름}.muto` | `docs/assets/{이름}.svg` |
| 터미널 데모 | VHS | `docs/assets/{이름}.tape` | `docs/assets/{이름}.gif` |

- `.muto` 하나에 그림 하나. 이름: 영어 소문자 kebab-case
- 실험 차트도 같은 위치. 입력은 `03-analyze`가 만든 `docs/experiments/{실험}/results/summary.json` 또는 그 파일에서 생성한 차트용 JSON. 원자료·추출 경로·생성 명령 보존
- 그림 문법 정본: [figure-syntax](https://github.com/woonyong-choi/mutoscope/blob/main/docs/design/figure-syntax.md)의 문법 표와 호환 규칙. 문법·기본값 복제 금지
- 색·글꼴·크기: mutoscope 토큰에서 결정. 색 역할·대비 정본: [docs-integration](https://github.com/woonyong-choi/mutoscope/blob/main/docs/design/docs-integration.md). 스킬·원본·변환 스크립트에 값 복사 금지
- 문서에 SVG만 포함. HTML 재생기는 검증용. Markdown 표는 기존 문서 규칙 유지

## 설치와 실행

- Node.js 20 이상. 공개 저장소 소스 설치만 확인(2026-10-03). 패키지는 private `0.0.0`, 공개 npm 릴리스로 간주 금지
- 아래 `mutoscope`는 설치 폴더 이름. 실행 시 `<mutoscope 경로>`를 clone한 절대 경로로 교체

```sh
git clone https://github.com/woonyong-choi/mutoscope.git
cd mutoscope
npm ci
node src/cli.js --help
```

```sh
node <mutoscope 경로>/src/cli.js check docs/assets/architecture.muto --strict
node <mutoscope 경로>/src/cli.js render docs/assets/architecture.muto --strict
node <mutoscope 경로>/src/cli.js render docs/assets/architecture.muto --strict --static
```

- `--help`: 사용법 출력과 종료 코드 2가 현재 동작(2026-10-03 확인)
- 같은 원본·같은 도구 커밋으로 재현. 확인한 커밋과 Node 버전 기록
- 두 render 명령은 같은 SVG 경로 사용. 문서 목적에 맞는 한 가지 선택, 비교 검증만 `--out`으로 폴더 분리

## 그림 작성

| 보여 줄 것 | 첫 문장·선언 | 정본 |
|---|---|---|
| 맥락, 구성 요소와 요청 흐름 | `flow right` 또는 `flow down`, `person`, `box`, `external`, `store`, `group` | figure-syntax |
| 메시지 순서 | `sequence`, 참여자 선언 뒤 `step` 안 메시지 | [figure-kinds](https://github.com/woonyong-choi/mutoscope/blob/main/docs/design/figure-kinds.md) |
| 상태와 전이 | `state down`, `state`, `start`, `final` | figure-kinds |
| 테이블과 외래 키 | `data right`, `table`, 열의 `fk=` | figure-kinds |
| 비트 필드, 배열, 스택, 행렬 | `flow`, `grid`, `item`, `gap` | [grid](https://github.com/woonyong-choi/mutoscope/blob/main/docs/design/grid.md) |
| 조건별 값, 두 방식 비교, 분포, 관계, 변화, 교차표 | `chart bar`, `dumbbell`, `box`, `scatter`, `line`, `heatmap` | [charts](https://github.com/woonyong-choi/mutoscope/blob/main/docs/design/charts.md) |

- 라벨·상태·테이블·열: 문서 표와 같은 이름과 순서. 연결: 문서에 근거가 있는 관계만
- 맥락 그림: 외부 요소 표의 요소와 시스템. 구성 요소 그림: 구성 요소 표의 행마다 도형 하나
- `title`: 그림 주제. `subtitle`: 보충 설명. `step`: 읽을 순서와 설명, 이동·강조·계열 드러내기는 해당 그림 종류 문법
- 배치·글꼴 내장: [layout](https://github.com/woonyong-choi/mutoscope/blob/main/docs/design/layout.md). 움직임·정지 출력 의미: [playback](https://github.com/woonyong-choi/mutoscope/blob/main/docs/design/playback.md)
- 정지 SVG: 모든 선과 차트 계열 표시, 빈 카드. 특정 단계 캡처로 간주 금지

## 실험 차트

- 값 손 기재 금지. `data "../experiments/{실험}/results/summary.json" at "/배열"`로 원본 기준 상대 경로와 JSON Pointer 지정(charts 값 출처)
- JSON 배열 형식이 다르면 `03-analyze`에서 차트용 JSON 생성. 수치 재입력 금지
- 계열 키: `series`의 `key=` 또는 계열 이름. 신뢰구간: 같은 키의 `.low`, `.high`. 행 키·결측값·계열 수: charts 값 출처 정본
- `data`와 인라인 `row`·`point`·`cell` 혼용 금지. 예시 데이터만 자리표시 규칙에 따른 인라인 값 허용(repo-docs 자리표시)
- `title`: 측정 대상 명사구. `subtitle`: 표본 수와 기준선 설명. 값 축 제목: 괄호 안 단위
- 통계·신뢰구간 필요 여부: 실험 설계와 통계 규칙(repo-docs-experiment 통계 규칙). 계열 역할·색: docs-integration 정본

## 대체 글

- 결론 한 문장, 마침표 없음. 문체는 해당 문서 기준. 그림 이름·종류만 적기 금지
- 문서 이미지의 대체 글 필수. SVG `title`로 대체 금지
- 설계·합성 데이터·예시 데이터의 표시와 파일 이름: (repo-docs 자리표시). 별도 상태 규칙 추가 금지
- `title`·`subtitle`·`step` 설명도 같은 사실 상태 유지. 예시 데이터 차트의 `subtitle`에 자리표시 표의 부제 접두사 적용
- 합성 데이터 데모: 화면 안 표시와 대체 글 모두 자리표시 표 적용

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

- 저장소 루트에서 실행. 기존 호출 경로 유지, `.muto`는 mutoscope, `.tape`는 VHS 호출

```sh
python3 <이 스킬 폴더>/scripts/render_figures.py --mutoscope <mutoscope 경로>/src/cli.js docs/assets/architecture.muto
```

- `--mutoscope` 생략 시 PATH의 `mutoscope` 실행. `--static`, `--require-data`, `--require-ci`는 mutoscope에 전달
- 원본 인자 생략 시 git 추적 원본 탐색. 공백 포함 경로 지원. 새 원본은 경로 지정 또는 git 추가 후 실행
- 옛 형식 원본 발견 시 목록 출력 후 변환 전 실패. `.muto`로 내용 이전 필요, 확장자만 변경 금지
- 모든 `.muto`의 strict 검사 뒤 렌더. 검사 실패 시 이 호출의 렌더 시작 금지. 렌더 중 I/O 실패의 전체 파일 원자성 보장 없음
- `.tape`와 그림 전용 옵션 동시 사용 금지. VHS 실행 위치와 결과 계약: VHS 절
- 실패 시 원본 수정 후 재실행. 실패 전부터 있던 SVG를 새 성공 결과로 간주 금지

## 검사

1. `mutoscope check --strict`: 출력 없음과 종료 코드 0 확인. 소스 설치에서는 설치와 실행 절의 `node` 접두사 사용
2. 실험 차트: `--require-data` 추가. 신뢰구간이 필요한 막대·덤벨·선 차트: `--require-ci`도 추가. 같은 옵션으로 render 실행
3. 원본 수와 SVG 수·문서 링크 대조. 같은 이름의 다른 원본을 한 `--out`에 쓰기 금지
4. 같은 원본·입력 JSON·도구 커밋으로 두 번 변환 후 SVG 바이트 동일 확인. VHS 제외
5. 실제 문서 삽입 환경에서 라이트·다크의 글자, 겹침, 잘림, 빈 영역과 움직임 확인. 시간차 두 장면과 정지 출력 대조, 정지 출력의 움직임 없음 확인
6. 모든 그림의 대체 글·자리표시 확인. README 그림 수: 대표 그림, 측정 결과 차트, 구성 그림 하나씩까지(repo-docs-readme)
7. 변환 도구 교체: 실제 기존 문서 호출·실험 데이터 입력으로 확인. 움직이는 출력·정지 출력·실패 시 파일 쓰기 계약 함께 검증. 오류 원본의 check와 render 실패, 새 산출물 없음과 기존 산출물 보존 확인

- `--strict`: 경고도 실패. 폐기 진단은 별도 `--no-deprecated`로 실패 처리(figure-syntax 호환 규칙). 출력이 남으면 진단 해결 후 재검사
- 기계 검사 통과를 실제 문서의 재생·가독성 확인으로 대체 금지
