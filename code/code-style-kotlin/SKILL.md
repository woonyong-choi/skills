---
name: code-style-kotlin
description: "Kotlin JVM 서버·CLI 코드를 작성·검토하거나 ktlint·detekt 설정을 고칠 때 사용. Android 제외."
---

# Code Style: Kotlin

- 사용자 지시를 먼저 적용. 해당 주제의 사용자 지시가 없으면 작업 대상 저장소의 같은 주제 규칙 파일(예: `AGENTS.md`, `CONTRIBUTING.md`) 적용. 둘 다 없으면 이 스킬 적용. 다른 스킬과 겹치는 규칙은 머리의 연결에 적힌 스킬 중 그 규칙을 정한 스킬 적용
- 기반: code-style 먼저 적용. 이 스킬 범위: code-style이 언어에 맡긴 부분의 Kotlin(JVM 서버, CLI) 규칙. Android 제외. 그 밖에서 code-style과 다르면 code-style 우선

## 이름

- 대소문자 표기: Kotlin 공식 코딩 컨벤션. 포맷: ktlint

| 대상 | 규칙 | 예 |
|---|---|---|
| 접근자 | 프로퍼티로. `getX()`·`setX()` 함수 금지 | `session.name` |
| 읽기 전용 공개 | `private set`, 또는 비공개 백킹 프로퍼티 `_이름` | `private val _items`, `val items: List<Item> get() = _items` |
| 생성 | 생성자. 팩토리는 companion object에 용도가 드러나는 이름 | `Config.fromFile(path)`, `Point.fromPolar(a, r)` |
| 변환 | `toX()` 새 객체, `asX()` 원본을 감싼 뷰 | `toList()`, `asSequence()` |
| 실패하면 null | `OrNull` 접미사 | `findOrNull(id)` |
| 상수 | `const val`, SCREAMING_SNAKE_CASE | `const val MAX_RETRY = 3` |
| 약어 | 두 글자는 모두 대문자, 세 글자 이상은 첫 글자만 | `IOStream`, `HttpClient` |
| 단위 | `kotlin.time.Duration` 우선 | `timeout: Duration` |

- I/O·잠금·외부 호출·입력 크기 비례 순회·예외·상태 변경이 없고 같은 상태에서 같은 값을 주는 계산은 함수 대신 프로퍼티

## 선언 순서

파일:

1. `@file:` 애노테이션
2. `package`
3. `import`. ktlint 순서(사전순 한 그룹, `java`·`javax`·`kotlin`은 끝, 별칭은 맨 끝). 와일드카드 금지
4. 최상위 상수·logger
5. 타입. 공개 먼저
6. 최상위 함수·확장 함수

클래스 (Kotlin 공식 순서):

1. 프로퍼티와 `init` 블록. `val` → `var`, 같은 안에서 공개 → 비공개
2. 보조 생성자
3. 메서드. code-style 타입 순서의 6~10 (프로퍼티·접근자 → 생명주기 → 공개 → 비공개 헬퍼 → 검증)
4. companion object. 상수와 팩토리 포함, 클래스 맨 끝

## 오류와 로그

| 경우 | 처리 |
|---|---|
| 호출하는 쪽이 경우별로 처리할 실패 | `sealed interface` 결과 타입 반환 |
| 실패 이유가 하나뿐인 실패 | `null` 반환, 함수 이름에 `OrNull` |
| 복구하지 않고 위로 올릴 실패 (I/O 등) | 예외. 실행 앱 최상위에서 한 번 처리 |
| 코드에 버그가 없으면 일어날 수 없는 경우 | 인자는 `require(조건) { "<이유>" }`, 상태는 `check(조건) { "<이유>" }`, 도달 불가는 `error("<이유>")` |
| 테스트 | `!!`·`assertFailsWith` 허용 |

- 테스트 밖에서 `!!`, `TODO()` 금지
- 예외는 역할이 드러나는 자체 예외 클래스로. `Exception`·`RuntimeException` 직접 던지기 금지
- 원인 보존: `throw ConfigException("Failed to read config", cause = e)`
- `catch (e: Exception)`은 실행 앱 최상위 처리기에서만
- suspend 함수 안에서 `runCatching` 금지. `CancellationException`은 잡으면 재전파
- 오류·로그 메시지는 대문자로 시작, 마침표 없음: `Failed to read config file`
- 예외 무시 시 처리: (code-style 오류와 로그)

