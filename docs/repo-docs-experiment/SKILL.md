---
name: repo-docs-experiment
description: "모집단, 표본, 판정 기준을 정한 측정이나 비교 실험의 설계, 수집, 결과를 기록할 때 쓴다."
---

# 실험 기록

설계 값을 정하는 실험 하나를 폴더 하나로 남긴다. 수집 전에 계획을 커밋으로 고정하고, 수집한 뒤 결과를 보고한다. 공통 규칙은 [repo-docs](../repo-docs/SKILL.md)를 먼저 따르고, 이 스킬은 실험 대상, 폴더, 흐름, 템플릿, 통계 규칙, 검사를 맡는다.

## 언제 쓰나

| 실험으로 하는 것 | 실험으로 하지 않는 것 |
|---|---|
| 설계의 규칙이나 기본값이 측정 결과에 기댈 때 | 공식 문서로 알 수 있는 사실([repo-docs-note](../repo-docs-note/SKILL.md) reference) |
| 외부 도구 동작을 비교하거나 추론할 모집단과 판정 기준이 있을 때 | 그 실행의 관측만 남길 때([repo-docs-note](../repo-docs-note/SKILL.md) insight) |
| 두 방식 중 나은 쪽을 수치로 고를 때 | CI가 계속 재는 성능 회귀 |

- 진행 상태는 단계 1의 추적 항목에만 둔다. 문서에 적지 않는다.

## 폴더

```text
docs/experiments/
  README.md
  {실험}/
    design.md
    report.md
    run.sh
    env.json
    logs/{명령}-{실행 id}.log
    data/
      README.md
      SHA256SUMS
      raw/{출처}-{실행 id}.jsonl
      processed/{이름}.csv
    scripts/
      01-collect.{확장자}
      02-process.{확장자}
      03-analyze.{확장자}
    results/
      summary.json
      tables/{이름}.csv
```

| 이름 | 규칙 |
|---|---|
| `{실험}` | 확인할 것을 영어 소문자 kebab-case로 쓴다(`cache-hit-ratio`). 번호와 날짜를 넣지 않는다 |
| `{실행 id}` | `YYYYMMDDTHHMMSSZ-{커밋 7자리}` |
| `raw/` | 수집한 그대로 두고 수집 뒤 고치지 않는다. 다시 수집하면 새 실행 id 파일로 둔다 |
| `processed/` | 스크립트만 만든다. 지워도 `run.sh process`로 다시 만든다 |
| `scripts/` | 번호가 실행 순서다. 입력은 앞 단계 파일만 쓴다 |
| `results/summary.json` | 보고서의 모든 수치를 담는다. 보고서 수치는 이 파일에서만 가져온다 |
| 결과 차트 | 저장소의 분석 도구로 결과 파일에서 재현한다. 원자료·추출 경로·생성 명령과 산출물을 연결하고 수치를 손으로 옮기지 않는다. 통계 차트는 DiagramPlay 범위에 포함하지 않는다 |
| `run.sh` | `collect`, `process`, `analyze`, `verify`, `all` 다섯 명령을 둔다. `./run.sh analyze`는 `raw/`에서 전처리를 다시 실행한 뒤 분석해 결과를 다시 만든다 |
| `logs/` | `run.sh` 명령마다 실행 출력 전부를 남긴다. 고치지 않고 홈 경로는 `~`로 쓴다. 아래 `log` 함수로만 남기고, 같은 로그가 있으면 거부한다. 검사나 재현으로 다시 돌릴 때는 `RUN_ID={실행 id}-check`를 쓰고 그 로그는 커밋하지 않는다 |
| 실행 id 공유 | `collect`가 첫 줄에 출력한 id를 같은 실행의 다음 명령에 `RUN_ID={실행 id} ./run.sh {명령}`으로 넘긴다. 빼면 새 id가 생긴다 |
| `env.json` | 계획의 실험 환경 표와 같은 항목을 `collect`가 자동으로 남긴다. 계획 값과 다르면 보고서의 계획과 다른 점에 적는다 |
| 파일 크기 | 저장소의 파일 크기 정책을 따른다. 밖에 저장하면 접근 경로, SHA-256, 재현 방법을 적는다 |

`run.sh` 머리는 다음과 같이 쓰고 명령마다 `log 명령 실행할 것`으로 부른다. 실패한 명령은 0이 아닌 코드로 끝나고, 어느 폴더에서 실행해도 실험 폴더를 기준으로 돈다.

```sh
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
id=${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)-$(git -C "${PROJECT_DIR:-.}" rev-parse --short=7 HEAD)}
log() { local f="logs/$1-$id.log"; [[ ! -e $f ]] || { echo "$f exists; use another RUN_ID" >&2; return 1; }; mkdir -p logs; { printf '$ RUN_ID=%s ./run.sh %s\n' "$id" "$1"; "${@:2}"; } 2>&1 | sed "s|$HOME|~|g" | tee "$f"; }
```

## 단계

