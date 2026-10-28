# 도구와 파일

DiagramPlay 작업을 시작하기 전에 그림 종류마다 쓰는 도구, 원본, 산출물을 정한다. DiagramPlay의 명령은 `diagramplay`, 원본 확장자는 `.diagramplay`, 저장소는 https://github.com/woonyong-choi/diagramplay 다.

| 그림 | 도구 | 원본 | 산출물 |
|---|---|---|---|
| 구조도, 순서도, 상태도, 데이터 관계도, 차트 | DiagramPlay | `docs/assets/{이름}.diagramplay` | `docs/assets/{이름}.svg` |
| 문서 안에서 관리하는 그림 | `diagramplay md` | Markdown의 `diagramplay` 코드 블록 | 문서의 이미지 줄과 SVG(markdown 정본) |
| 터미널 데모 | VHS | `docs/assets/{이름}.tape` | `docs/assets/{이름}.gif` |

- `.diagramplay` 하나에 그림 하나를 그린다. 실험 차트 입력은 [실험 차트](charts.md)를 따른다.
- 문법의 정본은 [figure-syntax](https://github.com/woonyong-choi/diagramplay/blob/main/docs/design/figure-syntax.md)와 [reference](https://github.com/woonyong-choi/diagramplay/blob/main/docs/reference)다. 문법과 기본값을 옮겨 적지 않는다.
- 테마와 토큰은 DiagramPlay가 의존하는 `@woonyong-choi/design-tokens` 패키지(`node_modules/@woonyong-choi/design-tokens/dist`)에서 온다. 색 역할과 대비는 [docs-integration](https://github.com/woonyong-choi/diagramplay/blob/main/docs/design/docs-integration.md)이 정본이다.
- 문서 안 원본은 `diagramplay` 블록과 생성 이미지 줄을 남긴다.

- 클라우드 구성도의 아이콘·그룹·선·생략 기준은 [NHN Cloud 구성도 규칙](nhn-cloud.md)을 먼저 읽는다. 자산 이름은 설치한 카탈로그가 정하며 임시 SVG를 만들지 않는다.