로그:

| 라이브러리 | 쓰는 곳 | 역할 |
|---|---|---|
| `org.slf4j:slf4j-api` | 모든 모듈 | 로그 기록 |
| `ch.qos.logback:logback-classic` | 실행 앱 모듈 | 로그 출력 설정 |

- 저장소에 이미 정한 다른 라이브러리가 있으면 그것 우선
- 라이브러리 모듈에 `logback-classic` 의존성 금지
- logger는 파일 최상위 `private val logger = LoggerFactory.getLogger(Session::class.java)`
- 값은 문자열 연결 대신 자리표시자로: `logger.info("Session started: {}", sessionId)`. 문자열 템플릿(`"$x"`) 금지
- 구조화 값은 `logger.atInfo().addKeyValue("sessionId", id).log("Session started")`
- 세션·요청 단위 문맥은 MDC. 코루틴에서는 `kotlinx-coroutines-slf4j`의 `MDCContext()`
- CLI logback 출력 대상은 stderr. 결과·진단 경계: (code-style 오류와 로그)

## 공개 범위와 주석

- 기본값이 `public`이므로 공개 범위 항상 명시. 비공개 → `internal` → `public` 순서로 필요한 만큼만 확대. `protected`는 상속용에만
- 라이브러리 모듈은 `kotlin { explicitApi() }`로 공개 범위·반환 타입 명시 강제
- 필드 접근은 프로퍼티로. 검증 규칙 없는 단순 데이터 묶음은 `data class`의 공개 `val`
- KDoc(`/** */`)은 code-style 주석 기준대로 필요할 때만. 쓰면 한 줄 요약. 매개변수·반환값은 `@param`·`@return` 대신 본문에서 `[이름]`으로 언급
- 던지는 예외는 `@throws`

## 테스트

- 테스트 프레임워크: 기존 빌드의 호환 버전 우선. 새 설정의 기본 선택은 JUnit과 `kotlin.test` 단언
- 위치: `src/test/kotlin`, 대상과 같은 패키지. 클래스 이름은 `<대상>Test`
- 이름: `parse_emptyInput_throwsException` (테스트 코드에서만 밑줄 허용)

## 린트 설정

기존 빌드·버전 카탈로그의 호환 버전을 사용한다. 새 설정은 Gradle·Kotlin·JDK 조합을 확인하고 선택 버전·확인일을 기록한다. 아래 버전 자리는 확인한 값으로 교체

`build.gradle.kts`:

```kotlin
plugins {
    id("io.gitlab.arturbosch.detekt") version "{호환 detekt 버전}"
    id("org.jlleitschuh.gradle.ktlint") version "{호환 ktlint 플러그인 버전}"
}

kotlin {
    explicitApi() // 라이브러리 모듈만
    compilerOptions {
        allWarningsAsErrors = true
    }
}

detekt {
    buildUponDefaultConfig = true
    config.setFrom("config/detekt.yml")
}
```

`config/detekt.yml`:

```yaml
complexity:
  LongMethod:
    threshold: 103
  LongParameterList:
    functionThreshold: 8
    constructorThreshold: 8
  NestedBlockDepth:
    threshold: 4
  ComplexCondition:
    threshold: 5
  CognitiveComplexMethod:
    active: true
    threshold: 16
  CyclomaticComplexMethod:
    active: false
style:
  ReturnCount:
    excludeGuardClauses: true
exceptions:
  NotImplementedDeclaration:
    active: true
```

- detekt threshold는 이 값 이상이면 경고 → code-style 절대 최대 + 1
- detekt 함수 길이에 선언 줄과 닫는 괄호 포함 → 본문 100줄 + 2 + 1 = 103
- `ComplexCondition` 기준: 조건 개수 → `&&`·`||` 3개 = 조건 4개, 5개부터 경고
- `!!` 검사(`UnsafeCallOnNullableType`)는 타입 정보가 필요해 `detektMain`·`detektTest`에서만 동작
- 인지 복잡도 기준: detekt 점수
- detekt·ktlint가 못 잡는 것은 직접 확인: 이름, 비교 순서, bool 매개변수, 파일 길이, 선언 순서, 로그 레벨

## 검사 명령

경고도 실패 처리

```
./gradlew ktlintCheck detektMain detektTest test
```
