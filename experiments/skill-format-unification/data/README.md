# 데이터

## 출처

| 항목 | 값 |
|---|---|
| 수집 방법 | 스킬 스냅숏은 작업 폴더에서 묶음. 트리거 선택과 문서 작성은 새 에이전트가 카탈로그와 스킬 파일만 보고 수행 |
| 수집 기간 | 2026-09-30~2026-09-30 |
| 개수 | 스킬 스냅숏 5개, 트리거 실행 4개(요청 30개씩), 작성 산출물 8벌(4라운드 × 2명), 누락 대조 발견 26건, 재대조 발견 10건 |
| 표본 여부 | 전수(스킬 22개 전부, 요청 30개 전부) |
| 라벨 | `expected.json`: 요청별 기대 스킬, 스킬 설계자가 작성. `audit-findings.jsonl`: 대조 에이전트 보고를 설계자가 분류 |
| 알려진 문제 | 에이전트 산출물은 샘플링이라 재실행 시 값이 다름. `skills-r2.tar.gz`는 r3 상태에서 끝 변환 줄을 빼서 복원한 것 |
| 개인정보 | 공개 점검에서 합성 사실과 작성 표본의 프로젝트명·계정·저작권자·주소를 범용 예시로 치환 |
| 라이선스 | 저장소 라이선스와 동일 |

## 파일

| 파일 | 내용 | 만드는 스크립트 |
|---|---|---|
| `raw/skills-{before,r1,r2,r3,after}.tar.gz` | 단계별 스킬 폴더 스냅숏 | `scripts/01-collect.sh` |
| `raw/prompts.md`, `raw/expected.json` | 트리거 요청 30개와 기대 스킬 | `scripts/01-collect.sh` |
| `raw/catalog-{before,r1,after}.md` | 이름과 description만 모은 카탈로그 | `scripts/01-collect.sh` |
| `raw/trigger-{버전}-{번호}.json` | 에이전트가 고른 스킬 | `scripts/01-collect.sh` |
| `raw/facts.md` | 작성 에이전트에 준 사실 | `scripts/01-collect.sh` |
| `raw/writers/{라운드}-{번호}/` | 작성 에이전트 산출 문서와 `READ_LOG.md` | `scripts/01-collect.sh` |
| `raw/audit-findings.jsonl` | 옛 스킬 대비 새 스킬 누락 대조 결과 | 손으로 기록 |
| `raw/audit-findings-2.jsonl` | 수정 뒤 재대조에서 찾은 새 충돌 | 손으로 기록 |
| `processed/skill_tokens.csv` | 버전, 스킬별 바이트와 토큰 | `scripts/02-process.py` |
| `processed/scenario_load.csv` | 요청 시나리오별 로드 스킬과 토큰 | `scripts/02-process.py` |
| `processed/style_check.csv` | 버전별 형식 검사 위반 수 | `scripts/02-process.py` |
| `processed/trigger.csv` | 요청별 적중, 누락, 과선택 | `scripts/02-process.py` |
| `processed/determinism.csv` | 라운드, 파일별 줄 차이 | `scripts/02-process.py` |
| `processed/audit.csv` | 누락 대조 결과 표(`pass` 1, 2) | `scripts/02-process.py` |

## 필드

### `raw/audit-findings.jsonl`, `raw/audit-findings-2.jsonl`

| 필드 | 타입 | 단위 | 제약 | 뜻 | 예 |
|---|---|---|---|---|---|
| `id` | string | 없음 | 고유 | 발견 번호. A: repo-docs 계열, B: 기록 스킬, C: 코드와 git 스킬, D: 재대조 | `A1` |
| `group` | string | 없음 | `repo-docs`, `records`, `code`, `reaudit` | 대조 단위 | `code` |
| `file` | string | 없음 | 필수 | 해당 스킬 | `code-style` |
| `kind` | string | 없음 | `loss`, `meaning`, `contradiction`, `wording`, `preexisting` | 소실, 뜻 변경, 새 충돌, 표현, 옛 버전부터 있던 문제 | `loss` |
| `summary` | string | 없음 | 필수 | 발견 내용 | `'레벨은 code-style 로그 레벨 표' 소실` |
| `fix` | string | 없음 | 필수 | 수정 내용 | `복원` |
| `fixed` | integer | 없음 | 0, 1 | 수정 여부 | `1` |

### `processed/scenario_load.csv`

| 필드 | 타입 | 단위 | 제약 | 뜻 | 예 |
|---|---|---|---|---|---|
| `scenario` | string | 없음 | 고유 | 시나리오 식별자 | `s01` |
| `request` | string | 없음 | 필수 | 요청 | `README 작성(그림 없음)` |
| `version` | string | 없음 | `before`, `after` | 스킬 버전 | `after` |
| `skills` | string | 없음 | 공백 구분 | 불러오는 스킬 | `repo-docs repo-docs-readme` |
| `o200k` | integer | 토큰 | 0 이상 | 불러오는 SKILL.md 전체의 o200k 토큰 합 | `7894` |
| `claude_legacy` | integer | 토큰 | 0 이상 | 같은 파일의 Claude 구 토크나이저 토큰 합 | `11962` |
| `catalog_o200k` | integer | 토큰 | 0 이상 | 항상 올라가는 이름과 description 합 | `1248` |
| `catalog_claude_legacy` | integer | 토큰 | 0 이상 | 같은 카탈로그의 Claude 구 토크나이저 토큰 합 | `2012` |

### `processed/determinism.csv`

| 필드 | 타입 | 단위 | 제약 | 뜻 | 예 |
|---|---|---|---|---|---|
| `round` | string | 없음 | `r1`~`r4` | 스킬 버전 라운드 | `r3` |
| `file` | string | 없음 | 필수 | 비교한 문서 | `docs/architecture.md` |
| `nonblank_lines` | integer | 줄 | 0 이상 | 첫 작성자 문서의 빈 줄 아닌 줄 수 | `45` |
| `diff_lines` | integer | 줄 | 0 이상 | `diff`에서 첫 작성자 쪽 다른 줄 수 | `6` |
| `same_headings` | integer | 없음 | 0, 1 | 제목 줄 목록 일치 | `1` |
| `same_file_set` | integer | 없음 | 0, 1 | 두 작성자의 파일 목록 일치 | `1` |

- 모든 행 필수 필드 규칙(`run_id`, `trial_id`, `condition`, `ts_utc`) 미적용: 에이전트 산출물이 문서 파일이라 행 단위 기록 없음
- 표: CSV(머리 행, UTF-8, RFC 4180)

## 공개용 식별 정보 정리

2026-10-04 공개 점검에서 `raw/facts.md`와 `raw/writers/`의 개인 식별 정보를 일관된 예시로 치환했다. 이 파일들은 최초 수집 바이트와 다르다. 스킬 스냅숏과 측정 결과는 그대로 보존하고, `SHA256SUMS`는 현재 파일 바이트로 갱신했다. 작성 표본 쌍의 줄 수와 줄 차이, 제목 일치 여부는 치환 전후가 같다.
