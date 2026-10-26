---
name: principle-type-system-discipline
description: "타입을 설계하거나, 함수 시그니처를 리뷰하거나, 정적 타입 언어로 코드를 쓸 때 쓴다. 잘못된 상태를 표현할 수 없게 만들고, 의미 있는 원시값에 브랜드를 붙이고, 외부 데이터는 경계에서 파싱하고, 변형을 빠짐없이 다루고, 정본 스키마에서 타입을 도출한다."
disable-model-invocation: true
user-invocable: false
---

# 타입 시스템 규율

불가능한 상태, 섞인 원시값, 다루지 않은 변형을 컴파일러가 거부하게 만든다. 처리기를 늘리기보다 오류와 특수 사례가 애초에 생기지 않게 정의한다. TypeScript 문법은 `code-style-typescript` 스킬의 TypeScript 전용 절을 본다.

- **의미 있는 원시값에 브랜드를 붙인다.** `UserId`와 `OrderId`는 속은 문자열이지만 서로 바꿔 쓸 수 있으면 안 된다. 각각 고유 타입을 준다. TypeScript라면 브랜드 교차 타입, 다른 언어라면 newtype을 쓴다. 생성할 때 한 번 검증하고 그 뒤로는 타입을 믿는다. 두 인자가 원시 타입은 같지만 뜻이 다르면 브랜드를 붙인다.
- **외부 데이터는 파싱하기 전까지 타입이 없다.** RPC 페이로드, JSON, IPC 메시지, CLI 인자, 설정 파일, 환경 변수, 데이터베이스 행이 그렇다. 모든 경계에 구조 없는 입력을 타입 있는 모델로 바꾸는 파싱 함수를 둔다. 검증을 어디에 둘지는 **principle-boundary-discipline** 원칙 스킬이 정한다.
- **정본 스키마에서 타입을 도출한다.** protocol buffer, OpenAPI 명세, GraphQL 스키마, 데이터베이스 마이그레이션, 디자인 토큰 파일 같은 파일이 모양을 소유한다면 같은 모양의 타입을 따로 손으로 만들지 말고 거기서 도출한다. **principle-encode-lessons-in-structure** 원칙 스킬을 본다.
