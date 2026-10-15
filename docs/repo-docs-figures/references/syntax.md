# 그림 작성

보여 줄 것 → 정본([reference](https://github.com/woonyong-choi/thinkflow/blob/main/docs/reference)):

- 맥락, 구성 요소와 요청 흐름 → `flow.md`, `architecture.md`
- 메시지 순서 → `sequence.md`
- 상태와 전이 → `state.md`
- 테이블과 외래 키 → `data.md`
- 비트 필드, 배열, 스택, 행렬 → `grid.md`
- 조건별 값·신뢰구간, 비교, 분포, 관계, 변화, 교차표, 차이 → `charts.md`. 차이 값은 차이 차트, 조건별 원래 값은 막대·덤벨

- 배치: 가로 기본(`view graph` 생략), `view graph down`은 위아래 의미가 있을 때만
- 세로 전환: 카드 수가 아닌 배치 폭 기준. 카드 글·선 라벨·분기 층을 포함한 가로 배치가 캔버스(기본 960px, 머리 `width wide` 1440px)를 넘으면 ThinkFlow의 세로 전환이나 접기. 렌더 SVG가 세로면 `width wide` 추가, 그래도 세로면 글 축약이나 의미 단위로 분할
- 좁은 화면(모바일 분기점 미만) HTML: ThinkFlow가 미리 만든 좁은 배치(대개 세로)로 교체, 남는 폭은 그림 안 가로 스크롤. 잘림 여부는 실제 폭에서 확인
- 라벨·상태·테이블·열: 문서 표와 같은 이름과 순서. 연결: 문서에 근거가 있는 관계만
- 맥락 그림: 외부 요소 표의 요소와 시스템. 구성 요소 그림: 구성 요소 표의 행마다 카드 하나
- `title`: 그림 주제. `scene`: 순서·변화가 이해를 도울 때만
- 정지 SVG: 모든 선과 차트 계열 표시. 특정 장면 캡처로 간주 금지
