# 도구와 파일

Torso 작업을 시작하기 전에 그림 종류마다 쓰는 도구, 원본, 산출물을 정한다. Torso의 명령은 `torso`, 원본 확장자는 `.torso`, 저장소는 https://github.com/woonyong-choi/torso 다.

| 그림 | 도구 | 원본 | 산출물 |
|---|---|---|---|
| 구조도, 순서도, 상태도, 데이터 관계도, 차트 | Torso | `docs/assets/{이름}.torso` | `docs/assets/{이름}.svg` |
| 문서 안에서 관리하는 그림 | `torso md` | Markdown의 `torso` 코드 블록 | 문서의 이미지 줄과 SVG(markdown 정본) |
| 터미널 데모 | VHS | `docs/assets/{이름}.tape` | `docs/assets/{이름}.gif` |

- `.torso` 하나에 그림 하나를 그린다. 실험 차트 입력은 [실험 차트](charts.md)를 따른다.
- 문법의 정본은 [figure-syntax](https://github.com/woonyong-choi/torso/blob/main/docs/design/figure-syntax.md)와 [reference](https://github.com/woonyong-choi/torso/blob/main/docs/reference)다. 문법과 기본값을 옮겨 적지 않는다.
- 테마와 토큰은 Torso가 의존하는 `@woonyong-choi/design-tokens` 패키지(`node_modules/@woonyong-choi/design-tokens/dist`)에서 온다. 색 역할과 대비는 [docs-integration](https://github.com/woonyong-choi/torso/blob/main/docs/design/docs-integration.md)이 정본이다.
- 문서 안 원본은 `torso` 블록과 생성 이미지 줄을 남긴다.
