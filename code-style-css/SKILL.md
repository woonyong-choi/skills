---
name: code-style-css
description: "CSS 작성, 리뷰, 리팩터링 시 사용. class 이름, 파일 구성, 속성 순서, 선택자 우선순위, 값과 단위, 다크 모드, 반응형, 접근성, Stylelint 설정과 검사 명령"
---

# Code Style: CSS

- 저장소 안에 같은 역할의 규칙이 있으면 그것 우선. 없으면 이 스킬이 다른 규칙보다 우선
- 기반: code-style, design-tokens 먼저 적용. 이 스킬 범위: code-style이 언어에 맡긴 부분의 CSS 규칙(`.css`, `<style>`, 인라인 `style`, JavaScript 문자열 안 CSS). 그 밖에서 code-style과 다르면 code-style 우선

## 이름

- 대소문자 표기: 소문자 kebab-case. 포맷: Prettier
- 파일: 역할 명사 kebab-case `.css` (folder-naming과 같은 기준)

| 대상 | 규칙 | 예 |
|---|---|---|
| 구성 요소 class | 저장소 접두사 + 구성 요소 이름. 접두사는 저장소마다 하나 | `.app-figure`, `.app-tabs` |
| 구성 요소 안 부분 | 구성 요소 이름 + `-` + 부분 이름 | `.app-tabs-button` |
| 상태 class | `is-`·`has-` 접두사. 구성 요소 class와 함께만 사용 | `.app-tabs-button.is-active` |
| JavaScript 연결용 | `js-` 접두사 또는 `data-*` 속성. 스타일 규칙에 사용 금지 | `data-step="2"` |
| 사용자 정의 속성 | design-tokens 이름 규칙 | `--color-accent` |
| 애니메이션 `@keyframes` | 동작 이름 kebab-case | `fade-in` |

- `utils`, `common`, `misc`, `helpers`, `etc` 같은 이름의 class·파일 금지 (folder-naming 금지)
- 모양을 뜻하는 이름 금지(`.blue-text`, `.mt-8`). 역할 이름만. 저장소가 유틸리티 CSS 프레임워크를 쓰면 그 규칙 우선

## 선언 순서

파일:

1. 파일 설명 주석
2. `@import`, `@layer` 순서 선언
3. 토큰 정의 (design-tokens 정본 파일에서만)
4. 기본 요소 스타일 (`html`, `body`, 태그 선택자)
5. 배치 (페이지 틀, grid·flex 컨테이너)
6. 구성 요소. 구성 요소 하나를 한 덩어리로, 파일 안 등장 순서는 화면 위 → 아래
7. 상태 class
8. `@media`·`@container` 덮어쓰기. 해당 구성 요소 덩어리 바로 뒤에 배치 허용

- 구성 요소가 5개를 넘으면 구성 요소마다 파일 분리
- JavaScript 템플릿 문자열 안 CSS: 같은 순서. 줄이 100을 넘으면 `.css` 파일로 분리해 빌드나 읽기로 넣기

규칙 안 속성:

| 순서 | 묶음 | 예 |
|---|---|---|
| 1 | 사용자 정의 속성 | `--button-height` |
| 2 | 위치 | `position`, `inset`, `z-index` |
| 3 | 배치 | `display`, `flex`, `grid`, `gap`, `align-*`, `justify-*`, `place-*` |
| 4 | 상자 | `width`, `height`, `min-*`, `max-*`, `margin`, `padding`, `box-sizing`, `overflow` |
| 5 | 글자 | `font`, `font-*`, `line-height`, `letter-spacing`, `text-*`, `white-space` |
| 6 | 모양 | `color`, `background`, `border`, `border-radius`, `box-shadow`, `opacity` |
| 7 | 애니메이션 | `transition`, `animation`, `transform` |
| 8 | 기타 | `cursor`, `pointer-events`, `user-select` |

- 축약 속성 뒤에 개별 속성. 반대 순서 금지(`padding-top` 뒤 `padding`)
- 같은 속성 두 번 선언 금지. 대체 값이 필요하면 `@supports`

## 선택자

- class 선택자 기본. id 선택자 금지. 태그 선택자는 기본 요소 스타일에만
- 우선순위 최대: class 셋(0,3,0). 넘으면 구조 재설계
- 중첩 깊이 최대 3, 한 선택자의 복합 선택자 최대 3
- `!important` 금지. 예외: `prefers-reduced-motion` 덮어쓰기, 외부 라이브러리 인라인 스타일 덮어쓰기. 예외마다 이유 주석
- 전역 태그 선택자로 다른 구성 요소 스타일 변경 금지
- 속성 선택자는 상태 표시용 `[aria-*]`, `[data-*]`에만

