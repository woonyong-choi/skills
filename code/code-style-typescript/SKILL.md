---
name: code-style-typescript
description: "JavaScript와 TypeScript 코드를 쓰거나 검토할 때, ESLint, Prettier, node:test, tsc 설정을 고칠 때 쓴다."
---

# TypeScript 코드 스타일

[code-style](../code-style/SKILL.md)을 먼저 적용하고, 이 스킬은 code-style이 언어에 맡긴 항목의 JavaScript와 TypeScript 규칙만 정한다. 그 밖에서 code-style과 다르면 code-style을 따른다.

## 적용 범위

- `.ts`, `.tsx` 파일에는 모든 절을 적용한다.
- `.js`, `.mjs`, `.cjs`, `.jsx` 파일에는 TypeScript 전용 절을 빼고 나머지 공통 절을 적용한다.

## 이름

- 변수와 함수는 camelCase, 클래스는 PascalCase, 모듈 상수는 UPPER_SNAKE_CASE로 쓰고 포맷은 Prettier로 맞춘다.
- 파일 이름은 소문자 kebab-case `.js`, `.ts`로 쓴다. [folder-naming](../folder-naming/SKILL.md)과 같은 기준이다.

| 대상 | 규칙 | 예 |
|---|---|---|
| 접근자 | 필드나 `get` 접근자를 쓴다. 계산 없는 `getX()`, `setX()` 메서드를 쓰지 않는다 | `session.name`, `get isReady()` |
| 생성 | `constructor`를 쓴다. 다른 생성 방법은 `static from*`이나 `create*` 팩토리로 둔다 | `Config.fromFile(path)`, `createPlayer(root)` |
| 변환 | 새 값은 `to*`, 같은 값의 다른 표현은 `as*` | `toJson()`, `asArray()` |
| 반복자 | 제너레이터 `*iter*`나 `[Symbol.iterator]` | `*iterSessions()` |
| 상수 | 모듈 최상위의 바뀌지 않는 값만 UPPER_SNAKE_CASE로 쓴다. 객체 상수는 `Object.freeze`로 얼린다 | `MAX_RETRY`, `DEFAULTS` |
| 약어 | 한 단어처럼 camelCase나 PascalCase로 쓴다 | `httpClient`, `parseUrl`, `HttpError` |
| 비공개 | 모듈에서는 export하지 않고, 클래스에서는 `#` 필드와 메서드를 쓴다. `_` 접두사를 쓰지 않는다 | `#cache` |
| 단위 | 시간 타입이 없으므로 반드시 접미사를 붙인다 | `timeoutMs`, `sizeBytes` |

## 선언 순서

모듈은 다음 규칙을 따른다.

- ES 모듈(`import`, `export`)만 쓰고 `package.json`에 `"type": "module"`을 둔다. CommonJS `require`를 쓰지 않는다. 외부 도구의 설정 파일은 예외다.
- 일반 모듈은 named export를 쓴다. 도구가 설정 파일에 default export를 요구하면 그 파일에서만 default export를 쓴다.
- import는 `node:` 내장 모듈, 외부 패키지, 상대 경로 순서로 묶고 그룹 사이에 빈 줄을 둔다. 내장 모듈에는 반드시 `node:` 접두사를 붙인다.
- 와일드카드 `import *`를 쓰지 않는다. 외부 패키지가 그 방식만 제공하면 예외다.
- 순환 import를 만들지 않는다.

파일은 다음 순서로 쓴다.

1. 라이선스 머리말과 공개 모듈의 문서 주석
2. import
3. 모듈 상수
4. 클래스. export하는 클래스를 먼저 둔다.
5. 함수. export하는 함수, 비공개 함수 순서로 두고, 비공개 함수는 처음 호출되는 순서로 둔다.
6. 진입점 실행 코드(실행 파일만, 파일 끝)

클래스는 다음 순서로 쓴다.

1. `static` 상수와 필드
2. 공개 필드, `#` 비공개 필드 순서
3. `constructor`
4. 이후는 code-style 타입 순서의 5~10번(팩토리, 접근자, 생명주기, 공개 메서드, 비공개 헬퍼, 검증)을 따른다.

