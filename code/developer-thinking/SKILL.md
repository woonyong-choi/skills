---
name: developer-thinking
description: "IT 제품을 설계·구현·수정·검토·배포할 때 적용."
---

# Developer Thinking

- 우선순위: 해당 주제의 사용자 지시 → 저장소 규칙 → 이 스킬. 중복 규칙은 머리에 연결한 정본 스킬 적용
- 범위: 개발 실행 순서·규칙 선택·재개 위치. 개인 업무·커리어 제외

## 실행 순서

1. 연결: 필수 상위 지침 확인 → git-issue의 과업 연결·복구로 요청·작업본 대조
2. 결정: repo-docs-design으로 요구·보존·미확정 선택 판정
3. 실행: code-style 본문의 조건별 읽기로 해당 절·언어·시각 규칙 적용
4. 검증: code-style의 검증으로 요청한 산출물과 근거 대조
5. 기록: git-issue의 checkpoint·상태·완료 규칙 적용

- 요청한 산출물·쓰기 범위 준수. 읽기 전용은 stdout, 임시 파일 금지. 유효한 결정·결과 재사용
- 실패·새 사실은 영향 단계로 복귀. 하위 스킬에서 루트 전체 재호출 금지

## 필요한 규칙

- 요청·변경 경로로 분류 선택. 신규 제품은 전체 영역 적용 여부 확인
- `spec`: 스펙·규모·보장 → repo-docs-design의 requirements
- `choice`: 기술·구조·정책 선택 → requirements와 repo-docs-design의 선택 절
- `infrastructure`: 구매·구축·인프라 → requirements·설계 선택·infrastructure와 code-style의 operations
- `data`: 데이터·공유 상태·비동기 → code-style의 data-and-concurrency
- `resources`: 성능·자원·캐시·큐 → 설계의 requirements와 code-style의 resources
- `interface`: 화면 상태·표현 → code-style의 interfaces. 시각 변경은 design-tokens, CSS 변경은 code-style-css 추가
- `external`: API·외부 입력·권한 → code-style의 operations·interfaces
- `operations`: 신뢰 경계·외부 의존·배포·복구 → code-style의 operations
- `review`: 주장·결과 대조 → code-style의 검증
- `product`: 신규 제품·전체 설계 → 위 영역 합집합
- 문서·Git·리팩터링·언어 → 해당 작업의 기존 소유 스킬

- 기술 참조는 소유 스킬의 `references/{이름}.md`. 제안·구현 전 선택한 본문·절 끝까지 필수 확인. 제목·요약·읽음 표시로 대체 금지
- 조회: `python3 <이 스킬 폴더>/scripts/read_rules.py <분류...>`. Python 3.9+·표준 라이브러리. stdout 원문은 선행 규칙부터 중복 제거. 성공 0·읽기 실패 1·입력 오류 2. 쓰기·네트워크 없음
- 기반은 선행 조건, 조건부는 해당 절만 조회. 같은 문맥·원문과 적용 단계 재사용. 범위 변경은 재선택, 압축·재개는 필수 원문 재조회
- 실행 불가 시 원문 직접 조회. 필수 지침·원문 미조회/접근 실패는 제외 아닌 영향 작업 보류
- 목록 밖 도메인·안전 계약은 공식 기준 확인. 읽음·형식 통과≠이해·실제 준수
