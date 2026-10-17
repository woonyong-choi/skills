---
name: repo-docs-figures
description: "README, docs, PR에 넣는 구조도, 차트, 스크린샷, 데모 GIF와 대체 글을 만들거나 고칠 때 쓴다."
---

# 문서 그림

문서 그림을 원본에서 다시 만들 수 있게 만들고, 규격과 대체 글을 맞추고, 실제 문서에서 보이는 모습을 검사한다. 공통 규칙은 [repo-docs](../repo-docs/SKILL.md)를 먼저 따르고, 이 스킬은 이미지 규격, 그림 원본 형식, 촬영, 변환, 검사, 대체 글을 맡는다. 그림을 넣는 자리는 종류별 스킬이 정한다.

## 원칙

- 원본, 입력 JSON, 만든 그림을 함께 커밋한다. 만든 그림을 손으로 고치지 않는다.
- 순서, 전이, 시간 변화가 전할 정보이면 움직이는 SVG를 만든다. 마지막 구조나 값만 전하면 정지 SVG를 만든다.

## 규격

이미지 규격의 정본이다. 다른 스킬은 숫자를 옮겨 적지 않고 이 절을 링크한다.

| 종류 | 형식 | 위치 | 크기 | 길이와 용량 |
|---|---|---|---|---|
| 로고 | SVG, 없으면 PNG(투명 배경) | `docs/assets/logo-light.*`, `logo-dark.*` | 표시 72~96px, PNG면 그 2배 | 100KB 이하 |
| 데모 GIF | GIF | `docs/assets/demo.gif` | 폭 960px 이하 | 15초 이하, 10MB 이하 |
| 스크린샷 | PNG | `docs/assets/{이름}-light.png`, `{이름}-dark.png` | 파일 폭 1920px | 1장 1MB 이하 |
| 구조도와 차트 | SVG와 원본 | `docs/assets/{이름}.svg` | 제한 없음 | 해당 없음 |
| PR 화면 비교 | PNG | `pr-assets` 브랜치 | 창 폭 1280px, 390px(**git-pull-request** 스킬의 화면과 움직임 변경 절) | 스크린샷과 같다 |

- 이름은 보여 주는 것을 영어 소문자 kebab-case로 짓는다(`lag-table-growing-light.png`). `image1`, 날짜, 한글 이름을 쓰지 않는다.

## 도구와 파일

- **렌더러.** 저장소의 그림 도구와 원본 형식을 먼저 쓴다. 원본, 입력, 변환 명령, 도구 버전을 남겨 같은 입력으로 다시 만들 수 있게 한다.
- **원본과 산출물.** `docs/assets/{이름}.{원본 확장자}`와 `docs/assets/{이름}.svg`로 둔다. 이름은 규격 절을 따른다.
- **실험 차트.** 분석 결과에서 만든 입력을 쓴다. 원자료, 추출 경로, 생성 명령을 남기고 수치를 다시 손으로 넣지 않는다.
- **색, 글꼴, 크기, 아이콘.** 대상 저장소의 디자인 정본에서 정한다. 정본 값을 복사하지 않고, 사용자 아이콘 세트는 경로로 참조한다.
- **면 위계.** 판과 그룹은 무채색이고 중첩 깊이마다 밝기 단계를 둔다. 그룹에는 테두리가 없고 도형 외곽선은 둔다. 강조 그룹도 무채색이다.
- **의미별 색 역할.** 핵심 흐름, 현재 상태, 주 계열, 아이콘은 주 강조색을 쓴다. 오류, 정상, 주의, 비교 계열은 각각 정본의 역할 토큰을 쓴다. 드문 강조와 주 강조를 가른다.
- **글꼴 역할.** 본문, 숫자, 코드는 정본 글꼴을 쓰고 차트 숫자는 `tabular-nums`를 쓴다. 자간도 정본을 따른다.
- **대비.** 라이트와 다크 모두 글자는 4.5 이상, 도형 외곽선과 뜻 있는 그래픽은 3 이상이다. 꾸밈 요소만 정본이 명시한 예외를 따른다.
- **문서 표시.** 문서에는 SVG와 대체 글을 넣는다. 문서 안 원본을 쓰는 도구는 원본 블록도 남긴다. HTML 재생기는 검증용이다.
- **기계 검사.** 원본과 입력 수를 산출물과 문서 링크 수와 대조한다. 같은 입력과 도구 버전으로 다시 만든 바이트를 비교한다. 녹화물은 프레임 바이트 비교에서 뺀다.
- **실제 삽입 환경.** 라이트와 다크에서 글자, 겹침, 잘림, 빈 영역을 확인한다. 움직임은 시간차 장면과 정지 출력을 대조한다.
- **도구 교체.** 기존 문서 호출, 실험 입력, 움직임, 정지 출력, 실패 때의 쓰기 계약을 검증한다. 실패한 원본에서 새 산출물이 생기지 않고 기존 산출물이 그대로 남는지 확인한다.