- 함수 선언문은 호출보다 뒤에 선언해도 된다. `const` 화살표 함수는 반드시 쓰기 전에 선언한다.
- 모듈 최상위 함수는 함수 선언문으로 쓴다. 화살표 함수는 콜백과 한 줄 식에만 쓴다.

## 오류와 로그

| 경우 | 처리 |
|---|---|
| 일어날 수 있는 실패 | `Error` 하위 클래스를 throw한다. async 함수는 reject한다 |
| 코드에 버그가 없으면 일어날 수 없는 경우 | `throw new Error('<성립해야 하는 이유>')` |
| 테스트 | `node:assert/strict` 단언 |

- 문자열이나 객체를 throw하지 않는다. 늘 `Error` 인스턴스를 던진다.
- 원인을 보존한다(`throw new ConfigError('failed to read config', { cause: error })`).
- 라이브러리 모듈의 오류 클래스는 `class {대상}Error extends Error`로 만들고 `this.name`을 지정한다.
- Promise는 돌려주거나 `await`한다. 떠 있는 Promise를 두지 않는다. 최상위에서는 top-level `await`를 쓴다.
- 오류와 로그 메시지는 소문자로 시작하고 마침표를 찍지 않는다(`failed to read config`).

로그는 다음 규칙을 따른다.

- 라이브러리 모듈에서는 `console`을 쓰지 않고 오류를 throw로 넘긴다.
- CLI 진입점 메서드는 진단을 `console.error`로, 결과를 `console.log`로 낸다. 출력 경계는 [code-style 오류와 로그](../code-style/references/errors.md)를 따른다.
- 브라우저 코드는 배포 코드에 `console.log`를 남기지 않는다.
- 저장소가 정한 로그 라이브러리가 있으면 그것을 쓴다.

## 공개 범위와 주석

