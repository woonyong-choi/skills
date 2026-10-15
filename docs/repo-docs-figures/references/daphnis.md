# 도구와 파일

그림 → 도구 → 원본 → 산출물:

- 구조도, 순서도, 상태도, 데이터 관계도, 차트 → daphnis → `docs/assets/{이름}.dap` → `docs/assets/{이름}.svg`
- 문서 안에서 관리하는 그림 → daphnis md → Markdown의 `dap` 코드 블록 → 문서의 이미지 줄과 SVG(markdown 정본)
- 터미널 데모 → VHS → `docs/assets/{이름}.tape` → `docs/assets/{이름}.gif`

- `.dap` 하나에 그림 하나. 이름: 영어 소문자 kebab-case
- 실험 차트도 같은 위치. 입력: [실험 차트](charts.md)
- 그림 문법 정본: [figure-syntax](https://github.com/woonyong-choi/daphnis/blob/main/docs/design/figure-syntax.md)의 문법 표와 호환 규칙. 문법·기본값 복제 금지
- 어댑터 토큰: daphnis `src/tokens.css`. 색 역할·대비와 지원 테마는 [docs-integration](https://github.com/woonyong-choi/daphnis/blob/main/docs/design/docs-integration.md) 참조. 대상 저장소의 디자인 정본과 맞지 않으면 공통 규칙을 만족하는 다른 어댑터 선택
- 문서 안 원본: `dap` 블록과 생성 이미지 줄 보존, Markdown 표는 기존 문서 규칙 적용