## 대체 글

- 그 그림을 봐야 알 수 있는 결론 한 문장으로 쓰고 마침표를 찍지 않는다. 문체는 그 문서를 따른다. 고정 문장을 쓰지 않고 그림마다 새로 쓴다.
- 그림 종류나 파일 이름만 적지 않는다. `queuewatch 스크린샷`은 안 되고 `지연이 늘어나는 토픽이 표 맨 위에 표시된다`는 된다.
- 라이트와 다크 두 장은 같은 대체 글을 쓴다. 두 장면을 합친 그림은 두 장면을 비교한 결론 한 문장으로 쓴다.
- `README.en.md`는 같은 그림 파일을 쓰고 대체 글만 영어로 쓴다.
- 문서 이미지에는 대체 글이 반드시 있어야 한다. SVG 안 제목으로 대신하지 않고, 생성된 이미지 줄까지 확인한다.
- 데이터 출처와 구현 여부 표시, 파일 이름은 repo-docs 자리표시 절을 따른다. 그림 제목, 부제, 단계 설명에도 같은 사실 상태를 적용한다. 예시 차트 부제의 접두사도 그 정본을 따른다.

## 선택 어댑터

기존 변환 스크립트가 지원하는 형식과 의존 도구다. 그림 도구 Torso(명령 `thinkflow`, 원본 `.thinkflow`, 저장소 https://github.com/woonyong-choi/torso)와 VHS, Playwright를 쓴다. 다른 렌더러를 쓰는 저장소는 위 공통 조건을 채우는 대응 명령을 쓴다. 해당 작업을 시작하기 전에 아래 하위 문서를 반드시 읽는다.

| 조건 | 하위 문서 |
|---|---|
| Torso 작업을 시작하기 전 | [references/thinkflow.md](references/thinkflow.md) |
| Torso를 설치하거나 직접 실행하기 전 | [references/execution.md](references/execution.md) |
| Torso Markdown 그림이나 CI 연결을 바꾸기 전 | [references/markdown.md](references/markdown.md) |
| Torso 그림 원본을 쓰거나 바꾸기 전 | [references/syntax.md](references/syntax.md) |
| Torso 그림에 담을 항목, 그림 종류, 배치를 정하기 전, 렌더 결과의 품질을 확인하기 전 | [references/torso-quality.md](references/torso-quality.md) |
| Torso 실험 차트를 쓰거나 바꾸기 전 | [references/charts.md](references/charts.md) |
| 스크린샷을 찍거나 합치기 전, `screens.json`을 쓰거나 바꾸기 전 | [references/screenshots.md](references/screenshots.md) |
| VHS 녹화 원본을 쓰거나 실행하기 전 | [references/vhs.md](references/vhs.md) |
| `render_figures.py` 변환을 실행하기 전 | [references/conversion.md](references/conversion.md) |
| Torso 변환과 검사, 변환 도구 교체 전 | [references/validation.md](references/validation.md) |

## 답변

- 만들거나 고친 원본과 산출물 경로를 적는다.
- 실행한 검사와 결과, 실제 삽입 환경에서 직접 확인한 범위를 나눠 적는다.

## 구분

- README 그림 배치는 [repo-docs-readme](../repo-docs-readme/SKILL.md)의 머리와 절 규칙이 맡는다.
- 실험 차트의 통계와 신뢰구간은 [repo-docs-experiment](../repo-docs-experiment/SKILL.md)의 통계 규칙이 맡는다.
- 그림을 넣는 자리는 각 종류별 `repo-docs-*` 스킬이 맡는다.
