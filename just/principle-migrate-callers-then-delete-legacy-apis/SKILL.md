---
name: principle-migrate-callers-then-delete-legacy-apis
description: "옛 호출부가 아직 남아 있는 상태에서 새 내부 API를 도입할 때 쓴다. 호환 계층을 남기지 말고 같은 웨이브에서 호출부를 옮기고 옛 API를 삭제한다."
disable-model-invocation: true
user-invocable: false
---

# 호출부 옮긴 뒤 레거시 API 삭제

옛 호출부가 남아 있는 상태에서 새 내부 API를 도입하면 호환 계층을 남기지 않는다. 같은 웨이브에서 호출부를 옮기고 옛 API를 삭제한다.

- 테스트는 새 계약을 확인하도록 고치고, 리팩터링 전 구현 세부만 지키던 테스트는 삭제한다.

**적용 조건.**

- 하위 호환에 기대는 외부 사용자가 없다.
- 프로젝트가 여러 곳을 한꺼번에 맞춰 고치는 호환성 깨짐 변경을 감당할 수 있다.
- 새 API가 단순화나 리팩터링 작업의 일부다.
