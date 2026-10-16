# 린트 설정

Stylelint 설정의 기준 값과 함께 정할 것을 적는다.

`.stylelintrc.json`:

```json
{
  "extends": ["stylelint-config-standard"],
  "rules": {
    "selector-max-id": 0,
    "declaration-no-important": true,
    "color-no-hex": true,
    "function-disallowed-list": ["rgb", "rgba", "hsl", "hsla", "hwb", "lab", "lch", "oklab", "oklch", "color"],
    "color-named": "never",
    "declaration-block-no-duplicate-properties": true,
    "declaration-block-no-shorthand-property-overrides": true
  }
}
```

- 속성 순서를 의무로 정한 저장소에서는 `stylelint-order`의 `order/properties-order`에 [선언 순서](../SKILL.md#선언-순서)의 속성 순서대로 목록을 넣는다.
- 토큰 허용 값과 예외 검사는 **design-tokens** 스킬의 `check_tokens.py`가 맡는다. 생성물을 검사에서 빼는 방법은 design-tokens의 정본과 생성물 규칙을 따른다.
