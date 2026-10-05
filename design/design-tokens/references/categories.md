# 토큰 분류·단계

| 분류 | 담는 값 | 기본 층 단계 예 |
|---|---|---|
| `color` | 색 | `blue.50`~`blue.900`, `gray.0`~`gray.1000` |
| `font` | 글꼴 묶음 | `sans`, `mono` |
| `size.text` | 글자 크기 | 11, 12, 13, 14, 16, 20, 24, 32 |
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

- 표의 단계 값은 그대로 따라야 하는 규칙이 아닌 예시. 실제 값은 적용 화면의 대비·배치 요구와 저장소의 토큰 정의 파일을 확인해 결정
- 간격의 기본 단위와 그 배수에 맞지 않는 단계의 이유는 토큰 정의 파일에 명시. 표의 2px·6px도 예시. 단계 이름은 순번, 픽셀 값을 이름에 넣기 금지(`space.16px` X)
