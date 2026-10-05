# 린트 설정

`.stylelintrc.json`:

```json
{
  "extends": ["stylelint-config-standard"],
  "rules": {
    "selector-max-id": 0,
    "declaration-no-important": true,
    "color-no-hex": true,
    "color-hex-length": "long",
    "function-disallowed-list": ["rgb", "rgba", "hsl", "hsla", "hwb", "lab", "lch", "oklab", "oklch", "color"],
    "color-named": "never",
    "declaration-block-no-duplicate-properties": true,
    "declaration-block-no-shorthand-property-overrides": true
  }
}
```

- 속성 순서를 의무화한 저장소에서는 `stylelint-order`의 `order/properties-order`에 이 스킬의 선언 순서 표대로 속성 목록 설정
- 토큰 허용 값·예외 검사: design-tokens의 check_tokens.py. 생성물 제외는 생성물 표시 또는 확인한 실제 생성 경로로만 설정(design-tokens의 정본과 생성물 절에 있는 파일 표)
