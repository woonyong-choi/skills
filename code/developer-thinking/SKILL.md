---
name: developer-thinking
description: "IT 제품을 설계·구현·수정·검토·배포할 때 적용."
---

# Developer Thinking

- 우선순위: 해당 주제의 사용자 지시 → 저장소 규칙 → 이 스킬. 중복 규칙은 머리에 연결한 정본 스킬 적용
- 범위: 개발 실행 순서·규칙 선택·재개 위치. 개인 업무·커리어 제외

## 실행 순서

1. 연결: git-issue의 과업 연결·복구로 현재 요청과 실제 작업본 확인
2. 결정: repo-docs-design으로 요구·보존·미확정 선택 판정
3. 실행: 선택 범위의 code-style·언어·시각 규칙 적용
4. 검증: code-style의 검증으로 요청한 산출물과 근거 대조
5. 기록: git-issue의 checkpoint·상태·완료 규칙 적용

- 요청한 산출물까지만 실행. 유효한 결정·결과 재사용
- 실패·새 사실은 영향 단계로 복귀. 하위 스킬에서 루트 전체 재호출 금지

## 필요한 규칙

- 요청과 실제 변경 경로로 아래 분류 선택. 신규 제품은 전체 영역의 적용 여부부터 확인
- `spec`: 스펙·규모·보장 → repo-docs-design의 requirements
- `choice`: 기술·구조·정책 선택 → repo-docs-design 본문과 requirements
- `infrastructure`: 구매·구축·인프라 → 설계 선택·requirements·infrastructure와 code-style의 operations
- `data`: 데이터·공유 상태·비동기 → code-style의 data-and-concurrency
- `resources`: 성능·자원·캐시·큐 → 설계의 requirements와 code-style의 resources
- `interface`: 화면·API → code-style의 interfaces. 시각 변경은 design-tokens, CSS 변경은 code-style-css 추가
- `external`: 외부 입력·권한별 API → code-style의 interfaces·operations
- `operations`: 신뢰 경계·외부 의존·배포·복구 → code-style의 operations
- `review`: 주장·결과 대조 → code-style의 검증
- `product`: 신규 제품·전체 설계 → 위 영역 합집합
- 문서·Git·리팩터링·언어 → 해당 작업의 기존 소유 스킬

- 기술 참조는 소유 스킬의 `references/{이름}.md`. 제안·구현 전 선택한 본문·절 끝까지 필수 확인. 제목·요약·읽음 표시로 대체 금지
- 조회: `python3 <이 스킬 폴더>/scripts/read_rules.py <분류...>`. Python 3.9 이상·표준 라이브러리. stdout에 선행 규칙부터 중복 없는 원문. 성공 0·읽기 실패 1·입력 오류 2. 쓰기·네트워크 없음
- 기반은 선행 조건, 조건부 참조는 해당 절만 조회. 이미 적용한 단계 재실행 금지. 같은 문맥·원문은 재사용, 범위 변경은 재선택, 압축·재개는 필요한 원문 재조회
- 실행 불가 시 선택 원문 직접 조회. 필수 원문 접근 실패·적용 여부 미확인은 제외로 처리하지 않고 영향 작업 보류
- 목록 밖 도메인·안전 계약은 해당 공식 기준 확인. 읽음·형식 통과와 이해·실제 준수 구분
