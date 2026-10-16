# Databricks 분석 테이블과 시스템 테이블

> 예시: 이 플레이북의 테이블 이름(`your_warehouse.events.*`, `<your_analytics_db>.<schema>.*`, `usage_event`, `raw_model_event` 같은 것)과 열 관례는 한 회사의 스키마를 본뜬 예시다. 실제 이름과 열은 회사마다 다르므로 `SHOW TABLES`와 `DESCRIBE TABLE`로 먼저 확인한다. `system.*` 시스템 테이블만 Databricks 공통이다.

## 이 출처에 있는 것

Databricks는 제품 분석, 데이터 파이프라인, 웨어하우스 텔레메트리 계층이다. Datadog을 보완한다. Datadog은 *인프라와 실행 환경*을 보고, Databricks는 *제품과 데이터*를 본다(사용자가 무엇을 했는지, 어떤 실험이 돌았는지, 기능 사용량이 어떻게 변했는지, 임곗값 상수가 어디서 왔는지).

- **제품 분석 이벤트.** `your_warehouse.events.analytics_track_event`(원본)와 `<your_analytics_db>.<schema>.<table>`의 이벤트별 타입 지정·중복 제거 dbt 모델. 사용자 행동: 기능 호출, 클릭, 수락·거절, 제출, 클라이언트가 보고한 오류.
- **사용량·과금 이벤트.** `your_warehouse.events.usage_event` / `<your_analytics_db>.<schema>.stg_usage_events`, `your_warehouse.events.raw_model_event` / `<your_analytics_db>.<schema>.stg_raw_model_events`. 비용이나 양에 따른 결정에 쓴다.
- **실험·기능 플래그 데이터.** 노출 테이블과 결과 테이블. **스키마는 회사마다 다르다.** 이름을 가정하기 전에 `SHOW TABLES`로 확인한다.
- **시스템 테이블.** `system.query.history`, `system.compute.warehouses`, `system.billing.*`, `system.access.audit`. "이 쿼리가 비쌌나?", "누가 얼마나 자주 돌렸나?", "웨어하우스 부하가 언제 치솟았나?"에 답한다.
- **dbt 계보.** `<your_analytics_db>.<schema>`의 모델은 어떤 파이프라인이 테이블·필드에 기대는지 보여 준다. 상위 테이블이 바뀌어서 그것을 쓰는 코드가 바뀌는 일이 잦다.
- **Databricks 노트북.** 엔지니어가 코드 변경 전에 쓴 탐색 분석. **SQL MCP로는 조회할 수 없다.** 근거가 노트북에 있다고 의심되면 빈 곳으로 적는다.

## 검색하는 법

Databricks SQL MCP를 쓴다. 주 도구는 `execute_sql_read_only`다. `statement_id`를 돌려주면 다시 돌리지 말고 `poll_sql_result`로 결과를 기다린다.

**조회 전에 방향을 잡는다.** 스키마는 회사마다 다르다. 테이블 이름을 믿기 전에 확인한다.

```sql
SHOW TABLES IN <your_analytics_db>.<schema> LIKE '*<keyword>*';
DESCRIBE TABLE <your_analytics_db>.<schema>.stg_<event>;
```

**모든 쿼리에 시간 범위를 건다.** 이 테이블들은 거대해서 범위 없는 스캔은 시간 초과가 난다. `_timestamp`(이벤트)나 `start_time`(`system.query.history`)으로 배포일을 감싸는 범위를 건다. 보통 앞뒤 30일 정도이고, 강한 이유가 있을 때만 넓힌다.

**원본 테이블보다 타입 지정 dbt 모델을 쓴다.** `<your_analytics_db>.<schema>.<table>`은 중복이 제거되고, 타입이 지정되고, liquid clustering이 적용돼 있다. `your_warehouse.events.analytics_track_event`에는 중복이 있고 `properties_json`은 타입이 없다. 모델 이름 패턴은 `stg_<source>_<event_name_with_underscores>`이고 `<source>`는 `app`, `backend`, `website`, `cli` 중 하나다. 패턴만으로 안 풀리면 `SHOW TABLES`로 정확한 모델 이름을 확인한다. 아직 dbt 모델이 없거나 dbt 갱신 지연 안쪽의 이벤트가 필요할 때만 원본 테이블로 내려간다.

**타입 지정 dbt 모델의 열 관례**(알아 두면 `DESCRIBE`를 따로 돌리지 않아도 된다):

- `_timestamp`, `_id`, `_auth_id`, `_request_id`, `event_name`. 모든 모델에 있음
- `properties_<name>`. 타입이 지정되고 밑줄로 바꾼 이벤트 속성(`properties_entrypoint`, `properties_size_bytes`, …)
- `context_team_id`, `context_client_version`, `context_country`, `context_client_os`. 미리 뽑아 둔 클라이언트 맥락