- 주석을 남기는 경우는 [code-style 공개 범위와 주석](../code-style/references/structure.md#공개-범위와-주석)을 따른다. 문서 주석은 공개 API 계약을 정의할 때만 JSDoc `/** */`으로 쓰고, 실패 조건은 `@throws`로 적는다.
- 매개변수와 반환값의 타입은 `.js` 파일에서만 JSDoc `@param`과 `@returns`로 적는다. `.ts` 파일에서는 TypeScript 타입으로 쓰고 JSDoc에 타입을 되풀이하지 않는다([TypeScript 전용](#typescript-전용)).
- checkJs를 쓰는 저장소이거나 공개 JSDoc 타입을 바꾸면 `// @ts-check`를 달고 `tsc --noEmit --checkJs`로 검사한다.

## 테스트

- `node:test`와 `node:assert/strict`를 쓴다. 저장소가 정한 테스트 도구가 있으면 그것을 쓴다.
- 테스트는 `test/` 폴더의 `{모듈}.test.js`나 `{모듈}.test.ts` 파일에 둔다.
- 이름은 code-style 형식을 따르고 대상은 함수 이름을 그대로 쓴다(`parseFlow_empty_input_throws`).
- 외부 명령이나 브라우저가 없으면 `{ skip: '<이유>' }`로 건너뛰고 미검증 범위를 보고한다. 바뀐 요구사항의 필수 검증이면 완료 판정을 미룬다.
- 브라우저 동작은 Playwright(`playwright-core`)로 실제 페이지를 열어 확인한다.

## 린트 설정

- ESLint와 Prettier 설정을 만들거나 바꾸거나 감사하기 전에 반드시 [린트 설정](references/lint.md)을 읽는다.
- 이름, 비교 순서, `&&`와 `||`의 개수와 섞기, 선언 순서, bool 매개변수 수는 ESLint가 잡지 못하므로 직접 확인한다.

## 검사 명령

경고도 실패로 처리한다.

- 함수 인자와 중첩을 검사하는 도구는 반드시 실제 구문 경계를 처리해야 한다. 정규식 탐색만 했으면 검사하지 못한 범위를 결과에 적는다.

```sh
npx prettier --check .
npx eslint --max-warnings 0 .
node --test
```

- Node.js 18 이상과 개발 의존성 `npm install --save-dev prettier eslint @eslint/js globals eslint-plugin-sonarjs`가 필요하다.

## TypeScript 전용

- 바탕 원칙은 **principle-type-system-discipline** 스킬과 **principle-boundary-discipline** 스킬이다. 규칙별 코드 예는 [TypeScript 타입 예](references/types.md)에 있다.
- 타입은 JSDoc 타입 대신 TypeScript 타입으로 쓴다. JSDoc은 공개 API의 실패 조건 `@throws`처럼 타입 밖의 계약에만 쓴다.
- 변형은 `kind` 리터럴 판별자로 모델링한다(판별 유니온). 불가능한 상태를 표현할 수 있는 모양과 선택적 필드 묶음을 쓰지 않는다.
- 원시 타입은 `& { readonly __brand: 'X' }`로 구분한다(브랜드 타입). 경계에서 한 번 검증한다.
- 잘못된 값을 만들 수 없는 모양으로 모델링한다(구성적 모델링). 비어 있지 않음은 `[T, ...T[]]`, 짝수 길이는 `[T, T][]`, 범위는 `start`와 `duration`으로 쓴다. 런타임 방어 코드로 대신하지 않는다.
- 모든 입력을 처리하는(total) 가장 단순한 타입을 쓴다. 모든 연산이 모든 입력을 처리하는 동안은 `T[]`를 유지한다. 느슨한 타입이 `!`, 캐스트, "일어날 리 없음" throw를 강요하는 곳에서만 `NonEmpty<T>`로 강화한다.
- `any`보다 `unknown`을 쓴다. 외부 데이터는 `unknown`으로 받고 쓰기 전에 좁힌다.
- 가드보다 스키마를 쓴다. 속성별 타입 가드를 쓰기 전에 저장소의 런타임 스키마 라이브러리를 쓰고, `z.infer`처럼 스키마에서 타입을 추론한다. 가드 하나 때문에 새 스키마 의존성을 더하지 않는다.
- `as` 캐스트를 쓰지 않는다. 검증한 뒤에만 캐스트한다. 기존 `as`를 없앨 때는 판별자 없음, 지나치게 넓은 원본 타입, 타입 없는 경계 같은 추론 실패 원인부터 확인한다.
- 좁히기는 판별자 switch, `in` 연산자, `typeof`와 `instanceof`, 사용자 정의 타입 가드, `as` 순서로 앞의 것을 먼저 쓴다.
- 타입 가드는 주장을 실제로 확인하는 것만 쓴다. 이름은 code-style [이름](../code-style/references/structure.md#이름)의 bool 반환 함수 규칙을 따른다.
- 빠짐없음 검사는 default 분기에 `const unreachable: never = x;`를 둔다. 새 변형을 추가하면 컴파일 오류가 난다.
- `as`보다 `satisfies`를 쓴다. 리터럴 타입을 넓히지 않고 검증한다.
- 경계에서 검증한다. 들어오는 곳에서 이름 붙은 도메인 타입으로 파싱한다. `Record<string, unknown>`은 어떤 표기든 파싱 지점 밖으로 넘기지 않는다. 전송 형식은 `ignoreUnknownFields`로 파싱하고, 저장된 JSON은 버전 정보와 파싱 실패 처리를 둔다.
- 스키마에서 타입을 도출한다. 새 인터페이스를 선언하기 전에 `Pick`, `Omit`, `Parameters`, `ReturnType`, `Awaited`, `typeof`를 쓴다.
- 인자 순서는 위치 인자 대신 객체 인자로 드러낸다. 핫 패스(프레임마다 렌더, 토크나이저, 파서)는 예외다.
- 로컬에서 돌릴 수 있는 것은 목을 쓰지 않고 진짜로 테스트한다. 누수와 해제 검사가 있는 실제 테스트 도구를 쓰고, UI는 실행 중인 빌드에서 확인한다.

TypeScript 파일에는 검사 명령을 하나 더 돌린다.

```sh
npx tsc --noEmit
```

- 개발 의존성 `typescript`와 저장소의 `tsconfig.json`이 필요하다.

## 구분

- CSS 문자열과 인라인 style은 [code-style-css](../code-style-css/SKILL.md)가 맡는다.
- SVG 속성 값은 **design-tokens** 스킬이 맡는다.
- 파일 이름은 [folder-naming](../folder-naming/SKILL.md)이 맡는다.
