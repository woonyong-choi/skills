# 스킬 형식 통일과 조건부 로드: 실험 결과

## 요약

요청 14개의 o200k 로드 합은 123250에서 106293으로 13.8% 준다(n = 14). 가설 7개 중 H3, H4, H5, H7은 채택, H1, H2는 기각, H6은 보류다. 새 형식은 스킬 폴더 안내의 작성 규칙으로 고정한다.

## 방법

| 항목 | 값 |
|---|---|
| 설계 | [실험 설계](design.md), 커밋 해당 없음 |
| 실행 id | `20260930T030000Z-local` |
| 환경 | [env.json](env.json) |
| 표본 | 설계: 스킬 22개, 요청 30개, 시나리오 14개, 작성 라운드 4개. 실제: 동일 |

옛 스킬 21개와 새 스킬 22개를 스냅숏으로 묶고, SKILL.md마다 바이트, o200k 토큰, Claude 구 토크나이저 토큰을 쟀다. 시나리오 14개는 요청마다 불러오는 스킬 집합을 규칙대로 정해 토큰을 더했다. 트리거는 새 에이전트에게 카탈로그만 주고 요청 30개의 스킬을 고르게 했다. 결정성은 같은 사실 파일로 두 에이전트가 문서 4개를 만들게 하고 `diff`로 줄 차이를 셌다. 누락 대조는 새 에이전트 셋이 옛 파일과 새 파일을 항목마다 맞대고, 수정 뒤 다른 에이전트가 다시 대조했다.

## 설계와 다른 점

| 변경 | 시점 | 이유 | 결론에 미친 영향 |
|---|---|---|---|
| 사전 등록 없이 측정 뒤 설계 작성, 가설과 기준도 사후 설정 | 분석 중 | 스킬 구조 변경과 측정을 한 작업에서 진행 | 판정의 기준 선택 의존 |
| 측정 중 스킬 수정(r1, r2, r3, after) | 수집 중 | 누락 대조와 결정성 차이에서 찾은 규칙 결함 수정 | 라운드 사이 차이를 규칙 하나에 귀속 불가 |
| `skills-r2.tar.gz`를 r3 상태에서 복원 | 수집 뒤 | r2 상태 별도 저장 없음 | r2 토큰 수치만 영향, 판정 영향 없음 |
| r3 상태 원자료 이름을 `skills-after`에서 `skills-r3`로 변경 | 수집 뒤 | 재대조 뒤 스킬을 다시 고쳐 최종본을 새 파일로 저장 | 없음 |
| 실행 id에 커밋 대신 `local` | 수집 전 | 저장소 밖 작업 폴더에서 측정 | 없음 |
| 원자료 필수 필드(`run_id`, `trial_id`, `condition`, `ts_utc`) 미적용 | 수집 전 | 산출물이 행 단위 기록이 아닌 문서 파일 | 없음 |

## 결과

### 흐름

| 단계 | 수 |
|---|---|
| 수집 | 12 |
| 분석 | 12 |

### 확인 분석

| 가설 | 지표 | 값 | 95% 신뢰구간 | n | 판정 |
|---|---|---|---|---|---|
| H1 | 조건부 없는 요청의 o200k 변화 | 9개 중 6개 -20% 이하. s09 +14.6%, s10 +13.6%, s13 +0.1% | 해당 없음 | 9 | 기각 |
| H2 | 조건부 요청의 o200k 변화 | 5개 중 4개 +10% 이하. s06 +10.2% | 해당 없음 | 5 | 기각 |
| H3 | 요청 14개 o200k 합 변화 | 123250 → 106293, -13.8% | 해당 없음 | 14 | 채택 |
| H4 | 재대조 반영 | 24/24, 유지 결정 2건. 재대조의 새 충돌 10건도 수정 | 해당 없음 | 26 | 채택 |
| H5 | 기반 줄을 따른 적중 | 실행 3개 모두 30/30(100.0%), 과선택 최대 1 | [88.6, 100.0] | 30 | 채택 |
| H6 | r4 줄 차이 비율 | 7/121(5.8%) | [2.8, 11.5] | 121 | 보류 |
| H7 | 형식 검사 위반 | 544 → 0 | 해당 없음 | 22 | 채택 |

시나리오별 수치는 [scenario_load.csv](results/tables/scenario_load.csv)에 있다. 트리거 실행별 수치는 [trigger.csv](results/tables/trigger.csv)에 있다. 라운드별 결정성은 [determinism.csv](results/tables/determinism.csv)에 있다.

### 탐색 분석

스킬 전체 크기는 거의 그대로였다. 바이트는 162055에서 161358로 0.4% 줄었다. o200k는 47680에서 47651로 0.1% 줄었다. Claude 구 토크나이저 값은 71811에서 71812였다. 항상 올라가는 카탈로그는 o200k 1417에서 1248로 11.9% 줄었다. 같은 카탈로그의 Claude 구 토크나이저 값은 2297에서 2012로 12.4% 줄었다. 카탈로그만 본 적중은 옛 카탈로그 29/30, 새 카탈로그 28/30이었다. 새 카탈로그에서 빠진 두 요청(홍보 영상, 리팩터링 기법)은 기반 줄을 따르면 채워졌다. 줄 차이 비율은 r1 14.4%, r2 10.7%, r3 9.0%, r4 5.8%였다. 작성 에이전트 8명의 기록상 읽은 스킬은 모두 같은 6개, 같은 순서였다. 조건이 거짓인 repo-docs-figures와 repo-docs-llms는 아무도 읽지 않았다.

