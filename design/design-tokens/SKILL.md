---
name: design-tokens
description: "UI의 색·글꼴·간격·시간 값을 토큰으로 정의·사용하거나 하드코딩을 검사할 때 사용."
---

# Design Tokens

- 우선순위: 해당 주제의 사용자 지시 → 저장소 규칙 → 이 스킬. 중복 규칙은 머리에 연결한 정본 스킬 적용
- 범위: 화면에 보이는 모든 값의 정의, 이름, 사용 방법, 하드코딩 검사
- 필요할 때만 읽기: CSS 작성 → code-style-css; JavaScript 작성 → code-style-javascript; 문서 그림 색·글꼴·크기 → repo-docs-figures; 기대값 근거 확인 → code-style

## 원칙

| 원칙 | 규칙 |
|---|---|
| 하드코딩 금지 | 색, 글꼴, 글자 크기, 줄 높이, 자간, 간격, 반지름, 테두리 두께, 그림자, 투명도, z-index, 시간, 이징, 크기, breakpoint 값은 토큰으로만 사용. 먼저 아래 토큰 대상 제외 항목인지 확인. 해당하지 않으면 외부 라이브러리가 요구하는 고정 값인지 확인. 그다음 토큰 없이 써도 되는 값 목록 확인. 어느 항목에도 해당하지 않으면 토큰 사용 |
| 직접 수정할 파일 | 기본값은 `tokens.json`, 테마에서 바뀌는 값은 `tokens.dark.json` 같은 테마 파일에서 관리. 다른 파일은 이 파일들로 생성하거나 토큰을 참조 |
| 먼저 만들고 쓰기 | 맞는 토큰이 없으면 코드에 값을 적지 않고 정본에 토큰 추가 후 사용 |
| 의미로 쓰기 | 색·그림자: 의미 토큰만. 그 밖 분류(간격, 크기, 반지름, 글자 크기, 시간 등): 기본 토큰 허용 |
| 테마는 의미 층에서 | 다크 모드, 고대비는 의미 토큰 값만 변경. 토큰 파일 밖 테마 분기 금지. 테마 전환 코드(사용자 선택 읽기·저장)는 그 줄에 `tokens-allow: {이유}` |

토큰 없이 써도 되는 값: `0`, `1`(flex 비율, 불투명), `auto`, `none`, `inherit`, `initial`, `unset`, `currentColor`, `transparent`, `100%`, `50%`(가운데 맞춤), `100vh`, `100vw`

- 토큰 대상 제외: 도형 좌표, 경로, 데이터에서 계산한 크기
- 문서 그림 토큰·색 역할·대비: (repo-docs-figures 도구와 파일). 이 스킬의 토큰을 그림 원본에 복제 금지
- 외부 라이브러리가 요구하는 고정 값: 그 줄에 `tokens-allow: {이유}` 주석. 이유 없는 허용 금지

## 세 층

| 층 | 역할 | 이름 예 | 참조하는 쪽 |
|---|---|---|---|
| 기본(primitive) | 쓸 수 있는 값 목록. 뜻 없음 | `color.blue.600`, `space.4`, `size.text.14` | 의미 토큰. 색·그림자 밖 분류는 코드도 |
| 의미(semantic) | 용도. 테마마다 값 변경 | `color.accent`, `color.text.muted`, `space.card.pad` | 구성 요소 토큰, 코드 |
| 구성 요소(component) | 한 구성 요소만의 값. 선택 | `button.height`, `tab.gap` | 그 구성 요소 코드 |

- 한 구성 요소의 값만 바꾸고 다른 구성 요소의 값은 유지해야 하면 구성 요소 토큰 사용. 그런 변경이 필요하지 않으면 의미 토큰 직접 사용
- 기본 토큰의 값만 숫자·hex. 의미·구성 요소 토큰의 값은 다른 토큰 참조 `{color.blue.600}`

## 이름

- 형식: `{분류}.{용도}.{변형}.{상태}`. 중복 없이 용도·상태를 식별하는 칸만 사용, 점으로 구분
- CSS 이름: 점을 `-`로 `--color-accent-hover`. JavaScript 이름: 같은 경로의 객체 `tokens.color.accent.hover`
- 소문자 kebab-case 낱말. 색 이름(`blue`)은 기본 층에만, 의미 층은 용도 이름(`accent`, `danger`)

토큰 분류·단계를 신설하거나 변경할 때 [분류·단계](references/categories.md) 필수 확인

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

## 새 값이 필요할 때

1. 색·그림자: 같은 용도의 의미 토큰 찾기. 없으면 의미·대비 조건을 충족하는 기본 색 단계로 의미 토큰 추가
2. 그 밖 분류: 기본 단계에서 고르기
3. 기존 단계로 충족 못 하는 조건과 적용 화면을 기록하고 기본 토큰 추가
4. 정본 수정 뒤 생성 스크립트 실행, 생성물과 함께 커밋

- 금지: 코드에 값 먼저 적고 나중에 토큰화, 한 번만 쓴다는 이유의 직접 값, 토큰 값과 같은 숫자 복사

## 검사

```sh
python3 <이 스킬 폴더>/scripts/check_tokens.py <검사할 폴더>
```

- 찾는 것: hex 색, 색 함수(`rgb()`, `oklch()` 등), 단위 붙은 길이·시간, 단위 없는 굵기·줄 높이·투명도·z-index·자간, 크기 표현 속성 숫자(`rx`, `stroke-width` 등), 글꼴 이름, 토큰 파일 밖 사용자 정의 속성 값, breakpoint 토큰에 없는 `@media`·`@container` 숫자, 색·그림자 기본 토큰 직접 참조, 토큰 파일 밖 테마 분기(`prefers-color-scheme`, `[data-theme`), 스타일 객체 숫자(`{ fontWeight: 600 }`)
- CSS 계열: 주석 밖 전체. 마크업 계열(`.html`, `.svg`, `.vue`, `.svelte`): `<style>`, `style` 속성, 표현 속성만. JavaScript 계열: 주석 밖 모든 문자열의 색, CSS·마크업 모양 문자열과 값 하나뿐인 문자열(`'12px'`)의 나머지 규칙, 코드의 토큰 경로(`tokens.color.blue['600']`), 스타일 객체(`style`, `sx`, `css`) 안 숫자
- 제외: `tokens.json`, `tokens.dark.json`, 생성물 표시 또는 명시한 산출물 경로, `node_modules`, `dist`, `build`, `.git`, 비어 있지 않은 이유를 가진 `tokens-allow:` 줄
- 출력 `total 0`까지 수정. 0이 아니면 종료 코드 1
- 직접 확인: 토큰 이름이 용도를 드러내는지, 구성 요소 토큰이 다른 구성 요소의 값을 유지한 채 그 구성 요소의 값만 바꾸는 데 필요한지, `style`·`sx`·`css` 밖 이름의 스타일 객체 숫자
- 기대값 근거: (code-style 테스트). 화면 구현값의 하드코딩과 검증 기대값 구분
