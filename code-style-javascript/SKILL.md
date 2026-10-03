---
name: code-style-javascript
description: "JavaScript(Node.js, 브라우저) 코드 작성, 리뷰, 리팩터링 시 사용. 이름 형식, 모듈, 에러 처리, 로그, 공개 범위, JSDoc, 테스트(node:test), ESLint·Prettier 설정과 검사 명령"
---

# Code Style: JavaScript

- 저장소 안에 같은 역할의 규칙이 있으면 그것 우선. 없으면 이 스킬이 다른 규칙보다 우선
- 기반: code-style 먼저 적용. 이 스킬 범위: code-style이 언어에 맡긴 부분의 JavaScript 규칙. 그 밖에서 code-style과 다르면 code-style 우선
- 필요할 때만 읽기: CSS 문자열, 인라인 style, SVG 속성 값 작성 → design-tokens

## 이름

- 대소문자 표기: 변수·함수 camelCase, 클래스 PascalCase, 모듈 상수 UPPER_SNAKE_CASE. 포맷: Prettier
- 파일: 소문자 kebab-case `.js` (folder-naming과 같은 기준)

| 대상 | 규칙 | 예 |
|---|---|---|
| 접근자 | 필드나 `get` 접근자. 계산 없는 `getX()`·`setX()` 메서드 금지 | `session.name`, `get isReady()` |
| 생성 | `constructor`. 다른 생성 방법은 `static from*`·`create*` 팩토리 | `Config.fromFile(path)`, `createPlayer(root)` |
| 변환 | `to*` 새 값, `as*` 같은 값의 다른 표현 | `toJson()`, `asArray()` |
| 반복자 | 제너레이터 `*iter*`나 `[Symbol.iterator]` | `*iterSessions()` |
| 상수 | 모듈 최상위의 바뀌지 않는 값만 UPPER_SNAKE_CASE. 객체 상수는 `Object.freeze` | `MAX_RETRY`, `DEFAULTS` |
| 약어 | 한 단어처럼 camelCase·PascalCase | `httpClient`, `parseUrl`, `HttpError` |
| 비공개 | 모듈: export 안 함. 클래스: `#` 필드·메서드. `_` 접두사 금지 | `#cache` |
| 단위 | 시간 타입이 없어 접미사 필수 | `timeoutMs`, `sizeBytes` |

## 선언 순서

모듈:

- ES 모듈(`import`·`export`)만. `package.json`에 `"type": "module"`. CommonJS `require` 금지(외부 도구 설정 파일 제외)
- named export만. `export default` 금지
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

- 함수 선언문은 끌어올려지므로 호출보다 뒤에 선언 허용. `const` 화살표 함수는 끌어올려지지 않아 사용 전 선언 필수
- 모듈 최상위 함수는 함수 선언문. 화살표 함수는 콜백과 한 줄 식에만

## 에러와 로그

| 경우 | 처리 |
|---|---|
| 일어날 수 있는 실패 | `Error` 하위 클래스 throw. async 함수는 reject |
| 코드에 버그가 없으면 일어날 수 없는 경우 | `throw new Error('<성립해야 하는 이유>')` |
| 테스트 | `node:assert/strict` 단언 |

- 문자열·객체 throw 금지. 항상 `Error` 인스턴스
- 원인 보존: `throw new ConfigError('failed to read config', { cause: error })`
- 라이브러리 모듈의 에러 클래스: `class {대상}Error extends Error`, `this.name` 지정
- Promise: 반환하거나 `await`. 떠 있는 Promise 금지. 최상위는 top-level `await`
- 에러·로그 메시지는 소문자로 시작, 마침표 없음: `failed to read config`

로그:

- 라이브러리 모듈: `console` 금지. 오류는 throw로 전달
- CLI 진입점: 진단은 `console.error`(stderr), 결과만 `console.log`(stdout)
- 브라우저 코드: 배포 코드에 `console.log` 금지
- 저장소에 정한 로그 라이브러리가 있으면 그것 우선

## 공개 범위와 주석

- 문서 주석: JSDoc `/** */`. 실패 조건은 `@throws`
- 타입은 JSDoc `@param`·`@returns`로. 타입 검사가 필요하면 `// @ts-check`와 `tsc --noEmit --checkJs`

## 테스트

- `node:test`와 `node:assert/strict`. 저장소에 정한 테스트 도구가 있으면 그것 우선
- 위치: `test/` 폴더, 파일은 `{모듈}.test.js`
- 이름: code-style 형식, 대상은 함수 이름 그대로: `parseFlow_empty_input_throws`
- 외부 명령·브라우저가 필요한 테스트: 없을 때 `{ skip: '<이유>' }`로 건너뛰기
- 브라우저 동작: Playwright(`playwright-core`)로 실제 페이지를 열어 확인

## 린트 설정

`eslint.config.js`:

```js
import js from '@eslint/js';
import globals from 'globals';
import sonarjs from 'eslint-plugin-sonarjs';

export default [
  { ignores: ['**/tokens.js'] },
  js.configs.recommended,
  {
    languageOptions: { globals: { ...globals.node, ...globals.browser } },
    plugins: { sonarjs },
    rules: {
      'max-lines': ['warn', { max: 750, skipBlankLines: true, skipComments: true }],
      'max-lines-per-function': ['warn', { max: 100, skipBlankLines: true, skipComments: true }],
      'max-params': ['warn', 7],
      'max-depth': ['warn', 3],
      'sonarjs/cognitive-complexity': ['warn', 15],
      'no-throw-literal': 'error',
      'prefer-promise-reject-errors': 'error',
      'no-console': ['warn', { allow: ['error'] }],
      yoda: 'error',
      eqeqeq: 'error',
      'no-negated-condition': 'warn',
      'no-nested-ternary': 'warn',
      'prefer-const': 'error',
      'no-var': 'error',
      'no-restricted-syntax': ['error', 'ExportDefaultDeclaration'],
    },
  },
  { files: ['test/**'], rules: { 'max-lines-per-function': 'off' } },
  { files: ['eslint.config.js'], rules: { 'no-restricted-syntax': 'off' } },
];
```

- CLI 진입점 파일은 `no-console`을 파일 단위로 끔
- ESLint가 못 잡는 것은 직접 확인: 이름, 비교 순서, `&&`·`||` 개수와 섞기, 선언 순서, bool 매개변수 수

`.prettierrc.json`:

```json
{ "singleQuote": true, "printWidth": 140 }
```

## 검사 명령

경고도 실패 처리

- 함수 인자·중첩 검사 도구: 실제 구문 경계 처리 필수. 정규식 탐색만이면 미검사 범위를 결과에 명시

```
npx prettier --check .
npx eslint --max-warnings 0 .
node --test
```
