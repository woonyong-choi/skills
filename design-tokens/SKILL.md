---
name: design-tokens
description: "색, 글꼴, 간격, 반지름, 그림자, 시간 같은 화면 값을 정하거나 쓸 때 사용. 토큰 정본, 이름, 세 층, 다크 모드, 하드코딩 금지, 생성·검사 스크립트"
---

# Design Tokens

- 저장소 안에 같은 역할의 규칙이 있으면 그것 우선. 없으면 이 스킬이 다른 규칙보다 우선
- 범위: 화면에 보이는 모든 값의 정의, 이름, 사용 방법, 하드코딩 검사
- 필요할 때만 읽기: CSS 작성 → code-style-css; JavaScript 작성 → code-style-javascript; 문서 그림(D2, Vega-Lite) 색 → repo-docs-figures

## 원칙

| 원칙 | 규칙 |
|---|---|
| 하드코딩 금지 | 색, 글꼴, 글자 크기, 줄 높이, 간격, 반지름, 테두리 두께, 그림자, 투명도, z-index, 시간, 이징, 크기, breakpoint 값은 토큰으로만 사용. 아래 허용 값 밖 예외 없음 |
| 정본 하나 | 토큰 값은 저장소에 파일 하나(`tokens.json`)만. 다른 파일은 생성물이거나 토큰 참조 |
| 먼저 만들고 쓰기 | 맞는 토큰이 없으면 코드에 값을 적지 않고 정본에 토큰 추가 후 사용 |
| 의미로 쓰기 | 코드는 의미 토큰만 참조. 기본 토큰 직접 참조 금지 |
| 테마는 의미 층에서 | 다크 모드, 고대비는 의미 토큰 값만 변경. 구성 요소 코드에 테마 분기 금지 |

토큰 없이 써도 되는 값: `0`, `1`(flex 비율, 불투명), `auto`, `none`, `inherit`, `initial`, `unset`, `currentColor`, `transparent`, `100%`, `50%`(가운데 맞춤), `100vh`, `100vw`

- 토큰 대상 제외: 도형 좌표, 경로, 데이터에서 계산한 크기
- 외부 라이브러리가 요구하는 고정 값: 그 줄에 `tokens-allow: {이유}` 주석. 이유 없는 허용 금지

## 세 층

| 층 | 역할 | 이름 예 | 참조하는 쪽 |
|---|---|---|---|
| 기본(primitive) | 쓸 수 있는 값 목록. 뜻 없음 | `color.blue.600`, `space.4`, `size.text.14` | 의미 토큰만 |
| 의미(semantic) | 용도. 테마마다 값 변경 | `color.accent`, `color.text.muted`, `space.card.pad` | 구성 요소 토큰, 코드 |
| 구성 요소(component) | 한 구성 요소만의 값. 선택 | `button.height`, `tab.gap` | 그 구성 요소 코드 |

- 구성 요소 토큰은 두 곳 이상에서 같은 값이 필요할 때만. 한 곳이면 의미 토큰 직접 사용
- 기본 토큰의 값만 숫자·hex. 의미·구성 요소 토큰의 값은 다른 토큰 참조 `{color.blue.600}`

## 이름

- 형식: `{분류}.{용도}.{변형}.{상태}`. 필요한 칸만, 점으로 구분
- CSS 이름: 점을 `-`로 `--color-accent-hover`. JavaScript 이름: 같은 경로의 객체 `tokens.color.accent.hover`
- 소문자 kebab-case 낱말. 색 이름(`blue`)은 기본 층에만, 의미 층은 용도 이름(`accent`, `danger`)

| 분류 | 담는 값 | 기본 층 단계 예 |
|---|---|---|
| `color` | 색 | `blue.50`~`blue.900`, `gray.0`~`gray.1000` |
| `font` | 글꼴 묶음 | `sans`, `mono` |
| `size.text` | 글자 크기 | 11, 12, 13, 14, 16, 20, 24, 32 |
| `leading` | 줄 높이 | `tight` 1.2, `normal` 1.5 |
| `weight` | 글자 굵기 | 400, 500, 600 |
| `space` | 간격, 여백 | 0, 1(2px), 2(4px), 3(6px), 4(8px), 5(12px), 6(16px), 7(24px), 8(32px), 9(48px) |
| `radius` | 모서리 둥글기 값 | `sm`, `md`, `lg`, `full` |
| `border` | 테두리 두께 | `thin`, `thick` |
| `shadow` | 그림자 | `sm`, `md` |
| `opacity` | 투명도 | `muted`, `faint` |
| `z` | 쌓임 순서 | `base`, `raised`, `overlay`, `modal` |
| `duration` | 시간 | `fast` 150ms, `normal` 250ms, `slow` 400ms |
| `ease` | 이징 | `standard`, `enter`, `exit` |
| `size` | 요소 크기 | `control.sm`, `icon.md` |
| `breakpoint` | 화면 폭 경계 | `sm` 640, `md` 768, `lg` 1024, `xl` 1440 |

