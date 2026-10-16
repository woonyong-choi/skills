---
name: code-style-typescript
description: "JavaScript·TypeScript 코드를 작성·검토하거나 ESLint·Prettier·node:test·tsc 설정을 고칠 때 사용."
---

# Code Style: TypeScript

- 우선순위: 사용자 지시 → 저장소 규칙 → 이 스킬. 범위 밖은 명시한 소유 스킬 적용
- 기반: code-style 먼저 적용. 이 스킬 범위: code-style이 언어에 맡긴 부분의 JavaScript·TypeScript 규칙. 그 밖에서 code-style과 다르면 code-style 우선
- 필요할 때만 읽기: CSS 문자열·인라인 style 작성 → code-style-css; SVG 속성 값 작성 → design-tokens; 파일 이름 결정 → folder-naming

적용 범위:

- `.ts`·`.tsx` → 모든 절
- `.js`·`.mjs`·`.cjs`·`.jsx` → TypeScript 전용 절 제외, 나머지 공통 절

## 이름

- 대소문자 표기: 변수·함수 camelCase, 클래스 PascalCase, 모듈 상수 UPPER_SNAKE_CASE. 포맷: Prettier
- 파일: 소문자 kebab-case `.js`·`.ts` (folder-naming과 같은 기준)

대상 → 규칙 → 예:

- 접근자 → 필드나 `get` 접근자. 계산 없는 `getX()`·`setX()` 메서드 금지 → `session.name`, `get isReady()`
- 생성 → `constructor`. 다른 생성 방법은 `static from*`·`create*` 팩토리 → `Config.fromFile(path)`, `createPlayer(root)`
- 변환 → `to*` 새 값, `as*` 같은 값의 다른 표현 → `toJson()`, `asArray()`
- 반복자 → 제너레이터 `*iter*`나 `[Symbol.iterator]` → `*iterSessions()`
- 상수 → 모듈 최상위의 바뀌지 않는 값만 UPPER_SNAKE_CASE. 객체 상수는 `Object.freeze` → `MAX_RETRY`, `DEFAULTS`
- 약어 → 한 단어처럼 camelCase·PascalCase → `httpClient`, `parseUrl`, `HttpError`
- 비공개 → 모듈: export 금지. 클래스: `#` 필드·메서드. `_` 접두사 금지 → `#cache`
- 단위 → 시간 타입이 없어 접미사 필수 → `timeoutMs`, `sizeBytes`

## 선언 순서

모듈:

- ES 모듈(`import`·`export`)만. `package.json`에 `"type": "module"`. CommonJS `require` 금지(외부 도구 설정 파일 제외)
- 일반 모듈은 named export. 도구가 설정 파일에 default export를 요구하면 그 파일에서 default export 사용
- import 순서: `node:` 내장 → 외부 패키지 → 상대 경로, 그룹 사이 빈 줄. 내장 모듈은 `node:` 접두사 필수
- 와일드카드 `import *` 금지(외부 패키지가 그 방식만 제공할 때 제외)
- 순환 import 금지

파일:

1. 파일 설명 주석
2. import
3. 모듈 상수
4. 클래스. export 먼저
5. 함수. export → 비공개, 비공개는 처음 호출되는 순서대로
6. 진입점 실행 코드 (실행 파일만, 파일 끝)

클래스:

1. `static` 상수·필드
2. 공개 필드 → `#` 비공개 필드
3. `constructor`
4. 이후는 code-style 타입 순서의 5~10 (팩토리 → 접근자 → 생명주기 → 공개 → 비공개 헬퍼 → 검증)

- 함수 선언문은 호출 뒤 선언 허용, `const` 화살표 함수는 사용 전 선언 필수
- 모듈 최상위 함수는 함수 선언문. 화살표 함수는 콜백과 한 줄 식에만

## 오류와 로그

경우 → 처리:

- 일어날 수 있는 실패 → `Error` 하위 클래스 throw. async 함수는 reject
- 코드에 버그가 없으면 일어날 수 없는 경우 → `throw new Error('<성립해야 하는 이유>')`
- 테스트 → `node:assert/strict` 단언

- 문자열·객체 throw 금지. 항상 `Error` 인스턴스
- 원인 보존: `throw new ConfigError('failed to read config', { cause: error })`
- 라이브러리 모듈의 오류 클래스: `class {대상}Error extends Error`, `this.name` 지정
- Promise: 반환하거나 `await`. 떠 있는 Promise 금지. 최상위는 top-level `await`
- 오류·로그 메시지는 소문자로 시작, 마침표 없음: `failed to read config`

로그:

- 라이브러리 모듈: `console` 금지. 오류는 throw로 전달
- CLI 진입점 메서드: 진단 `console.error`, 결과 `console.log`. 출력 경계: (code-style 오류와 로그)
- 브라우저 코드: 배포 코드에 `console.log` 금지
- 저장소에 정한 로그 라이브러리가 있으면 그것 우선

## 공개 범위와 주석

