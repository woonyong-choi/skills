---
name: code-style-css
description: "CSS와 인라인 style을 작성·검토할 때 사용. 선택자·배치·반응형·접근성 검사 포함."
---

# Code Style: CSS

- 상위 지시 우선. 같은 대상·조건의 저장소 규칙이 있으면 적용, 없으면 공통 정본과 전용 규칙의 위임 범위 적용
- 기반: code-style, design-tokens 먼저 적용. 이 스킬 범위: code-style이 언어에 맡긴 부분의 CSS 규칙(`.css`, `<style>`, 인라인 `style`, JavaScript 문자열 안 CSS). 그 밖에서 code-style과 다르면 code-style 우선
- 필요할 때만 읽기: class·파일 이름의 금지 이름 확인 → folder-naming

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

- class·파일의 금지 이름: folder-naming 적용
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

- 구성 요소 소유권·재사용·독립 로드 조건이 다르면 파일 분리 검토
- JavaScript 템플릿 문자열 안 CSS: 같은 순서. 독립 변경·재사용·로드가 필요하면 `.css` 파일로 분리해 빌드나 읽기로 넣기

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
- 선택자 우선순위·중첩: 다른 구성 요소의 내부 구조에 의존하거나 덮어쓰기 경쟁이 생기면 소유권과 선택자 구조 재검토
- `!important` 금지. 예외: `prefers-reduced-motion` 덮어쓰기, 외부 라이브러리 인라인 스타일 덮어쓰기. 예외 위치에만 이유를 포함한 `stylelint-disable-next-line declaration-no-important -- {이유}` 적용
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
- 누를 수 있는 요소: [WCAG 2.5.8](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)의 크기·간격·예외 조건으로 판정
- 글자 대비: 본문 4.5:1, 큰 글자·아이콘 3:1 이상. 큰 글자는 WCAG 1.4.3의 크기·굵기 정의로 판정(18pt 이상 또는 굵은 14pt 이상). 실제 화면 검증(테스트)

## 공개 범위와 주석

- 다른 구성 요소 class를 밖에서 덮어쓰기 금지. 바꿀 값은 그 구성 요소의 사용자 정의 속성으로 열기
- 주석 언어와 쓰는 때: (code-style 공개 범위와 주석)
- 구획 주석(`/* ---- 버튼 ---- */`): 선언 순서 파일 항목의 경계에만

## 테스트

- 화면 확인: Playwright로 밝은·어두운 테마, 최소 지원 폭·각 breakpoint 전후·최대 검토 폭 스크린샷. 사용한 폭 기록
- 실제 배경 면 위의 최종 합성 색·불투명도·전환 상태 확인. 정지 화면과 움직이는 중간 상태의 규칙 적용 범위 구분
- `prefers-reduced-motion: reduce` 에뮬레이션에서 움직임 정지 확인
- 넘침 확인: 버튼·탭 글자가 상자를 넘지 않는지 `scrollWidth <= clientWidth`
- 스크린샷 비교를 저장소에 두면 기준 이미지는 `test/screenshots/`

## 린트 설정

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

- 속성 순서를 의무화한 저장소에서는 `stylelint-order`의 `order/properties-order`에 선언 순서 표 순서
- 토큰 허용 값·예외 검사: design-tokens의 check_tokens.py. 생성물 제외는 생성물 표시 또는 확인한 실제 생성 경로로만 설정(design-tokens 정본과 생성물)
- Stylelint가 못 잡는 것은 직접 확인: class 이름 형식, 상태 class 짝, 파일 구성 순서, 접근성 항목

## 검사 명령

경고도 실패 처리

```
npx prettier --check "**/*.css"
npx stylelint "**/*.css" --max-warnings 0
python3 <design-tokens 스킬 폴더>/scripts/check_tokens.py <소스 폴더>
```