- 단계 예는 새 저장소의 시작값. 저장소 정본이 있으면 정본 우선
- 간격 기본 단위 4px, 단계 이름은 숫자 순번. 픽셀 값을 이름에 넣기 금지(`space.16px` X)

## 정본과 생성물

| 파일 | 내용 | 손으로 수정 |
|---|---|---|
| `tokens.json` | 정본. DTCG(Design Tokens Community Group) 2025.10 형식(`$value`, `$type`, `$description`) | 허용 |
| `tokens.dark.json` | 다크 모드에서 바뀌는 의미 토큰만 | 허용 |
| `tokens.css` | 생성물. `:root`의 CSS 사용자 정의 속성, 다크 모드 덮어쓰기 | 금지 |
| `tokens.js` | 생성물. 토큰 경로 객체(값은 `var(--…)`)와 계산용 숫자 | 금지 |

```sh
python3 <이 스킬 폴더>/scripts/build_tokens.py tokens.json --out <생성 폴더>
```

- 위치: 저장소에 화면 코드가 한 곳이면 그 소스 루트, 여럿이면 공유 폴더 하나. 생성물은 커밋
- 생성물 첫 줄: 정본 경로와 `생성물, 손으로 고치지 않음` 주석
- 생성물은 포매터·린터 제외: `.prettierignore`, ESLint `ignores`, Stylelint `ignoreFiles`
- 다크 모드: `@media (prefers-color-scheme: dark)`와 `[data-theme='dark']` 두 곳에 같은 값 생성. `[data-theme='light']`는 밝은 값 강제

## 쓰는 방법

| 자리 | 쓰는 방법 | 예 |
|---|---|---|
| CSS | `var(--토큰)` | `padding: var(--space-4);` |
| CSS 계산 | `calc()` 안 토큰 | `calc(var(--space-4) * 2)` |
| `@media` 조건 | breakpoint 토큰과 같은 숫자. `var()` 사용 불가 | `@media (min-width: 768px)` |
| JavaScript가 만드는 CSS, 인라인 style, SVG 속성 | `tokens.js`의 값(`var(--…)` 문자열) | `` `fill="${tokens.color.accent}"` `` |
| JavaScript 배치 계산 | `tokens.js`의 `values` 숫자 | `values.size.text['14']` |

- 이미지로 넣는 SVG: 스타일시트가 없어 `var()` 값 소실. 그 SVG 안 `<style>`에 `tokens.css` 내용 포함
- 테스트 코드의 기대값도 토큰 참조. 숫자 복사 금지

## 새 값이 필요할 때

1. 의미 토큰 목록에서 같은 용도 찾기
2. 없으면 기본 토큰에서 가장 가까운 단계로 의미 토큰 추가
3. 기본 단계에도 없으면 기본 토큰 추가. 단계 사이 값은 디자인 확인 후만
4. 정본 수정 뒤 생성 스크립트 실행, 생성물과 함께 커밋

- 금지: 코드에 값 먼저 적고 나중에 토큰화, 한 번만 쓴다는 이유의 직접 값, 토큰 값과 같은 숫자 복사

## 검사

```sh
python3 <이 스킬 폴더>/scripts/check_tokens.py <검사할 폴더>
```

- 찾는 것: hex 색, `rgb()`·`hsl()`·`oklch()` 색, 단위가 붙은 길이·시간(`px`, `rem`, `em`, `ms`, `s`), 글꼴 이름, 토큰 파일 밖의 사용자 정의 속성 값, breakpoint 토큰에 없는 `@media` 숫자
- 대상: `.css`, `.scss`, `.html`, `.svg`, `.js`, `.mjs`, `.ts`, `.jsx`, `.tsx`, `.vue`, `.svelte`. JavaScript 계열은 문자열 안만
- 제외: `tokens.json`, `tokens.dark.json`, 생성물, `node_modules`, `dist`, `.git`, `tokens-allow:` 주석이 있는 줄
- 출력 `total 0`까지 수정. 0이 아니면 종료 코드 1
- 스크립트가 못 잡는 것은 직접 확인: 단위 없는 SVG 속성 숫자(`rx="10"`), 기본 토큰 직접 참조, 구성 요소 코드 안 테마 분기
