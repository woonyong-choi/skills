# 토큰 분류와 단계

토큰 분류나 단계를 새로 만들거나 바꿀 때 이 표의 이름과 단계 예를 기준으로 쓴다.

| 분류 | 담는 값 | 기본 층 단계 예 |
|---|---|---|
| `color` | 색 | `blue.50`~`blue.900`, `gray.0`~`gray.1000` |
| `font` | 글꼴 묶음 | `sans`, `mono` |
| `size.text` | 글자 크기(`rem`) | `xs`, `sm`, `md`, `lg`, `xl` |
| `leading` | 줄 높이 | `tight` 1.2, `normal` 1.5 |
| `weight` | 글자 굵기 | 400, 500, 600 |
| `tracking` | 자간 | `tight` 0.03em, `wide` 0.04em |
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

- 단계 값은 예시다. 실제 값은 적용 화면의 대비와 배치 요구, 저장소의 토큰 정의 파일로 정한다.
- 간격의 기본 단위 배수에 맞지 않는 단계는 그 이유를 토큰 정의 파일에 적는다.
- 단계 이름은 순번이나 크기 이름으로 쓴다. 값이나 단위가 든 이름(`space.16px`)은 쓰지 않는다.
