# 린트 설정

Cargo와 Clippy 설정의 기준 값과 그 값을 정한 계산을 적는다.

- workspace는 각 crate의 `Cargo.toml`에 `[lints] workspace = true`를 두고 루트에서 아래 설정을 관리한다.
- 단일 패키지는 그 `Cargo.toml`의 `[lints.rust]`, `[lints.clippy]`에 같은 규칙을 적는다.

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

## 값을 정한 계산

- clippy 매개변수 수는 self를 포함하므로 code-style [수치 기준](../../code-style/references/structure.md#수치-기준)의 7개에 self를 더해 8로 둔다.
- clippy 중첩은 impl과 fn 블록을 포함하므로 impl(1)과 fn(2)에 수치 기준의 3단을 더해 5로 둔다.
- clippy 인지 복잡도는 실험 단계(nursery) 규칙이고 SonarQube와 점수가 다르다. 기준은 clippy 점수다.
- `x == true` 비교(`bool_comparison`), 불필요한 부정(`nonminimal_bool`), 테스트 모듈 뒤 선언(`items_after_test_module`)은 clippy 기본 규칙이 잡는다.
