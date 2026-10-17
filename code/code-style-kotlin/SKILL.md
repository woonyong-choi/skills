---
name: code-style-kotlin
description: "Kotlin JVM 서버와 CLI 코드(Android 제외)를 쓰거나 검토할 때, ktlint와 detekt 설정을 고칠 때 쓴다."
---

# Kotlin 코드 스타일

[code-style](../code-style/SKILL.md)을 먼저 적용하고, 이 스킬은 code-style이 언어에 맡긴 항목의 Kotlin(JVM 서버, CLI) 규칙만 정한다. Android는 다루지 않는다. 그 밖에서 code-style과 다르면 code-style을 따른다.

## 이름

- 대소문자는 Kotlin 공식 코딩 컨벤션을 따르고 포맷은 ktlint로 맞춘다.

| 대상 | 규칙 | 예 |
|---|---|---|
| 접근자 | 프로퍼티로 쓴다. `getX()`, `setX()` 함수를 쓰지 않는다 | `session.name` |
| 읽기 전용 공개 | `private set`이나 비공개 백킹 프로퍼티 `_이름`을 쓴다 | `private val _items`, `val items: List<Item> get() = _items` |
| 생성 | 생성자를 쓴다. 팩토리는 companion object에 용도가 드러나는 이름으로 둔다 | `Config.fromFile(path)`, `Point.fromPolar(a, r)` |
| 변환 | 새 객체는 `toX()`, 원본을 감싼 뷰는 `asX()` | `toList()`, `asSequence()` |
| 실패하면 null | `OrNull` 접미사를 붙인다 | `findOrNull(id)` |
| 상수 | `const val`을 SCREAMING_SNAKE_CASE로 쓴다 | `const val MAX_RETRY = 3` |
| 약어 | 두 글자 약어는 모두 대문자로, 세 글자 이상은 첫 글자만 대문자로 쓴다 | `IOStream`, `HttpClient` |
| 단위 | `kotlin.time.Duration`을 먼저 쓴다 | `timeout: Duration` |

- I/O, 잠금, 외부 호출, 입력 크기에 비례하는 순회, 예외, 상태 변경이 없고 같은 상태에서 같은 값을 주는 계산은 함수 대신 프로퍼티로 쓴다.

## 선언 순서

파일은 다음 순서로 쓴다.

1. `@file:` 애노테이션
2. `package`
3. `import`. ktlint 순서를 따른다. 사전순 한 그룹으로 두고 `java`, `javax`, `kotlin`은 끝에, 별칭은 맨 끝에 둔다. 와일드카드를 쓰지 않는다.
4. 최상위 상수와 logger
5. 타입. 공개 타입을 먼저 둔다.
6. 최상위 함수와 확장 함수

클래스는 Kotlin 공식 순서를 따른다.

1. 프로퍼티와 `init` 블록. `val`, `var` 순서로 두고 그 안에서 공개, 비공개 순서로 둔다.
2. 보조 생성자
3. 메서드. code-style 타입 순서의 6~10번(프로퍼티와 접근자, 생명주기, 공개 메서드, 비공개 헬퍼, 검증)을 따른다.
4. companion object. 상수와 팩토리를 넣고 클래스 맨 끝에 둔다.

## 오류와 로그

| 경우 | 처리 |
|---|---|
| 호출하는 쪽이 경우별로 처리할 실패 | `sealed interface` 결과 타입을 돌려준다 |
| 실패 이유가 하나뿐인 실패 | `null`을 돌려주고 함수 이름에 `OrNull`을 붙인다 |
| 복구하지 않고 위로 올릴 실패(I/O 등) | 예외를 던지고 실행 앱 최상위에서 한 번 처리한다 |
| 코드에 버그가 없으면 일어날 수 없는 경우 | 인자는 `require(조건) { "<이유>" }`, 상태는 `check(조건) { "<이유>" }`, 도달 불가는 `error("<이유>")` |
| 테스트 | `!!`와 `assertFailsWith`를 써도 된다 |

