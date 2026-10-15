# 그림 작성

보여 줄 것 → 정본([reference](https://github.com/woonyong-choi/thinkflow/blob/main/docs/reference)):

- 맥락, 구성 요소와 요청 흐름 → `flow.md`, `architecture.md`
- 메시지 순서 → `sequence.md`
- 상태와 전이 → `state.md`
- 테이블과 외래 키 → `data.md`
- 비트 필드, 배열, 스택, 행렬 → `grid.md`
- 조건별 값·신뢰구간, 비교, 분포, 관계, 변화, 교차표, 차이 → `charts.md`. 차이 값은 차이 차트, 조건별 원래 값은 막대·덤벨

- 가로 배치 기본(`view graph` 생략). 한 줄 카드 4개 이하는 기본 캔버스, 5~6개는 `width wide`, 7개 이상은 ThinkFlow가 세로로 돌리므로 그림을 나눔
- 라벨·상태·테이블·열: 문서 표와 같은 이름과 순서. 연결: 문서에 근거가 있는 관계만
- 맥락 그림: 외부 요소 표의 요소와 시스템. 구성 요소 그림: 구성 요소 표의 행마다 카드 하나
- `title`: 그림 주제. `scene`: 순서·변화가 이해를 도울 때만
- 정지 SVG: 모든 선과 차트 계열 표시. 특정 장면 캡처로 간주 금지
