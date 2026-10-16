# 도구와 파일

그림 → 도구 → 원본 → 산출물:

- 구조도, 순서도, 상태도, 데이터 관계도, 차트 → ThinkFlow → `docs/assets/{이름}.thinkflow` → `docs/assets/{이름}.svg`
- 문서 안에서 관리하는 그림 → `thinkflow md` → Markdown의 `thinkflow` 코드 블록 → 문서의 이미지 줄과 SVG(markdown 정본)
- 터미널 데모 → VHS → `docs/assets/{이름}.tape` → `docs/assets/{이름}.gif`

- `.thinkflow` 하나에 그림 하나. 실험 차트 입력: [실험 차트](charts.md)
- 문법 정본: [figure-syntax](https://github.com/woonyong-choi/thinkflow/blob/main/docs/design/figure-syntax.md)와 [reference](https://github.com/woonyong-choi/thinkflow/blob/main/docs/reference). 문법·기본값 복제 금지
- 테마·토큰: ThinkFlow가 의존하는 `@woonyong-choi/design-tokens` 패키지(`node_modules/@woonyong-choi/design-tokens/dist`). 색 역할·대비: [docs-integration](https://github.com/woonyong-choi/thinkflow/blob/main/docs/design/docs-integration.md)
- 문서 안 원본: `thinkflow` 블록과 생성 이미지 줄 보존
