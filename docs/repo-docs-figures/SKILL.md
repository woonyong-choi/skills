---
name: repo-docs-figures
description: "저장소 문서의 구조도·차트·대체 글·데모 GIF를 만들거나 고칠 때 사용."
---

# Repo Docs Figures

- 사용자 지시를 먼저 적용. 해당 주제의 사용자 지시가 없으면 작업 대상 저장소의 같은 주제 규칙 파일(예: `AGENTS.md`, `CONTRIBUTING.md`) 적용. 둘 다 없으면 이 스킬 적용. 다른 스킬과 겹치는 규칙은 머리의 연결에 적힌 스킬 중 그 규칙을 정한 스킬 적용
- 기반: repo-docs 먼저 적용. 이 스킬 범위: 그림 원본 형식, 변환, 검사, 대체 글. 그림을 넣는 자리는 종류별 스킬 담당
- 필요할 때만 읽기: README 그림 배치 → repo-docs-readme; 실험 차트의 통계·신뢰구간 → repo-docs-experiment

- 원본·입력 JSON·만든 그림 함께 커밋. 만든 그림의 손 수정 금지
- 순서·전이·시간 변화가 전달할 정보이면 움직이는 SVG, 최종 구조·값만 전달하면 `--static` 정지 SVG

## 도구와 파일

| 그림 | 도구 | 원본 | 산출물 |
|---|---|---|---|
| 구조도, 순서도, 상태도, 데이터 관계도, 차트 | daphnis | `docs/assets/{이름}.dap` | `docs/assets/{이름}.svg` |
| 문서 안에서 관리하는 그림 | daphnis md | Markdown의 `dap` 코드 블록 | 문서의 이미지 줄과 SVG(markdown 정본) |
| 터미널 데모 | VHS | `docs/assets/{이름}.tape` | `docs/assets/{이름}.gif` |

