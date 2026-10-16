---
name: repo-docs-experiment
description: "모집단·표본·판정 기준을 정한 측정·비교 실험의 설계·수집·결과를 기록할 때 사용."
---

# Repo Docs Experiment

- 우선순위: 사용자 지시 → 저장소 규칙 → 이 스킬. 범위 밖은 명시한 소유 스킬 적용
- 기반: repo-docs 먼저 적용. 이 스킬 범위: 실험 대상, 폴더, 흐름, 템플릿, 통계 규칙, 검사
- 필요할 때만 읽기: 결과 차트 → repo-docs-figures; 완료 조건의 범위 변경 → git-issue 범위 변경 절; 실험 이슈, PR, 커밋 실행 → git-issue, git-branch, git-pull-request, git-commit

- 실험 하나 = 폴더 하나. 수집 전 계획 커밋 → 수집 → 결과 보고
- 진행 상태: 흐름 1의 추적 항목. 문서에 기록 금지
- 등록 프로젝트(Vault 문서 영역 사용): 실험 폴더는 Vault `docs/experiments/`, `run.sh` 실행 시 `PROJECT_DIR=<작업 저장소 절대 경로>` 지정. 계획 고정은 커밋 대신 수집 전 `design.md` SHA-256을 이슈에 기록, 흐름 3·8과 검사 1은 저장소에 승인된 실험 문서일 때만

## 대상

실험으로 하는 것 → 실험으로 하지 않는 것:

- 설계의 규칙이나 기본값이 측정 결과에 기대는 경우 → 공식 문서로 알 수 있는 사실 (repo-docs-note reference)
- 외부 도구 동작을 비교·추론할 모집단과 판정 기준이 있는 경우 → 해당 실행의 관측만 기록하는 경우 (repo-docs-note insight)
- 두 방식 중 나은 쪽을 수치로 고르는 경우 → CI가 계속 재는 성능 회귀

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

이름 → 규칙:

- `{실험}` → 확인할 것, 영어 소문자 kebab-case: `cache-hit-ratio`. 번호, 날짜 금지
- `{실행 id}` → `YYYYMMDDTHHMMSSZ-{커밋 7자리}`
- `raw/` → 수집한 그대로, 수집 뒤 수정 금지. 재수집은 새 실행 id 파일
- `processed/` → 스크립트만 생성. 지워도 `run.sh process`로 재생성
- `scripts/` → 번호 = 실행 순서. 입력은 앞 단계 파일만
- `results/summary.json` → 보고서의 모든 수치. 보고서 수치는 이 파일에서만
- 결과 차트 → 원본·산출물 위치, JSON 입력과 변환·검사(repo-docs-figures references/charts.md 실험 차트)
- `run.sh` → `collect`, `process`, `analyze`, `verify`, `all` 다섯 명령. `./run.sh analyze`는 `raw/`를 입력으로 전처리를 다시 실행한 뒤 분석을 실행해 결과 재생성
- `logs/` → `run.sh` 명령마다 실행 출력 전부. 수정 금지, 홈 경로는 `~`로. 아래 `log` 함수로만 기록, 기존 로그면 거부. 검사·재현 재실행은 `RUN_ID={실행 id}-check`, 그 로그 커밋 제외
- 실행 id 공유 → `collect`가 첫 줄에 출력한 id를 같은 실행의 이후 명령에 `RUN_ID={실행 id} ./run.sh {명령}`으로 전달. 생략하면 새 id
- `env.json` → 계획의 실험 환경 표와 같은 항목을 `collect`가 자동 기록. 계획 값과 다르면 보고서 계획과 다른 점에
- 파일 크기 → 저장소의 파일 크기 정책 적용. 외부 저장 시 접근 경로·SHA-256·재현 방법 기록

`run.sh` 머리(명령마다 `log 명령 실행할 것`). 실패한 명령은 비영 종료로 전달, 어느 폴더에서 실행해도 실험 폴더 기준:

```sh
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
id=${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)-$(git -C "${PROJECT_DIR:-.}" rev-parse --short=7 HEAD)}
log() { local f="logs/$1-$id.log"; [[ ! -e $f ]] || { echo "$f exists; use another RUN_ID" >&2; return 1; }; mkdir -p logs; { printf '$ RUN_ID=%s ./run.sh %s\n' "$id" "$1"; "${@:2}"; } 2>&1 | sed "s|$HOME|~|g" | tee "$f"; }
```