### 잘 통하는 조사 패턴

대상에 맞는 테이블과 열 조합을 고른다.

1. **이벤트 사용량 추이.** PR 머지 앞뒤 30일 동안 관련 `stg_*` 모델의 일별 개수. 머지 하루 이틀 안에 0에서 꾸준한 양으로 계단처럼 오르면 그 PR이 기능을 출시했다는 강한 정황 증거다. 0으로 줄어들면 폐기나 삭제를 시사한다.
2. **방어 코드의 기원.** PR *이전* 14일 동안 관련 `properties_<name>` 열의 분포(중앙값 / p99 / 최댓값). p99가 대상의 임곗값 상수와 같으면 그 숫자를 데이터에서 골랐음을 시사한다.
3. **실험·기능 플래그 조회.** `SHOW TABLES ... LIKE '*experiment*'`로 노출 테이블을 찾고, PR 날짜 근처에서 관련 플래그 키의 변형별 노출 수를 뽑는다.
4. **마이그레이션, 백필, 성능 재작성의 쿼리 이력 증거.** `system.query.history`를 `statement_text ILIKE '%<table_or_symbol>%'`와 좁은 `start_time` 범위로 거르면 변경의 계기가 됐을 법한 비싼 쿼리가 나온다(`total_duration_ms`로 정렬하거나 `SUM(read_bytes)`, `COUNT(*)`로 집계).
5. **dbt 계보.** 대상이 `<your_analytics_db>.<schema>` 모델을 읽거나 쓰면, 그 모델 자체의 git 이력(이 저장소 안)에 근거가 있는 경우가 많다. 직접 따라가지 말고 그 단서를 git 조사자에게 넘긴다.

## 좋은 증거의 모습

위 패턴 외에:

- 방어 코드 PR 이후 며칠 만에 오류 분류 이벤트 수가 거의 0으로 떨어진다. PR이 그 오류 종류를 해결했음을 시사한다
- 노출 테이블 행에 대상의 기능 플래그 키가 PR 배포일 즈음 "shipped" / "concluded" 결정과 함께 있다

## 흔한 함정

- **계측됐다고 원인인 것은 아니다.** 이벤트가 있다는 것은 누군가 기록할 만큼 신경 썼다는 뜻이지, 대상 코드가 그것 *때문에* 있다는 뜻은 아니다. 인과를 주장하기 전에 git 조사자의 PR·커밋 인용과 짝짓는다.
- **조용한 계측 변경.** 이벤트 양이 계단처럼 오른 것은 사용자 행동이 바뀐 것이 아니라 새 이벤트 기록이 시작된 것일 수 있다. 증가를 기능 출시 신호로 읽기 전에 같은 기간의 계측 PR을 확인한다.
- **스키마 변화.** 이벤트 속성은 바뀐다. 지금 타입 지정 dbt 모델에 있는 열이 대상 작성 당시에는 없었을 수 있다. 오래된 데이터는 그 속성을 원본 `properties_json` 안에만 가지고 있을 수 있다.
- **dbt 갱신 지연.** `<your_analytics_db>.<schema>.*`는 일정에 따라(보통 매시간이나 매일) 다시 만들어진다. 최근 몇 시간의 이벤트는 `your_warehouse.events.*`로 내려가 `_id`로 중복을 제거한다.
- **회사마다 다른 테이블.** 실험, 기능 플래그, 과금, 사용량 테이블은 제각각이다. 존재를 확인하지 않은 테이블의 결과를 보고하는 것은 전형적인 실패다. 먼저 `SHOW TABLES` / `DESCRIBE TABLE`로 확인한다.
- **보존 기간 경계.** 관련 기간이 테이블 보존 기간이나 dbt 모델 생성일보다 앞서면 빈 결과가 아니라 *빈 곳*이다. 종합자가 "결과 없음"을 "활동 없음"으로 읽지 않도록 명시한다.
- **노트북은 조회할 수 없다.** SQL MCP는 Databricks 노트북을 보지 못한다. 근거가 노트북에 있다고 의심되면 빈 곳으로 돌려준다.

## 돌려줄 것

관련 결과마다:
- 종류(제품 이벤트 / 실험 노출 / 사용량·과금 이벤트 / 시스템 테이블 행 / dbt 모델)
- 전체 이름의 테이블과 실행한 정확한 쿼리
- 조회한 시간 범위
- 간단한 숫자 요약(개수, 백분위, 처음·마지막 관측 시각). **원본 행을 쏟아 내지 않는다.**
- 대상 배포일과의 시간 상관(예: "첫 행 2024-08-15, PR #49074 머지 2024-08-14")
- 관련성과 강도: 직접 / 정황 / 약함