## 논의

### 해석

조건부 로드는 그림, 판단 기록, 리팩터링 기법이 필요 없는 요청에서 로드량을 크게 줄이고 전체 합도 줄인다. 반면 문서 목록 표와 결정성 규칙을 넘겨받은 repo-docs가 커져 s06, s09, s10은 늘었다. 파일 전체 크기가 거의 그대로인 것은 코드와 템플릿이 대부분이고 새 규칙이 압축분을 채웠기 때문이다. 결정성의 남은 차이는 사실 파일에 없는 주어, 동의어, 배경 문장의 자유 서술에 몰려 있다.

### 타당성 위협

| 종류 | 위협 | 이 실험에서 |
|---|---|---|
| 내적 | 가설과 기준을 결과를 본 뒤 정해 유리한 기준을 고를 수 있다. | 기각 2개와 보류 1개를 그대로 보고했다. |
| 내적 | 라운드마다 여러 규칙을 함께 바꿔 어떤 규칙이 차이를 줄였는지 가를 수 없다. | 라운드별 스냅숏은 남겼지만 규칙 하나씩의 효과는 재지 않았다. |
| 구성 | 로드량은 규칙대로 불러온다는 가정의 계산값이고 실제 에이전트가 읽은 양이 아니다. | 작성 에이전트 8명이 기록한 읽은 스킬이 계산 집합과 같았다. |
| 구성 | Claude 토큰은 공개된 구 토크나이저의 근사치다. | 두 토크나이저의 변화율 방향은 s13(+0.1%, -0.2%)을 뺀 13개 시나리오에서 같았다. |
| 외적 | 사실 파일 하나, 요청 30개로 다른 저장소에 일반화하기 어렵다. | 결정성은 한 저장소의 문서 4개만 쟀다. |

### 한계

- 줄 차이 비율의 줄 사이 비독립, 신뢰구간 과소 추정 가능
- 트리거 실행 수가 새 카탈로그 3회, 옛 카탈로그 1회
- 결정성 라운드마다 작성자 2명
- 코드, git 스킬의 결정성은 측정 전

## 부록. #25 변경의 크기와 읽기 연결

이 부록은 위 실험과 따로 잰 #25 변경 시점의 정적 값이다. 위 실험의 스냅숏과 스킬 집합이 다르다.

### 본문 크기

기준 커밋 `d7e8489`와 #25 변경 후의 실제 스킬 27개를 비교했다. 표에는 지금 남은 24개와 삭제한 repo-docs-journal을 두고, 그 밖에 삭제한 스킬은 표와 합계에서 뺐다. 값은 frontmatter와 개행을 포함한 UTF-8 `SKILL.md` 전체 바이트다. 시험 fixture와 실험 보관본은 제외했다. 하위 문서로 옮긴 내용은 보존하며, 이 표는 저장소 용량이나 평균 호출 비용의 감소를 뜻하지 않는다.

| 스킬 | 변경 전 | 변경 후 | 감소 |
|---|---:|---:|---:|
| [code-refactoring](../../code/code-refactoring/SKILL.md) | 12,758 | 4,865 | 7,893 |
| [code-style](../../code/code-style/SKILL.md) | 20,750 | 19,747 | 1,003 |
| [code-style-css](../../code/code-style-css/SKILL.md) | 7,479 | 6,523 | 956 |
| [code-style-typescript](../../code/code-style-typescript/SKILL.md)(측정 당시 JavaScript 전용) | 7,279 | 5,321 | 1,958 |
| [code-style-kotlin](../../code/code-style-kotlin/SKILL.md) | 7,125 | 5,536 | 1,589 |
| [code-style-python](../../code/code-style-python/SKILL.md) | 5,728 | 5,034 | 694 |
| [code-style-rust](../../code/code-style-rust/SKILL.md) | 8,073 | 6,251 | 1,822 |
| [design-tokens](../../design/design-tokens/SKILL.md) | 8,991 | 7,502 | 1,489 |
| [folder-naming](../../code/folder-naming/SKILL.md) | 3,399 | 3,213 | 186 |
| [git-branch](../../git/git-branch/SKILL.md) | 7,827 | 5,587 | 2,240 |
| [git-commit](../../git/git-commit/SKILL.md) | 5,753 | 5,017 | 736 |
| [git-issue](../../git/git-issue/SKILL.md) | 17,281 | 8,155 | 9,126 |
| [git-pull-request](../../git/git-pull-request/SKILL.md) | 6,169 | 5,026 | 1,143 |
| [repo-docs](../../docs/repo-docs/SKILL.md) | 20,511 | 11,048 | 9,463 |
| [repo-docs-decision](../../docs/repo-docs-decision/SKILL.md) | 5,568 | 2,881 | 2,687 |
| [repo-docs-design](../../docs/repo-docs-design/SKILL.md) | 10,869 | 4,274 | 6,595 |
| [repo-docs-experiment](../../docs/repo-docs-experiment/SKILL.md) | 12,990 | 6,463 | 6,527 |
| [repo-docs-figures](../../docs/repo-docs-figures/SKILL.md) | 14,171 | 4,151 | 10,020 |
| repo-docs-journal(삭제) | 6,458 | 3,473 | 2,985 |
| [repo-docs-llms](../../docs/repo-docs-llms/SKILL.md) | 3,693 | 2,596 | 1,097 |
| [repo-docs-note](../../docs/repo-docs-note/SKILL.md) | 3,141 | 2,352 | 789 |
| [repo-docs-readme](../../docs/repo-docs-readme/SKILL.md) | 12,684 | 11,218 | 1,466 |
| [repo-docs-root](../../docs/repo-docs-root/SKILL.md) | 6,999 | 2,815 | 4,184 |
| [repo-docs-spec](../../docs/repo-docs-spec/SKILL.md) | 7,736 | 1,941 | 5,795 |
| [skill-sync](../../tools/skill-sync/SKILL.md) | 8,231 | 5,405 | 2,826 |
| 합계 | 231,663 | 146,394 | 85,269 |

