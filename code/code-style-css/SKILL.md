---
name: code-style-css
description: "CSS와 인라인 style을 쓰거나 검토할 때, 선택자, 배치, 반응형, 접근성을 검사할 때 쓴다."
---

# CSS 코드 스타일

[code-style](../code-style/SKILL.md)과 **design-tokens** 스킬을 먼저 적용하고, 이 스킬은 code-style이 언어에 맡긴 항목의 CSS 규칙만 정한다. 대상은 `.css`, `<style>`, 인라인 `style`, JavaScript 문자열 안의 CSS다. 그 밖에서 부딪히면 화면 값과 토큰은 design-tokens를, 나머지는 code-style을 따른다.

## 이름

- 대소문자는 소문자 kebab-case로 쓰고 포맷은 Prettier를 따른다.
- 파일 이름은 역할 명사를 kebab-case로 쓴 `.css`다. [folder-naming](../folder-naming/SKILL.md)과 같은 기준이다.

| 대상 | 규칙 | 예 |
|---|---|---|
| 구성 요소 class | 저장소 접두사와 구성 요소 이름을 잇는다. 접두사는 저장소마다 하나다 | `.app-figure`, `.app-tabs` |
| 구성 요소 안 부분 | 구성 요소 이름 뒤에 `-`와 부분 이름을 붙인다 | `.app-tabs-button` |
| 상태 class | `is-`, `has-` 접두사를 쓰고 구성 요소 class와 함께만 쓴다 | `.app-tabs-button.is-active` |
| JavaScript 연결용 | `js-` 접두사나 `data-*` 속성을 쓰고 스타일 규칙에는 쓰지 않는다 | `data-step="2"` |
| 사용자 정의 속성 | design-tokens의 이름 규칙을 따른다 | `--color-accent` |
| 애니메이션 `@keyframes` | 동작 이름을 kebab-case로 쓴다 | `fade-in` |

- 모양을 뜻하는 이름(`.blue-text`, `.mt-8`)을 쓰지 않고 역할 이름만 쓴다. 저장소가 유틸리티 CSS 프레임워크를 쓰면 그 규칙을 따른다.

## 선언 순서

파일은 다음 순서로 쓴다.

1. 라이선스 머리말
2. `@import`(생성된 `tokens.css` 포함)와 `@layer` 순서 선언. 토큰 정의를 직접 쓰지 않는다.
3. 기본 요소 스타일(`html`, `body`, 태그 선택자)
4. 배치(페이지 틀, grid와 flex 컨테이너)
5. 구성 요소. 구성 요소 하나를 한 덩어리로 두고, 파일 안 순서는 화면의 위에서 아래로 둔다.
6. 상태 class
7. `@media`, `@container` 덮어쓰기. 해당 구성 요소 덩어리 바로 뒤에 두어도 된다.

- 스타일을 적용하는 구성 요소, 다른 곳에서 다시 쓰는지, 따로 불러와야 하는지가 다르면 파일을 나눌지 검토한다.
- JavaScript 템플릿 문자열 안의 CSS에도 위 순서를 적용한다. 위의 파일 분리 조건에 해당하면 `.css` 파일로 빼서 빌드에 넣거나 실행할 때 읽는다.

규칙 안 속성은 다음 묶음 순서로 쓴다.

1. 사용자 정의 속성(`--button-height`)
2. 위치(`position`, `inset`, `z-index`)
3. 배치(`display`, `flex`, `grid`, `gap`, `align-*`, `justify-*`, `place-*`)
4. 상자(`width`, `height`, `min-*`, `max-*`, `margin`, `padding`, `box-sizing`, `overflow`)
5. 글자(`font`, `font-*`, `line-height`, `letter-spacing`, `text-*`, `white-space`)
6. 모양(`color`, `background`, `border`, `border-radius`, `box-shadow`, `opacity`)
7. 애니메이션(`transition`, `animation`, `transform`)
8. 기타(`cursor`, `pointer-events`, `user-select`)

- 축약 속성 뒤에 개별 속성을 쓴다. 반대 순서(`padding-top` 뒤 `padding`)로 쓰지 않는다.
- 같은 속성을 두 번 선언하지 않는다. 지원 브라우저에서 속성이나 값의 지원이 갈리면 `@supports`를 쓴다.

## 선택자

