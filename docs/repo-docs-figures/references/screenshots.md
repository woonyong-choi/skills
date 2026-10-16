# 스크린샷

크기·형식·용량: SKILL.md 규격 절

## 구성

- 단일: 앱 영역만 잘라 단색 배경 위에 둥근 모서리·그림자. 브라우저는 주소창·탭 제외 페이지 안쪽만, 터미널은 창 안쪽만
- 두 장면: 한 파일로 합쳐 좌우 배치, 장면 사이 여백 고정
- 확대: 동그라미·화살표·강조 상자 대신 같은 화면의 해당 영역을 배율 2배로 다시 촬영(clip)해 오른쪽에 배치. 이미지 늘리기 금지
- 마우스 커서·손글씨·이모지 금지
- 배경·여백·모서리·그림자 값: 대상 저장소 디자인 정본 토큰을 `screens.json`의 `style`에. 정본이 없으면 스크립트 기본값(무채색) 사용하고 PR 본문에 기록

## 크기

- 단일: 창 폭 960px, 배율 2 → 최종 파일 폭 1920px(배경 여백 포함)
- 두 장면·확대: 창 폭 640px, 배율 2 → 최종 파일 폭 1920px
- 1MB 초과: 설치된 무손실 압축 도구(oxipng 등). 그래도 넘으면 저장 없이 보고

## 테마

- 라이트·다크 두 장 필수. 문서 삽입은 `picture` 태그

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/{이름}-dark.png">
  <img alt="{결론 한 문장}" src="docs/assets/{이름}-light.png">
</picture>
```

## 데이터

- 합성 데이터만. `.local/screenshots/{실행 id}/`에 만들고 앱을 그 경로로 실행. 개인 문서·실제 계정·토큰·실제 홈 경로 금지
- 촬영 후 그 폴더를 휴지통으로 이동(macOS `trash`, Linux `gio trash`). 휴지통 도구가 없으면 지우지 않고 경로 보고. 영구 삭제 금지

## 촬영 방법

- 웹 화면: Playwright로 창 폭·배율·`colorScheme` 고정 촬영
- 터미널: VHS `Screenshot` 명령으로 창 안쪽 촬영
- 위 둘로 안 되는 데스크톱 앱: 손 캡처 허용. 창 크기·테마·데이터 조건을 PR 본문에 기록
- 만든 PNG의 손 수정 금지, 촬영 목록 원본과 함께 커밋

## 촬영 목록

원본: 대상 저장소 `docs/assets/screens.json`

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

필드 → 규칙:

- `style` → 생략 가능. 생략한 키는 스크립트 기본값
- `name` → 규격 절 이름 규칙
- `url`, `command` → 둘 중 하나. `two`는 두 개 목록. `{data}`는 합성 데이터 폴더 경로로 치환, 명령에는 `SCREENS_DATA` 환경 변수로도 전달
- `layout` → `single`, `two`, `zoom`. 창 폭은 크기 절 기본값, `width`로 바꿀 때 PR 본문에 이유
- `select` → 웹 화면에서 잘라낼 앱 영역 선택자. 생략하면 페이지 전체
- `zoom` → 확대할 영역의 CSS 픽셀 좌표
- `alt` → SKILL.md 대체 글 절

## 실행

```sh
python3 {스킬 폴더}/scripts/screens.py shoot --config docs/assets/screens.json
python3 {스킬 폴더}/scripts/screens.py check --config docs/assets/screens.json
```

- `shoot`: 촬영 → 배경·모서리·그림자 합성 → 두 장면·확대 합치기 → 라이트·다크 PNG 저장. 하나라도 실패하면 기존 PNG 유지, 종료 1
- `check`: 대체 글, 이름, 두 테마 파일, 폭 1920px, 1MB 이하 대조. PR 전 실행
- 실행 조건: Python Playwright와 Chromium, 터미널 화면은 VHS
