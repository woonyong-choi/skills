# 린트 설정

workspace는 각 crate의 `Cargo.toml`에 `[lints] workspace = true`를 두고 루트에서 아래 설정을 관리한다. 단일 패키지는 해당 `Cargo.toml`의 `[lints.rust]`, `[lints.clippy]`에 같은 규칙 적용

작업 공간 `Cargo.toml`:

```toml
[workspace.lints.rust]
unreachable_pub = "warn"

[workspace.lints.clippy]
too_many_lines = "warn"
too_many_arguments = "warn"
fn_params_excessive_bools = "warn"
excessive_nesting = "warn"
cognitive_complexity = "warn"
if_not_else = "warn"
unwrap_used = "warn"
panic = "warn"
todo = "warn"
unimplemented = "warn"
```

`clippy.toml`:

```toml
too-many-lines-threshold = 100
too-many-arguments-threshold = 8
max-fn-params-bools = 3
excessive-nesting-threshold = 5
cognitive-complexity-threshold = 15
allow-unwrap-in-tests = true
allow-panic-in-tests = true
```

- clippy 매개변수 수에 self 포함 → 7개 (code-style 수치 기준) + self = 8
- clippy 중첩에 impl·fn 블록 포함 → impl(1) + fn(2) + 3단 (code-style 수치 기준) = 5. impl 밖 함수는 1단 더 허용되므로 직접 확인
- clippy 인지 복잡도: 실험 단계(nursery) 규칙, SonarQube와 점수 차이. 기준은 clippy 점수
- clippy 기본 규칙이 잡는 것: `x == true` 비교(`bool_comparison`), 불필요한 부정(`nonminimal_bool`), 테스트 모듈 뒤 선언(`items_after_test_module`)