- class 선택자를 기본으로 쓴다. id 선택자를 쓰지 않는다. 태그 선택자는 기본 요소 스타일에만 쓴다.
- 다른 구성 요소 내부의 태그나 class에 기대거나, 같은 속성을 덮으려고 선택자 우선순위를 계속 높이고 있으면 각 스타일을 어느 구성 요소에 둘지와 선택자 구조를 다시 검토한다.
- `!important`를 쓰지 않는다. 예외는 `prefers-reduced-motion` 덮어쓰기와 외부 라이브러리 인라인 스타일 덮어쓰기다. 예외 자리에만 이유를 넣은 `stylelint-disable-next-line declaration-no-important -- {이유}`를 단다.
- 전역 태그 선택자로 다른 구성 요소의 스타일을 바꾸지 않는다.
- 속성 선택자는 상태를 나타내는 `[aria-*]`, `[data-*]`에만 쓴다.

## 값

- 화면 값은 토큰만 쓴다(design-tokens 원칙). 색은 의미 토큰의 `var()`만 쓰고 색을 직접 적지 않는다.
- 길이 단위는 글자 크기에 `rem`, 테두리에 `px` 토큰, 배치 비율에 `%`와 `fr`을 쓴다.
- `0`에는 단위를 붙이지 않는다(`0px`로 쓰지 않는다).

## 반응형과 접근성

- 모바일 먼저 쓴다. 기본 규칙은 좁은 화면용이고 넓은 화면은 `min-width`로 덮어쓴다.
- breakpoint와 다크 모드는 **design-tokens** 스킬의 쓰는 방법과 정본과 생성물 규칙을 따른다.
- 모든 `transition`과 `animation`에 반드시 `@media (prefers-reduced-motion: reduce)` 대응을 둔다.
- 반드시 `:focus-visible` 스타일을 둔다. `outline: none`만 단독으로 쓰지 않는다.
- 누를 수 있는 요소는 [WCAG 2.5.8](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)의 크기, 간격, 예외 조건으로 판정한다.
- 글자 대비는 본문 4.5:1, 큰 글자와 아이콘 3:1 이상이다. 큰 글자는 WCAG 1.4.3의 크기와 굵기 정의(18pt 이상 또는 굵은 14pt 이상)로 판정한다. 실제 화면으로 검증한다(테스트 절).

## 공개 범위와 주석

- 다른 구성 요소의 class를 밖에서 덮어쓰지 않는다. 바꿀 값은 그 구성 요소의 사용자 정의 속성으로 연다.
- 주석의 언어와 쓰는 때는 [code-style 공개 범위와 주석](../code-style/references/structure.md#공개-범위와-주석)을 따른다. 구획 주석(`/* ---- 버튼 ---- */`)을 쓰지 않는다. 구성 요소 경계는 선언 순서와 파일 나누기로 드러낸다.

## 테스트

- 화면은 Playwright 스크린샷으로 확인한다. 변경이 영향을 주는 테마, 저장소 지원표의 최소 폭과 최대 폭, 영향받는 breakpoint 앞뒤를 찍는다. 지원표가 없으면 수용 조건에 쓰는 폭을 적는다. 저장소에 테스트를 더할지는 [code-style 테스트](../code-style/references/testing.md)를 따른다.
- 실제 배경 면 위에서 최종 합성 색, 불투명도, 전환 상태를 확인한다. 정지 화면과 움직이는 중간 상태에 규칙이 어디까지 적용되는지 구분한다.
- `prefers-reduced-motion: reduce` 에뮬레이션에서 움직임이 멈추는지 확인한다.
- 버튼과 탭의 글자가 상자를 넘지 않는지 `scrollWidth <= clientWidth`로 확인한다.
- 스크린샷 비교를 저장소에 두면 기준 이미지는 `test/screenshots/`에 둔다.

## 린트 설정

- Stylelint 설정을 만들거나 바꾸거나 감사하기 전에 반드시 [린트 설정](references/lint.md)을 읽는다.
- class 이름 형식, 상태 class 짝, 파일 구성 순서, 접근성 항목은 Stylelint가 잡지 못하므로 직접 확인한다.

## 검사 명령

경고도 실패로 처리한다.

```sh
npx prettier --check "**/*.css"
npx stylelint "**/*.css" --max-warnings 0
python3 <design-tokens 스킬 폴더>/scripts/check_tokens.py <소스 폴더>
```

- Node.js와 개발 의존성 `npm install --save-dev prettier stylelint stylelint-config-standard`, Python 3.9 이상과 표준 라이브러리가 필요하다.

## 구분

- class와 파일 이름의 금지 이름은 [folder-naming](../folder-naming/SKILL.md)이 맡는다.
- 토큰 값, 테마, 아이콘, 화면 값 검사는 **design-tokens** 스킬이 맡는다.
- 언어 공통 규칙은 [code-style](../code-style/SKILL.md)이 맡는다.
