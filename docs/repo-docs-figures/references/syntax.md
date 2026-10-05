# 그림 작성

| 보여 줄 것 | 종류·선언 | 정본 |
|---|---|---|
| 맥락, 구성 요소와 요청 흐름 | `flow right` 또는 `flow down`, `person`, `box`, `external`, `store`, `group` | figure-syntax |
| 메시지 순서 | `sequence`, 참여자 선언 뒤 `step` 안 메시지 | [figure-kinds](https://github.com/woonyong-choi/daphnis/blob/main/docs/design/figure-kinds.md) |
| 상태와 전이 | `state down`, `state`, `start`, `final` | figure-kinds |
| 테이블과 외래 키 | `data right`, `table`, 열의 `fk=` | figure-kinds |
| 비트 필드, 배열, 스택, 행렬 | `flow`, `grid`, `item`, `gap` | [grid](https://github.com/woonyong-choi/daphnis/blob/main/docs/design/grid.md) |
| 조건별 값과 신뢰구간, 행마다 다른 기준(`rule=`) | 막대 | [charts](https://github.com/woonyong-choi/daphnis/blob/main/docs/design/charts.md) |
| 같은 입력에서 두 방식의 값 비교 | 덤벨 | charts |
| 연속값 분포 | 상자 | charts |
| 두 변수의 관계 | 산점도 | charts |
| 순서·시간에 따른 변화, 작은 변화의 축 확대(`zero off`) | 선 | charts |
| 판정 교차표 | 히트맵 | charts |
| 음수일 수 있는 차이 값과 신뢰구간, 0선·음수 기준선 | 차이(`chart difference`) | charts |

- 차트 선언·값 출처·축 제약: charts 정본. 차이 값은 차이 차트, 조건별 원래 값은 막대·덤벨 선택. 막대 행 기준과 공통 기준선 구분, 선 차트 축 확대 시 잘림 표시 확인

- 라벨·상태·테이블·열: 문서 표와 같은 이름과 순서. 연결: 문서에 근거가 있는 관계만
- 맥락 그림: 외부 요소 표의 요소와 시스템. 구성 요소 그림: 구성 요소 표의 행마다 도형 하나
- `title`: 그림 주제. `subtitle`: 보충 설명. `step`: 읽을 순서와 설명, 이동·강조·계열 드러내기는 해당 그림 종류 문법
- 배치·글꼴 내장: [layout](https://github.com/woonyong-choi/daphnis/blob/main/docs/design/layout.md). 움직임·정지 출력 의미: [playback](https://github.com/woonyong-choi/daphnis/blob/main/docs/design/playback.md)
- 정지 SVG: 모든 선과 차트 계열 표시, 빈 카드. 특정 단계 캡처로 간주 금지