- `.dap` 하나에 그림 하나. 이름: 영어 소문자 kebab-case
- 실험 차트도 같은 위치. 입력은 `03-analyze`가 만든 `docs/experiments/{실험}/results/summary.json` 또는 그 파일에서 생성한 차트용 JSON. 원자료·추출 경로·생성 명령 보존
- 그림 문법 정본: [figure-syntax](https://github.com/woonyong-choi/daphnis/blob/main/docs/design/figure-syntax.md)의 문법 표와 호환 규칙. 문법·기본값 복제 금지
- 색·글꼴·크기: daphnis 토큰에서 결정. 색 역할·대비 정본: [docs-integration](https://github.com/woonyong-choi/daphnis/blob/main/docs/design/docs-integration.md). 스킬·원본·변환 스크립트에 값 복사 금지
- 면 위계: 판과 그룹은 무채색, 그룹 중첩 깊이별 밝기 단계로 구분. 일반 그룹 테두리 없음, 도형 외곽선 유지. 강조 그룹도 무채색 면 유지
- 색 역할: 핵심 흐름·현재 상태·차트 주 계열·구성도 아이콘은 NHN 브랜드 파랑. 보라는 드문 강조, 빨강은 오류, 초록은 정상. 주황은 차트 비교 계열과 주의 상태에만 사용. 원색과 테마별 단계는 docs-integration 정본 참조
- 글꼴: 본문·숫자 Pretendard, 차트 숫자 `tabular-nums`, 코드는 JetBrains Mono. 자간은 daphnis 토큰 참조
- 대비: 라이트·다크 모두 글자 4.5 이상, 도형 외곽선과 의미 있는 그래픽 3 이상. 꾸밈 요소만 정본에 명시한 예외 적용
- 아이콘: 재생·이동 등 조작 아이콘은 Lucide. 구성도는 Carbon 범용·Simple Icons 브랜드 아이콘, 사용자 세트는 경로 참조만 허용. NHN 아이콘 세트 복제 금지
- 문서 그림 표시: SVG. 문서 안 원본 관리 시 `dap` 블록도 보존, HTML 재생기는 검증용. Markdown 표는 기존 문서 규칙 유지

## 설치와 실행

- 실행 환경: Node.js 20 이상. 설치·배포 정본: [README](https://github.com/woonyong-choi/daphnis/blob/main/README.md#installation). 패키지 버전만으로 npm 배포 여부 판단 금지
- `<daphnis 경로>`: 의존성이 설치된 기존 작업본의 절대 경로. 아래 명령은 문서 저장소 루트에서 실행

```sh
node <daphnis 경로>/src/cli.js --help
```

```sh
node <daphnis 경로>/src/cli.js check docs/assets/architecture.dap --strict
node <daphnis 경로>/src/cli.js render docs/assets/architecture.dap --strict
node <daphnis 경로>/src/cli.js render docs/assets/architecture.dap --strict --static
```

- 실행 전 사용할 버전의 도움말에서 명령 형식과 성공·실패 시 종료 코드를 확인·기록
- 같은 원본·같은 도구 커밋으로 재현. 확인한 커밋과 Node 버전 기록
- 두 render 명령은 같은 SVG 경로 사용. 전달할 순서·전이·시간 정보 여부로 한 가지 선택, 비교 검증만 `--out`으로 폴더 분리

## Markdown과 CI

- 문서 안 그림 관리: `daphnis md`로 `dap` 코드 블록에서 SVG 생성과 이미지 줄 갱신. 블록·파일 이름·출력 위치·오래된 SVG 정리 규칙: [markdown](https://github.com/woonyong-choi/daphnis/blob/main/docs/design/markdown.md). 문법·기본값 복제 금지
- 원본 문서와 생성 SVG 함께 커밋. 생성 이미지 줄의 대체 글은 블록의 `title`에서 결정하므로 `title`도 대체 글 규칙 적용
- 읽기 전용 최신성 검사: 아래 명령. 사용 버전에서 성공·실패 코드와 파일 변경 여부 확인·기록

```sh
node <daphnis 경로>/src/cli.js md <문서 경로>.md --check --strict
node <daphnis 경로>/src/cli.js md <문서 경로>.md --check --strict --static
```

- 생성 명령과 GitHub Action 연결 예: [README 사용법](https://github.com/woonyong-choi/daphnis/blob/main/README.md#keep-figures-in-a-markdown-document). 위 검사와 생성에 같은 출력 옵션 사용
- Action 정본: [action.yml](https://github.com/woonyong-choi/daphnis/blob/main/action.yml). 추적 파일 대상으로 원본 검사와 Markdown 최신성 검사, 생성 모드는 파일 갱신만 수행하고 자동 커밋 없음. 입력 문법·기본값은 정본 참조
- Action 검증 결과에는 로컬 파일을 `action.yml`과 대조했는지, GitHub에서 실제 실행 결과를 확인했는지 각각 기록

## 그림 작성

| 보여 줄 것 | 종류·선언 | 정본 |
|---|---|---|
| 맥락, 구성 요소와 요청 흐름 | `flow right` 또는 `flow down`, `person`, `box`, `external`, `store`, `group` | figure-syntax |
| 메시지 순서 | `sequence`, 참여자 선언 뒤 `step` 안 메시지 | [figure-kinds](https://github.com/woonyong-choi/daphnis/blob/main/docs/design/figure-kinds.md) |
| 상태와 전이 | `state down`, `state`, `start`, `final` | figure-kinds |
| 테이블과 외래 키 | `data right`, `table`, 열의 `fk=` | figure-kinds |
| 비트 필드, 배열, 스택, 행렬 | `flow`, `grid`, `item`, `gap` | [grid](https://github.com/woonyong-choi/daphnis/blob/main/docs/design/grid.md) |
| 조건별 값과 신뢰구간, 행마다 다른 기준(`rule=`) | 막대 | [charts](https://github.com/woonyong-choi/daphnis/blob/main/docs/design/charts.md) |
| 같은 입력에서 두 방식의 값 비교 | 덤벨 | charts |
| 연속값 분포 | 상자 | charts |
| 두 변수의 관계 | 산점도 | charts |
| 순서·시간에 따른 변화, 작은 변화의 축 확대(`zero off`) | 선 | charts |
| 판정 교차표 | 히트맵 | charts |
| 음수일 수 있는 차이 값과 신뢰구간, 0선·음수 기준선 | 차이(`chart difference`) | charts |

- 차트 선언·값 출처·축 제약: charts 정본. 차이 값은 차이 차트, 조건별 원래 값은 막대·덤벨 선택. 막대 행 기준과 공통 기준선 구분, 선 차트 축 확대 시 잘림 표시 확인

- 라벨·상태·테이블·열: 문서 표와 같은 이름과 순서. 연결: 문서에 근거가 있는 관계만
- 맥락 그림: 외부 요소 표의 요소와 시스템. 구성 요소 그림: 구성 요소 표의 행마다 도형 하나
- `title`: 그림 주제. `subtitle`: 보충 설명. `step`: 읽을 순서와 설명, 이동·강조·계열 드러내기는 해당 그림 종류 문법
- 배치·글꼴 내장: [layout](https://github.com/woonyong-choi/daphnis/blob/main/docs/design/layout.md). 움직임·정지 출력 의미: [playback](https://github.com/woonyong-choi/daphnis/blob/main/docs/design/playback.md)
- 정지 SVG: 모든 선과 차트 계열 표시, 빈 카드. 특정 단계 캡처로 간주 금지

## 실험 차트

- 값 손 기재 금지. `data "../experiments/{실험}/results/summary.json" at "/배열"`로 원본 기준 상대 경로와 JSON Pointer 지정(charts 값 출처)
- JSON 배열 형식이 다르면 `03-analyze`에서 차트용 JSON 생성. 수치 재입력 금지
- 계열 키: `series`의 `key=` 또는 계열 이름. 신뢰구간: 같은 키의 `.low`, `.high`. 행 키·결측값·계열 수: charts 값 출처 정본
- `data`와 인라인 `row`·`point`·`cell` 혼용 금지. 예시 데이터만 자리표시 규칙에 따른 인라인 값 허용(repo-docs 자리표시)
- `title`: 측정 대상 명사구. 문서 안 블록은 대체 글 규칙 적용. `subtitle`: 표본 수와 기준선 설명. 값 축 제목: 괄호 안 단위
- 통계·신뢰구간 필요 여부: 실험 설계와 통계 규칙(repo-docs-experiment 통계 규칙). 계열 역할·색: docs-integration 정본

## 대체 글

- 결론 한 문장, 마침표 없음. 문체는 해당 문서 기준. 그림 이름·종류만 적기 금지
- 문서 이미지의 대체 글 필수. SVG `title`만으로 대체 금지. 문서 안 블록은 생성 이미지 줄의 대체 글까지 확인
- 설계·합성 데이터·예시 데이터의 표시와 파일 이름: (repo-docs 자리표시). 별도 상태 규칙 추가 금지
- `title`·`subtitle`·`step` 설명도 같은 사실 상태 유지. 예시 데이터 차트의 `subtitle`에 자리표시 표의 부제 접두사 적용

## VHS

아래 값은 실행 형식을 보여 주는 예시이며 그대로 사용할 의무 없음. 글꼴·색·크기는 저장소 디자인 기준으로 결정. 길이·용량은 게시 환경 제한을 확인해 결정. 재생 속도는 실제로 재생하며 글을 다 읽을 수 있는지 확인해 결정

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

- 준비 명령(빌드, 합성 데이터 준비): `Hide`와 `Show` 사이
- 사용자 이름, 홈 경로, 키, 실제 사용자 데이터의 화면 노출 금지
- VHS 화면·대체 글에도 repo-docs 자리표시 적용
- 실행 위치: 저장소 루트. `Output`은 저장소 루트 기준 경로

## 변환

- 저장소 루트에서 실행. 기존 호출 경로 유지, `.dap`는 daphnis, `.tape`는 VHS 호출

```sh
python3 <이 스킬 폴더>/scripts/render_figures.py --daphnis <daphnis 경로>/src/cli.js docs/assets/architecture.dap
```

- `--daphnis`: 작업본 루트 또는 `src/cli.js` 경로. 생략 시 `DAPHNIS_PATH`, 없으면 PATH의 `daphnis` 실행. `--static`, `--require-data`, `--require-ci`는 daphnis에 전달
- 옛 `--mutoscope`·`MUTOSCOPE_PATH`: 이번 판까지 별칭 허용, 지정 시 stderr에 폐기·대체 이름 안내. 우선순위: 새 옵션 → 옛 옵션 → 새 환경 변수 → 옛 환경 변수 → PATH
- 원본 인자 생략 시 git 추적 원본 탐색. 공백 포함 경로 지원. 새 원본은 경로 지정 또는 git 추가 후 실행
- 옛 형식 원본 발견 시 목록 출력 후 변환 전 실패. `.dap`로 내용 이전 필요, 확장자만 변경 금지
- 모든 `.dap`의 strict 검사 뒤 렌더. 검사 실패 시 이 호출의 렌더 시작 금지. 렌더 중 I/O 실패의 전체 파일 원자성 보장 없음
- `.tape`와 그림 전용 옵션 동시 사용 금지. VHS 실행 위치와 결과 계약: VHS 절
- 실패 시 원본 수정 후 재실행. 실패 전부터 있던 SVG를 새 성공 결과로 간주 금지

## 검사

1. `daphnis check --strict`: 출력 없음과 종료 코드 0 확인. 소스 설치에서는 설치와 실행 절의 `node` 접두사 사용
2. 실험 차트: `--require-data` 추가. 신뢰구간이 필요한 막대·덤벨·선·차이 차트: `--require-ci`도 추가. 같은 옵션으로 render 실행, 문서 안 블록은 md에 같은 검사 옵션 적용
3. 원본 수와 SVG 수·문서 링크 대조. 같은 이름의 다른 원본을 한 `--out`에 쓰기 금지
4. 같은 원본·입력 JSON·도구 커밋으로 두 번 변환 후 SVG 바이트 동일 확인. VHS 제외
5. 실제 문서 삽입 환경에서 라이트·다크의 글자, 겹침, 잘림, 빈 영역과 움직임 확인. 시간차 두 장면과 정지 출력 대조, 정지 출력의 움직임 없음 확인
6. 모든 그림의 대체 글·자리표시 확인. README 그림 배치·개수: repo-docs-readme 적용
7. 변환 도구 교체: 실제 기존 문서 호출·실험 데이터 입력으로 확인. 움직이는 출력·정지 출력·실패 시 파일 쓰기 계약 함께 검증. 오류 원본의 check와 render 실패, 새 산출물 없음과 기존 산출물 보존 확인

- `--strict`: 경고도 실패. 폐기 진단은 별도 `--no-deprecated`로 실패 처리(figure-syntax 호환 규칙). 출력이 남으면 진단 해결 후 재검사
- 기계 검사 통과를 실제 문서의 재생·가독성 확인으로 대체 금지