1. 저장소 추적 정책에 따라 실험 식별자를 만든다. GitHub를 쓰면 `experiment` 이슈(**git-issue** 스킬)를, 추적기가 없으면 설계 문서 안 식별자를 쓴다.
2. `design.md`, `run.sh`, `scripts/`를 쓰고 수집 전에 계획, 가설, 판정 기준을 커밋으로 고정한다.
3. 일반 실측은 2번의 계획 커밋을 같은 PR의 첫 기준점으로 두고, 수집과 결과를 더해 함께 머지한다.
4. 수집 전에 승인받아야 할 데이터 접근이나 판정 조건이 있는 실험만 2번을 저장소 승인 절차로 먼저 확정한다. PR을 쓰면 사전 등록 PR을 머지한다. 이슈 연결은 **git-issue** 스킬의 닫기 절을 따른다.
5. `./run.sh collect`로 수집하고 출력 첫 줄의 실행 id를 남긴다. 미리 본 데이터는 계획에 적고 가설 검증용 자료와 가른다.
6. `RUN_ID={실행 id} ./run.sh verify`, `RUN_ID={실행 id} ./run.sh analyze`를 돌린 뒤 저장소의 분석 도구로 결과 차트를 만든다. 원자료·추출 경로·생성 명령을 연결하고 수치를 손으로 옮기지 않는다.
7. `report.md`, `data/README.md`를 쓰고 `docs/experiments/README.md`의 결론 칸을 채운다.
8. 결론이 설계를 바꾸면 같은 PR에서 설계 문서를 고친다.

- 수집을 시작한 뒤에는 `design.md`의 가설과 판정 기준을 고치지 않는다.
- 결과를 본 뒤 계획, 가설, 판정 기준을 바꾸면 보고서의 `계획과 다른 점`에 적는다. 바뀐 부분의 분석은 `추가 분석`으로 가르고 가설 검증 판정에 쓰지 않는다.

## 문체

| 문서 | 시제 |
|---|---|
| `design.md` | 할 일을 현재형 `-한다`로 쓴다 |
| `report.md`의 실험 환경, 데이터 처리, 가설 검증, 추가 분석 | 과거형 `-했다`, `-였다` |
| `report.md`의 요약, 해석, 위험 요소 점검, 한계, 결론 | 현재형 `-다` |

## 템플릿

- `docs/experiments/README.md`를 쓰거나 갱신하거나 검토하기 전에 [references/index.md](references/index.md)를 반드시 읽는다.
- `design.md`를 쓰거나 갱신하거나 검토하기 전에 [references/design.md](references/design.md)를 반드시 읽는다.
- `data/README.md`를 쓰거나 갱신하거나 검토하기 전에 [references/data.md](references/data.md)를 반드시 읽는다.
- `report.md`를 쓰거나 갱신하거나 검토하기 전에 [references/report.md](references/report.md)를 반드시 읽는다.

## 통계 규칙

| 대상 | 규칙 |
|---|---|
| 비율 | `k/n`과 비율, 표본과 대응 구조에 맞는 신뢰구간을 쓴다. 방법, 가정, 출처는 계획에 적는다 |
| 같은 입력에서 두 방식 비교 | 대응 관계를 지키고 불일치 수와 효과 차이, 신뢰구간을 쓴다. 검정은 자료 유형과 표본 가정을 근거로 고른다 |
| 연속값 | 분포와 판정 목적에 맞는 요약량, 차이, 불확실성을 미리 정한다 |
| 시간 측정 | 반복 수, 예열 수, 이상치 분류를 함께 쓴다. 여러 비율을 모은 방법과 각 값을 적는다 |
| 개수 대조(토큰 등) | 정확한 개수, 차이의 절댓값과 백분율, 항목별 분포를 쓴다 |
| 검정 | 계산한 p값과 효과 크기를 함께 쓴다. 판정 임계값만 보고하지 않는다 |
| 다중 비교 | 확인 가설과 선택 절차에 맞는 보정 방법과 근거를 미리 고정한다 |
| 유효 숫자 | 측정 정밀도와 판정 목적에 맞게 미리 고정한다 |
| 무작위 | 시드는 계획의 실험 환경과 `env.json`에 적는다. LLM 샘플링처럼 고정할 수 없는 부분은 시드 칸에 이유를 적는다 |

## 검사

보고서를 머지하기 전에 다음을 확인한다.

1. 수집 전 계획 커밋이 첫 `raw/` 파일 커밋의 조상이다.
2. `RUN_ID={실행 id}-check ./run.sh verify`가 통과한다.
3. `RUN_ID={실행 id}-check ./run.sh analyze` 뒤 `results/`가 커밋본과 바이트까지 같다. 결과 차트도 같은 입력·분석 도구·생성 명령으로 재현되는지 확인한다.
4. 보고서의 모든 수치가 `results/summary.json`에 있다.
5. 실패하거나 뺀 실행이 모두 데이터 처리 표에 있다.
6. `logs/`에 보고한 실행 id의 명령별 로그가 있다.

## 답변

- 실험 폴더 경로, 단계 진행 위치, 실행 id를 적는다.
- 보고서를 썼으면 가설별 판정과 설계에 반영한 문서를 적는다.
- 통과하지 못한 검사 항목이 있으면 그 항목을 적는다.

## 구분

- 구성도·순서도·시퀀스와 문서에 넣는 스크린샷·데모는 [repo-docs-figures](../repo-docs-figures/SKILL.md)가 맡는다. 통계 결과 차트는 실험의 분석 도구로 만든다.
- 완료 조건의 범위 변경은 **git-issue** 스킬의 범위 변경 절이 맡는다.
- 실험 이슈, 브랜치, PR, 커밋 실행은 **git-issue**, **git-branch**, **git-pull-request**, **git-commit** 스킬이 맡는다.