- 문서 주석: 필요할 때만 JSDoc `/** */`. 실패 조건 `@throws`, 타입 `@param`·`@returns`
- checkJs 사용 저장소나 공개 JSDoc 타입 변경: `// @ts-check`와 `tsc --noEmit --checkJs`

## 테스트

- `node:test`와 `node:assert/strict`. 저장소에 정한 테스트 도구가 있으면 그것 우선
- 위치: `test/` 폴더, 파일은 `{모듈}.test.js`·`{모듈}.test.ts`
- 이름: code-style 형식, 대상은 함수 이름 그대로: `parseFlow_empty_input_throws`
- 외부 명령·브라우저가 없으면 `{ skip: '<이유>' }`와 미검증 범위 보고. 변경 요구사항의 필수 검증이면 완료 판정 보류
- 브라우저 동작: Playwright(`playwright-core`)로 실제 페이지를 열어 확인

## 린트 설정

ESLint·Prettier 설정 생성·변경·감사 전 [lint.md](references/lint.md) 필수 확인

- ESLint가 못 잡는 것은 직접 확인: 이름, 비교 순서, `&&`·`||` 개수와 섞기, 선언 순서, bool 매개변수 수

## 검사 명령

경고도 실패 처리

- 함수 인자·중첩 검사 도구: 실제 구문 경계 처리 필수. 정규식 탐색만이면 미검사 범위를 결과에 명시

```
npx prettier --check .
npx eslint --max-warnings 0 .
node --test
```

- 실행 조건: Node.js 18+와 개발 의존성 `npm install --save-dev prettier eslint @eslint/js globals eslint-plugin-sonarjs`

## TypeScript 전용

- 바탕 원칙: principle-type-system-discipline, principle-boundary-discipline. 규칙별 코드 예: [types.md](references/types.md)
- 타입 표기: JSDoc 타입 대신 TypeScript 타입. JSDoc은 실패 조건 `@throws` 같은 타입 밖 설명만

규칙 → 내용:

- 판별 유니온 → 변형은 `kind` 리터럴 판별자로 모델링. 불가능한 상태를 표현할 수 없는 모양, 선택적 필드 묶음 금지
- 브랜드 타입 → 원시 타입에 `& { readonly __brand: 'X' }`로 구분. 경계에서 한 번 검증
- 구성적 모델링 → 잘못된 값을 만들 수 없는 모양. 비어 있지 않음 `[T, ...T[]]`, 짝수 길이 `[T, T][]`, 범위 `start`와 `duration`. 런타임 방어 코드로 대신하기 금지
- 모든 입력을 처리하는(total) 가장 단순한 타입 → 모든 연산이 모든 입력을 처리하는 동안 `T[]` 유지. 느슨한 타입이 `!`·캐스트·"일어날 리 없음" throw를 강요하는 곳에서만 `NonEmpty<T>`로 강화
- `any`보다 `unknown` → 외부 데이터는 `unknown`, 쓰기 전에 좁히기
- 가드보다 스키마 → 속성별 타입 가드 작성 전 저장소의 런타임 스키마 라이브러리 사용, `z.infer`처럼 스키마에서 타입 추론. 가드 하나를 위한 새 스키마 의존성 추가 금지
- `as` 캐스트 금지 → 검증한 뒤에만 캐스트. 기존 `as` 제거는 추론 실패 원인(판별자 없음, 지나치게 넓은 원본 타입, 타입 없는 경계)부터 확인
- 좁히기 위계 → 판별자 switch > `in` 연산자 > `typeof`·`instanceof` > 사용자 정의 타입 가드 > `as`
- 타입 가드 → 주장을 실제로 확인하는 가드만. 이름 규칙은 code-style 이름 절의 bool 반환 함수
- 빠짐없음 검사 → default 분기에 `const unreachable: never = x;`. 새 변형 추가 시 컴파일 오류
- `as`보다 `satisfies` → 리터럴 타입을 넓히지 않는 검증
- 경계 검증 → 들어오는 곳에서 이름 붙은 도메인 타입으로 파싱. `Record<string, unknown>`(어떤 표기든)은 파싱 지점 밖으로 전달 금지. 전송 형식은 `ignoreUnknownFields`, 저장된 JSON은 버전 정보와 파싱 실패 처리
- 스키마에서 도출한 타입 → 새 인터페이스 선언 전 `Pick`·`Omit`·`Parameters`·`ReturnType`·`Awaited`·`typeof`
- 객체 인자 → 위치 인자 대신 객체로 인자 순서 설명. 핫 패스(프레임마다 렌더, 토크나이저, 파서) 제외
- 진짜 테스트 → 로컬에서 돌릴 수 있는 것은 목 금지. 누수·해제 검사가 있는 실제 테스트 도구, UI는 실행 중인 빌드에서 확인

검사 명령 추가:

```sh
npx tsc --noEmit
```

- 실행 조건: 개발 의존성 `typescript`와 저장소 `tsconfig.json`
