# Sentry 오류 이력

## 검색하는 법

Sentry MCP를 쓴다.

1. **방향을 잡는다.** 프로젝트 슬러그와 조직을 모르면:

   ```text
   find_organizations
   find_projects
   ```

2. **대상과 관련된 이슈를 검색한다.**

   ```text
   search_issues (natural language, e.g., "errors in PaymentService timeout", "unhandled exceptions in uploadFile")
   ```

   검색어는 대상이 처리하는 예외 클래스 이름, 함수나 클래스 이름, 확인하는 오류 메시지 문자열, 파일 경로로 만든다.

3. **릴리스와 시간 범위로 좁힌다.**

   ```text
   search_issue_events (filter by release, time, environment, trace ID, tags)
   get_issue_tag_values (for an issue, see distribution across versions, users, environments)
   ```

   의심 가는 이슈는 **처음 관측**과 **마지막 관측**(멈춘 시점이 대상 배포일과 맞는가?), **영향받은 릴리스**(어느 릴리스에서 났고, 어느 릴리스가 고쳤나?), **빈도 추이**(치솟았다가 해결됐나?)를 확인한다.

4. **맥락을 위해 이벤트 전체를 가져온다.**

   ```text
   get_sentry_resource (pass a Sentry URL or type+ID)
   ```

   스택 트레이스가 대상 코드를 지나는가? 태그와 브레드크럼이 대상이 막는 조건과 맞는가?

5. **대상 근처에 나간 릴리스를 확인한다.**

   ```text
   find_releases (around the commit date of the target)
   ```

   릴리스 버전을 PR 머지일과 대조한다.

6. **Seer는 아껴 쓴다.**

   ```text
   analyze_issue_with_seer
   ```

   Seer의 AI 근본 원인 분석은 가설을 내놓는 도구일 뿐이다. 권위 있는 결론이 아니라 추론으로 다룬다. 1차 증거는 실제 이벤트와 스택 트레이스다.

## 돌려줄 것

관련 이슈마다:
- 이슈 ID와 제목
- 프로젝트와 조직
- 처음·마지막 관측 시각
- 이벤트 수(알면 샘플링 비율도)
- 영향받은 릴리스
- 대상과의 관련성을 보여 주는 대표 스택 트레이스 조각(요약이 아니라 원문 발췌)
- 처음·마지막 관측 시각과 대상 배포일의 상관
- 이슈 링크
- 작성자 댓글이나 해결 메모
