# Datadog 텔레메트리

## 이 출처에 있는 것

Datadog에는 실행 기록, 즉 계획하거나 논의한 것이 아니라 운영 환경에서 실제로 일어난 일이 있다.

- **지표.** 팀이 계측한 카운터, 게이지, 히스토그램. 지표가 *있다는 것* 자체가 누군가 그 숫자를 지켜볼 가치가 있다고 봤다는 증거다.
- **모니터와 알림.** 팀이 누군가를 깨울 만하다고 정한 조건. `rate_limit_hit > 10/min`에 울리는 모니터는 팀이 그 임곗값을 걱정했다는 직접 증거다.
- **대시보드.** 팀이 하위 시스템에서 중요하다고 보는 것을 골라 모은 화면.
- **APM 트레이스와 스팬.** 요청 단위 실행 데이터. "왜 느린가" / "왜 여기 타임아웃이 있나" 질문에 쓴다.
- **로그.** 양이 많은 이벤트 기록. 방어 코드의 계기가 된 오류 조건이 들어 있는 경우가 많다.
- **장애.** 타임라인과 연결된 포스트모템이 있는 공식 장애 기록.
- **노트북.** 팀의 탐색 조사. 가설과 분석이 담긴 경우가 많다.

## 검색하는 법

Datadog MCP를 쓴다. 넓게 시작해 좁힌다.

1. **담당 서비스를 찾는다.**

   ```text
   search_datadog_services (filter by name or team)
   search_datadog_service_dependencies (see upstream/downstream)
   ```

2. **대시보드와 모니터부터 본다.**

   ```text
   search_datadog_dashboards (query: feature name, service name, symbol)
   search_datadog_monitors   (same queries)
   ```

   대시보드나 모니터가 대상을 다루면 그 쿼리와 지켜보는 임곗값을 적는다. "왜 N으로 제한했나?"의 답이 그 임곗값인 경우가 많다.

3. **대상 주변 지표를 본다.**

   ```text
   search_datadog_metrics (by name pattern, e.g., the feature or symbol)
   get_datadog_metric_context (metadata: description, units, tags)
   get_datadog_metric (timeseries; "was there a spike around the PR date?")
   ```

   지표 추이를 대상이 추가·변경된 날짜와 맞춰 보면 강한 뒷받침 증거가 된다. "`payment_timeout` 지표가 2023-11-03에 치솟았고, 재시도 로직은 2023-11-06에 머지됐다."

4. **로그. 쏟아 내지 말고 좁힌다.**

   ```text
   search_datadog_logs (raw log patterns near the target, set use_log_patterns=true)
   analyze_datadog_logs (SQL-style aggregations, only when you need counts)
   ```

   심볼, 오류 문자열, 기능 이름으로 검색한다. **시간 범위를 건 쿼리를 강하게 선호한다**(예: 변경 앞뒤 30일).

5. **APM 스팬과 트레이스.**

   ```text
   aggregate_spans    (stats: "how often does this endpoint fail?")
   search_datadog_spans (inspect individual spans)
   get_datadog_trace  (a specific trace ID)
   ```

   타임아웃, 재시도, 느린 경로, 서비스 사이 동작에 쓸모 있다.

6. **장애.**

   ```text
   search_datadog_incidents (by title, team, date range)
   get_datadog_incident     (full detail for a specific incident)
   ```

   대상이 방어적으로 보이면 그것이 추가된 즈음의 장애를 검색한다. 타임라인에 "X에 대한 방어 코드 추가"가 있는 장애는 직접 증거에 가깝다.

## 좋은 증거의 모습

- 쿼리와 임곗값이 코드가 강제하는 제약과 맞는 모니터(코드는 100으로 제한하고, 모니터는 요청이 분당 100을 넘으면 알림)
- 대상 작성자가 만든 대시보드. 위젯이 코드가 재거나 막는 것과 대응한다
- 코드 머지 직전에 운영 환경에서 치솟고 이후 안정된 지표
- 대상 코드, 같은 심볼, 같은 오류 문자열을 언급하는 장애 기록
- 변경 전 기간에 찍힌, 방어 코드가 막을 특정 오류 패턴을 보여 주는 로그

## 흔한 함정

- **상관은 인과가 아니다.** PR 전에 치솟고 후에 안정된 것은 시사적이지만 결정적이지 않다. 같은 기간에 다른 변경이 머지됐을 수 있다. 이웃 PR을 확인한다.
- **찾은 차트 하나에 해석을 지나치게 맞추기.** 차트는 만든 사람의 관점을 반영한다. "재시도 성공률"이라는 차트는 팀이 재시도 성공에 신경 썼다는 증거지, 특정 코드 줄이 그것 때문에 있다는 증거가 아니다.
- **사라진 텔레메트리.** 지표는 이름이 바뀌거나, 지워지거나, 보존 기간이 짧을 수 있다. 관련 기간의 데이터를 못 찾으면 빈 결과가 아니라 빈 곳이다.
- **데이터 양이 많아서 생기는 잡음.** 로그 검색은 서비스, 태그, 시간 범위로 적극적으로 좁힌다. 원본 로그를 쏟아 내지 말고 `analyze_datadog_logs`로 집계한다.
- **계측됐다고 원인인 것은 아니다.** 지표는 누군가 무언가를 잴 만큼 신경 썼다는 것을 보여 줄 뿐, 코드가 그것 *때문에* 추가됐다는 것을 보여 주지 않는다. 커밋·PR 날짜와 대조한다.

## 돌려줄 것

관련 항목마다:
- 종류(대시보드 / 모니터 / 지표 / 로그 패턴 / 트레이스 / 장애 / 노트북)
- 제목이나 이름
- 링크나 식별자(대시보드 ID, 모니터 ID, 지표 이름, 장애 ID)
- 소유자·작성자와 생성·수정 날짜
- 질문과 관련된 구체적인 조건, 쿼리, 인용(가능하면 원문 그대로)
- 관련성: 대상 코드에 대해 무엇을 시사하는지, 연결이 얼마나 강한지