- 테스트 밖에서 `!!`와 `TODO()`를 쓰지 않는다.
- 예외는 역할이 드러나는 자체 예외 클래스로 던진다. `Exception`이나 `RuntimeException`을 직접 던지지 않는다.
- 원인을 보존한다(`throw ConfigException("Failed to read config", cause = e)`).
- `catch (e: Exception)`은 실행 앱 최상위 처리기에서만 쓴다.
- suspend 함수 안에서 `runCatching`을 쓰지 않는다. `CancellationException`을 잡으면 다시 던진다.
- 오류와 로그 메시지는 대문자로 시작하고 마침표를 찍지 않는다(`Failed to read config file`).

로그 라이브러리는 다음과 같이 쓴다. 저장소가 이미 다른 라이브러리를 정했으면 그것을 쓴다.

| 라이브러리 | 쓰는 곳 | 역할 |
|---|---|---|
| `org.slf4j:slf4j-api` | 모든 모듈 | 로그 기록 |
| `ch.qos.logback:logback-classic` | 실행 앱 모듈 | 로그 출력 설정 |

- 라이브러리 모듈에 `logback-classic` 의존성을 두지 않는다.
- logger는 파일 최상위에 `private val logger = LoggerFactory.getLogger(Session::class.java)`로 둔다.
- 값은 문자열 연결 대신 자리표시자로 넘긴다(`logger.info("Session started: {}", sessionId)`). 문자열 템플릿(`"$x"`)을 쓰지 않는다.
- 구조화 값은 `logger.atInfo().addKeyValue("sessionId", id).log("Session started")`로 넘긴다.
- 세션과 요청 단위 문맥은 MDC에 둔다. 코루틴에서는 `kotlinx-coroutines-slf4j`의 `MDCContext()`를 쓴다.
- CLI의 logback 출력 대상은 stderr다. 결과와 진단의 경계는 [code-style 오류와 로그](../code-style/references/errors.md)를 따른다.

## 공개 범위와 주석

- 기본값이 `public`이므로 공개 범위를 늘 적는다. 비공개, `internal`, `public` 순서로 필요한 만큼만 넓힌다. `protected`는 상속용에만 쓴다.
- 라이브러리 모듈은 `kotlin { explicitApi() }`로 공개 범위와 반환 타입 표기를 강제한다.
- 필드는 프로퍼티로 다룬다. 검증 규칙이 없는 단순 데이터 묶음은 `data class`의 공개 `val`로 둔다.
- 주석을 남기는 경우는 [code-style 공개 범위와 주석](../code-style/references/structure.md#공개-범위와-주석)을 따른다. KDoc(`/** */`)은 공개 API 계약을 정의할 때만 한 줄 요약으로 쓴다. 매개변수와 반환값은 `@param`, `@return` 대신 본문에서 `[이름]`으로 언급한다.
- 공개 API가 던지는 예외는 `@throws`로 적는다.

## 테스트

- 테스트 프레임워크는 기존 빌드와 호환되는 버전을 먼저 쓴다. 새로 설정할 때는 JUnit과 `kotlin.test` 단언을 기본으로 고른다.
- 테스트는 `src/test/kotlin`에서 대상과 같은 패키지에 두고, 클래스 이름은 `<대상>Test`로 짓는다.
- 이름은 `parse_emptyInput_throwsException`처럼 짓는다. 밑줄은 테스트 코드에서만 허용한다.

## 린트 설정

- Gradle, detekt, ktlint 설정을 만들거나 바꾸거나 감사하기 전에 반드시 [린트 설정](references/lint.md)을 읽는다.
- 이름, 비교 순서, bool 매개변수, 파일 길이, 선언 순서, 로그 레벨은 detekt와 ktlint가 잡지 못하므로 직접 확인한다.

## 검사 명령

경고도 실패로 처리한다.

```sh
./gradlew ktlintCheck detektMain detektTest test
```
