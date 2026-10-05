# 린트 설정

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
