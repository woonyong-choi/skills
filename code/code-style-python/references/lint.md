# 린트 설정

`pyproject.toml`:

```toml
[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "B", "SIM", "PLR0913", "FBT", "D", "S101", "S110", "BLE", "G"]
# 누락 docstring 규칙 제외: docstring은 필요할 때만
ignore = ["D100", "D101", "D102", "D103", "D104", "D105", "D106", "D107"]

[tool.ruff.lint.pylint]
max-args = 7

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "D"]

[tool.mypy]
strict = true

[tool.pytest.ini_options]
filterwarnings = ["error"]
```

- ruff `max-args`: `self`·`cls` 제외 → 7 그대로 (code-style 수치 기준)