## 값

- 화면 값: 토큰만 (design-tokens 원칙)
- 길이 단위: 글자 크기 `rem`, 테두리 `px` 토큰, 배치 비율 `%`·`fr`
- `0`에 단위 금지(`0px` X)
- 토큰 정의 파일의 색 표기: 소문자 6자리 hex나 `oklch()`

## 반응형과 접근성

- 모바일 먼저: 기본 규칙은 좁은 화면, 넓은 화면은 `min-width` 덮어쓰기
- breakpoint, 다크 모드: (design-tokens 쓰는 방법, 정본과 생성물)
- 움직임: 모든 `transition`·`animation`에 `@media (prefers-reduced-motion: reduce)` 대응 필수
- 초점: `:focus-visible` 스타일 필수. `outline: none` 단독 사용 금지
- 누를 수 있는 요소 크기: 최소 24×24 CSS px(WCAG 2.2 2.5.8)
- 글자 대비: 본문 4.5:1, 큰 글자·아이콘 3:1 이상. 실제 화면 검증(테스트)

## 공개 범위와 주석

- 다른 구성 요소 class를 밖에서 덮어쓰기 금지. 바꿀 값은 그 구성 요소의 사용자 정의 속성으로 열기
- 주석 언어와 쓰는 때: (code-style 공개 범위와 주석)
- 구획 주석(`/* ---- 버튼 ---- */`): 선언 순서 파일 항목의 경계에만

## 테스트

- 화면 확인: Playwright로 밝은 화면, 어두운 화면, 좁은 화면(390px), 넓은 화면(1440px) 스크린샷
- 실제 배경 면 위의 최종 합성 색·불투명도·전환 상태 확인. 정지 화면과 움직이는 중간 상태의 규칙 적용 범위 구분
- `prefers-reduced-motion: reduce` 에뮬레이션에서 움직임 정지 확인
- 넘침 확인: 버튼·탭 글자가 상자를 넘지 않는지 `scrollWidth <= clientWidth`
- 스크린샷 비교를 저장소에 두면 기준 이미지는 `test/screenshots/`

## 린트 설정

`.stylelintrc.json`:

```json
{
  "extends": ["stylelint-config-standard"],
  "plugins": ["stylelint-declaration-strict-value"],
  "rules": {
    "selector-max-id": 0,
    "selector-max-specificity": "0,3,0",
    "max-nesting-depth": 3,
    "selector-max-compound-selectors": 3,
    "declaration-no-important": true,
    "color-no-hex": true,
    "color-hex-length": "long",
    "function-disallowed-list": ["rgb", "rgba", "hsl", "hsla", "hwb", "lab", "lch", "oklab", "oklch", "color"],
    "color-named": "never",
    "declaration-block-no-duplicate-properties": true,
    "declaration-block-no-shorthand-property-overrides": true,
    "scale-unlimited/declaration-strict-value": [
      ["/color$/", "background", "fill", "stroke", "/^font/", "line-height", "letter-spacing", "/^(margin|padding|gap|inset)/", "/^(min-|max-)?(width|height)$/", "border-radius", "border-width", "box-shadow", "opacity", "z-index", "/(duration|timing-function)$/"],
      { "ignoreValues": ["0", "1", "auto", "none", "inherit", "initial", "unset", "currentcolor", "transparent", "100%", "50%", "100vh", "100vw"] }
    ]
  },
  "overrides": [
    { "files": ["**/tokens.css"], "rules": { "color-no-hex": null, "function-disallowed-list": null, "scale-unlimited/declaration-strict-value": null } }
  ]
}
```

- 속성 순서 자동 검사가 필요하면 `stylelint-order`의 `order/properties-order`에 선언 순서 표 순서
- Stylelint가 못 잡는 것은 직접 확인: class 이름 형식, 상태 class 짝, 파일 구성 순서, 접근성 항목

## 검사 명령

경고도 실패 처리

```
npx prettier --check "**/*.css"
npx stylelint "**/*.css" --max-warnings 0
python3 <design-tokens 스킬 폴더>/scripts/check_tokens.py <소스 폴더>
```
