# 스크린샷

스크린샷을 찍거나 합칠 때, `screens.json`을 쓰거나 바꿀 때 따른다. 크기, 형식, 용량은 [규격 절](../SKILL.md#규격)을 따른다.

## 구성

- 한 장면은 앱 영역만 잘라 단색 배경 위에 둥근 모서리와 그림자를 붙인다. 브라우저는 주소창과 탭을 빼고 페이지 안쪽만, 터미널은 창 안쪽만 찍는다.
- 두 장면은 한 파일로 합쳐 좌우로 놓고 장면 사이 여백을 고정한다.
- 확대는 동그라미, 화살표, 강조 상자 대신 같은 화면의 그 영역을 배율 2배로 다시 찍어(clip) 오른쪽에 놓는다. 이미지를 늘리지 않는다.
- 마우스 커서, 손글씨, 이모지를 넣지 않는다.
- 배경, 여백, 모서리, 그림자 값은 대상 저장소 디자인 정본 토큰을 `screens.json`의 `style`에 넣는다. 정본이 없으면 스크립트 기본값(무채색)을 쓰고 PR 본문에 적는다.

## 크기

- 한 장면은 창 폭 960px, 배율 2로 찍어 최종 파일 폭을 1920px(배경 여백 포함)로 만든다.
- 두 장면과 확대는 창 폭 640px, 배율 2로 찍어 최종 파일 폭을 1920px로 만든다.
- 1MB를 넘으면 설치된 무손실 압축 도구(oxipng 등)를 쓴다. 그래도 넘으면 저장하지 않고 보고한다.

## 테마

라이트와 다크 두 장을 반드시 찍는다. 문서에는 `picture` 태그로 넣는다.

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/{이름}-dark.png">
  <img alt="{결론 한 문장}" src="docs/assets/{이름}-light.png">
</picture>
```

## 데이터

- 합성 데이터만 쓴다. 작업 저장소의 `.local/runs/screenshots-{실행 id}/`에 만들고 앱을 그 경로로 실행한다. git 저장소 밖이면 촬영을 멈춘다. 개인 문서, 실제 계정, 토큰, 실제 홈 경로를 쓰지 않는다.
- 찍은 뒤 그 폴더를 휴지통으로 옮긴다(macOS `trash`, Linux `gio trash`). 휴지통 도구가 없으면 지우지 않고 경로를 보고한다. 영구 삭제하지 않는다.

## 촬영 방법

- 웹 화면은 Playwright로 창 폭, 배율, `colorScheme`을 고정해 찍는다.
- 터미널은 VHS `Screenshot` 명령으로 창 안쪽을 찍는다.
- 위 둘로 안 되는 데스크톱 앱만 손으로 캡처한다. 창 크기, 테마, 데이터 조건을 PR 본문에 적는다.
- 만든 PNG를 손으로 고치지 않고 촬영 목록 원본과 함께 커밋한다.

## 촬영 목록

원본은 대상 저장소의 `docs/assets/screens.json`이다.

```json
{
  "style": {"padding": 48, "gap": 32, "radius": 12, "shadow": "0 8px 24px rgba(0, 0, 0, 0.18)", "background": {"light": "#e5e5e5", "dark": "#262626"}},
  "screens": [
    {"name": "{이름}", "url": "{대상 URL}", "layout": "single", "select": "{잘라낼 영역 선택자}", "alt": "{결론 한 문장}"},
    {"name": "{이름}", "url": ["{장면 1 URL}", "{장면 2 URL}"], "layout": "two", "alt": "{두 장면을 비교한 결론 한 문장}"},
    {"name": "{이름}", "command": "{터미널 명령}", "layout": "zoom", "zoom": {"x": 0, "y": 0, "width": 320, "height": 160}, "alt": "{결론 한 문장}"}
  ]
}
```

| 필드 | 규칙 |
|---|---|
| `style` | 뺄 수 있다. 뺀 키는 스크립트 기본값을 쓴다 |
| `name` | 규격 절의 이름 규칙을 따른다 |
| `url`, `command` | 둘 중 하나를 쓴다. `two`는 두 개짜리 목록이다. `{data}`는 합성 데이터 폴더 경로로 바뀌고, 명령에는 `SCREENS_DATA` 환경 변수로도 넘어간다 |
| `layout` | `single`, `two`, `zoom` 중 하나다. 창 폭은 크기 절 기본값을 쓰고, `width`로 바꾸면 PR 본문에 이유를 적는다 |
| `select` | 웹 화면에서 잘라 낼 앱 영역의 선택자다. 빼면 페이지 전체를 쓴다 |
| `zoom` | 확대할 영역의 CSS 픽셀 좌표다 |
| `alt` | [대체 글 절](../SKILL.md#대체-글)을 따른다 |

## 실행

Python Playwright와 Chromium이 필요하고, 터미널 화면에는 VHS가 필요하다.

```sh
python3 {스킬 폴더}/scripts/screens.py shoot --config docs/assets/screens.json
python3 {스킬 폴더}/scripts/screens.py check --config docs/assets/screens.json
```

- `shoot`은 찍고, 배경과 모서리와 그림자를 합치고, 두 장면과 확대를 합친 뒤 라이트와 다크 PNG를 저장한다. 하나라도 실패하면 기존 PNG를 그대로 두고 종료 코드 1로 끝난다.
- `check`는 대체 글, 이름, 두 테마 파일, 폭 1920px, 1MB 이하를 대조한다. PR 전에 실행한다.