## 흐름

1. 저장소 추적 정책에 따라 실험 식별자 생성. GitHub 사용 시 `experiment` 이슈(git-issue), 추적기가 없으면 설계 문서 내부 식별자 사용
2. `design.md`, `run.sh`, `scripts/` 작성, 수집 전 계획·가설·판정 기준을 커밋으로 고정
3. 일반 실측: 2번 계획 커밋을 같은 PR의 첫 기준점으로 두고, 수집·결과를 더해 함께 머지
4. 수집 전 승인해야 할 데이터 접근·판정 조건이 있는 실험만 2번을 저장소 승인 절차로 먼저 확정. PR 사용 시 사전 등록 PR 머지. 이슈 연결은 git-issue 닫기 절
5. `./run.sh collect`로 수집, 출력 첫 줄의 실행 id 기록. 사전 열람 데이터는 계획에 기록하고 가설 검증용 자료와 구분
6. `RUN_ID={실행 id} ./run.sh verify`, `RUN_ID={실행 id} ./run.sh analyze` 후 결과 차트 변환(repo-docs-figures references/conversion.md 변환)
7. `report.md`, `data/README.md` 작성, `docs/experiments/README.md` 결론 칸 기입
8. 결론이 설계를 바꾸면 같은 PR에서 설계 문서 수정

- 수집 시작 뒤 `design.md`의 가설·판정 기준 수정 금지
- 결과를 본 뒤 계획·가설·판정 기준을 바꾸면 보고서 `계획과 다른 점`에 기록. 바뀐 부분의 분석은 `추가 분석`으로 구분하고 가설 검증 판정에 사용 금지

## 문체

문서 → 시제:

- `design.md` → 현재형 `-한다`, 할 일
- `report.md` 실험 환경, 데이터 처리, 가설 검증, 추가 분석 → 과거형 `-했다`, `-였다`
- `report.md` 요약, 해석, 위험 요소 점검, 한계, 결론 → 현재형 `-다`

## docs/experiments/README.md

`docs/experiments/README.md` 작성·갱신·검토 전 [index.md](references/index.md) 필수 확인

## design.md

`design.md` 작성·갱신·검토 전 [design.md](references/design.md) 필수 확인

## data/README.md

`data/README.md` 작성·갱신·검토 전 [data.md](references/data.md) 필수 확인

## report.md

`report.md` 작성·갱신·검토 전 [report.md](references/report.md) 필수 확인

## 통계 규칙

대상 → 규칙:

- 비율 → `k/n`과 비율, 표본·대응 구조에 맞는 신뢰구간. 방법·가정·출처는 계획에 기록
- 같은 입력의 두 방식 비교 → 대응 관계 보존, 불일치 수와 효과 차이·신뢰구간. 검정 선택은 자료 유형과 표본 가정에 근거
- 연속값 → 분포와 판정 목적에 맞는 요약량·차이·불확실성을 사전 지정
- 시간 측정 → 반복 수, 예열 수, 이상치 분류 함께. 여러 비율의 집계법과 각 값 기록
- 개수 대조(토큰 등) → 정확한 개수, 차이의 절댓값과 백분율, 항목별 분포
- 검정 → 계산한 p값과 효과 크기 함께, 판정 임계값만 보고 금지
- 다중 비교 → 확인 가설과 선택 절차에 맞는 보정 방법·근거를 사전 고정
- 유효 숫자 → 측정 정밀도와 판정 목적에 맞게 사전 고정
- 무작위 → 시드는 계획의 실험 환경과 `env.json`에. LLM 샘플링처럼 고정 불가한 부분은 시드 칸에 이유

## 검사

보고서 머지 전 확인:

1. 수집 전 계획 커밋이 첫 `raw/` 파일 커밋의 조상
2. `RUN_ID={실행 id}-check ./run.sh verify` 통과
3. `RUN_ID={실행 id}-check ./run.sh analyze` 뒤 `results/`가 커밋본과 같은 바이트, 차트 재현 검사(repo-docs-figures references/validation.md 검사)
4. 보고서의 모든 수치가 `results/summary.json`에 존재
5. 실패, 제외한 실행 전부 데이터 처리 표에
6. `logs/`에 보고한 실행 id의 명령별 로그 존재
