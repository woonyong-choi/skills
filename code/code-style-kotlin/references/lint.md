# 린트 설정

Gradle, detekt, ktlint 설정의 기준 값과 그 값을 정한 계산을 적는다.

- 기존 빌드와 버전 카탈로그에 호환되는 버전을 쓴다.
- 새로 설정할 때는 Gradle, Kotlin, JDK 조합을 확인한 뒤 고른 버전과 확인한 날짜를 적는다. 아래 버전 자리는 확인한 값으로 바꾼다.

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

## 값을 정한 계산

- detekt threshold는 그 값 이상이면 경고하므로 code-style [수치 기준](../../code-style/references/structure.md#수치-기준)의 절대 최대에 1을 더한다.
- detekt 함수 길이는 선언 줄과 닫는 괄호를 포함하므로 본문 100줄에 그 2줄과 경고 기준 1을 더해 103으로 둔다.
- `ComplexCondition`은 조건 개수를 센다. `&&`, `||` 3개는 조건 4개이므로 5개부터 경고한다.
- `!!` 검사(`UnsafeCallOnNullableType`)는 타입 정보가 필요해 `detektMain`과 `detektTest`에서만 돈다.
- 인지 복잡도는 detekt 점수를 기준으로 삼는다.