기본 본문 합계는 36.8% 줄었다. 아래 조건에 해당하는 작업은 하위 문서를 추가로 읽는다. 이미 읽은 정본은 같은 작업에서 중복 합산하지 않으며, 원본 변경 시 다시 확인한다.

### 읽기 연결

아래 읽기 연결과 읽기량은 #25 시점의 정적 값이다. 지금 스킬 크기와 다르며 실제 호출 빈도나 평균 토큰 사용량을 잰 값이 아니다.

`기반`은 먼저 적용하는 스킬이다. 종류별·언어별 스킬의 필수 규칙은 본문에 남기고, 하위 문서는 작업·파일·단계 조건이 맞을 때 읽는다. 다른 스킬의 하위 문서는 이름으로 찾은 스킬 폴더 기준 경로다. 같은 스킬의 하위 문서는 상대 링크로 열 수 있으며, 설치본과 zip에도 같은 내용이 들어간다.

| 작업 | 먼저 읽는 정본 | 조건부 하위 문서 |
|---|---|---|
| Python 코드 검토 | code-style, code-style-python | 린트 설정 생성·변경·감사 시 Python의 `references/lint.md` |
| CSS 검토 | code-style, design-tokens, code-style-css | Stylelint 설정 작업 시 CSS의 `references/lint.md`; 토큰 분류·단계 신설·변경 시 `references/categories.md` |
| 커밋 메시지 작성 | git-commit, repo-docs의 `references/writing.md` | 메시지 작성 시 git-commit의 `references/commit-template.txt`; 실제 커밋 전 검사 시 code-style |
| 설계 문서 작성 | repo-docs, `references/writing.md`, repo-docs-design | 작성·갱신·검토 대상에 따라 `references/index.md`, `architecture.md`, `design.md`, `glossary.md` 중 해당 문서 |
| 이슈 본문 작성 | git-issue, repo-docs의 `references/writing.md` | 종류별 `references/{design,build,bug,experiment,docs}.md`; 게시 전 `public-links.md`; 상태 사건 발생 전 `project-status.md` |
| 스킬 검사 | skill-sync, `references/execution.md` | 형식 수정 시 `references/authoring.md`; 도구 설치 시 `installation.md`; 계정 배포 시 `claude-upload.md` |

위 연결에 따른 정적 읽기량이다. Python·CSS 검토는 설정 변경이 없는 기본 경로다. 아키텍처 작성은 공통 문체와 선택한 템플릿까지 포함한다.

| 작업 | 변경 전 바이트 | 변경 후 바이트 | 감소 |
|---|---:|---:|---:|
| Python 코드 검토 | 26,478 | 24,781 | 1,697 |
| CSS 검토 | 37,220 | 33,772 | 3,448 |
| 커밋 메시지 작성 | 26,264 | 14,534 | 11,730 |
| 아키텍처 문서 작성 | 31,380 | 27,543 | 3,837 |

## 재현

```sh
./run.sh verify
./run.sh analyze
```

| 파일 | SHA-256 |
|---|---|
| `data/SHA256SUMS` | `34b4dac6c5f76e06fa507a3b33637cc4e4d330d1ac467ee16633ad8b4c3b2e9b` |

## 결론

| 가설 | 판정 | 반영한 문서 |
|---|---|---|
| H1 | 기각 | 없음 |
| H2 | 기각 | 없음 |
| H3 | 채택 | [스킬 폴더 안내](../../README.md) |
| H4 | 채택 | [스킬 폴더 안내](../../README.md) |
| H5 | 채택 | [스킬 폴더 안내](../../README.md) |
| H6 | 보류 | 없음 |
| H7 | 채택 | [스킬 폴더 안내](../../README.md) |
