# 그림 작성

DiagramPlay 그림 원본을 쓰거나 바꿀 때 보여 줄 것에 맞는 정본을 읽고 배치를 정한다.

작성 범위는 [도구와 파일의 기능 범위](diagramplay.md#기능-범위)를 따른다. 차트나 분석 전용 보기를 만드는 문법은 사용하지 않는다.

## 정본 고르기

보여 줄 것에 맞는 정본을 [reference](https://github.com/woonyong-choi/diagramplay/blob/main/docs/reference)에서 읽는다. 네트워크가 막혔으면 쓰는 DiagramPlay 작업본의 `docs/reference/`와 `docs/design/figure-syntax.md`를 읽는다.

| 보여 줄 것 | 정본 |
|---|---|
| 맥락, 구성 요소와 요청 흐름 | `flow.md`, `architecture.md` |
| 메시지 순서 | `sequence.md` |
| 테이블과 외래 키 | `data.md` |
| 클래스·인터페이스·필드·메서드·관계 | `../design/figure-kinds.md`와 클래스 예제 |

## 배치

클라우드 구성도는 [NHN Cloud 구성도 규칙](nhn-cloud.md)을 먼저 따른다. 방향, 그림 나누기와 표시 폭은 [그림 품질](diagramplay-quality.md)의 가로형 원칙과 4절을 따른다. SVG와 HTML은 실제 원본과 도구 버전으로 정지 그림과 재생기를 각각 넣을 환경의 폭에서 확인한다. 가로 넘침뿐 아니라 글자가 읽히는지도 확인한다.

## 내용

- 라벨, 상태, 테이블, 열은 문서 표와 같은 이름과 순서로 쓴다. 연결은 문서에 근거가 있는 관계만 긋는다.
- 맥락 그림에는 외부 요소 표의 요소와 시스템을 그린다. 구성 요소 그림에는 구성 요소 표의 행마다 카드 하나를 그리고, 실제 표시에서 읽기 어려우면 [그림 품질](diagramplay-quality.md) 1절 5번대로 합치거나 나눈다.
- `title`은 그림 주제다. `scene`은 순서나 변화가 이해를 도울 때만 쓴다.
- 그림에 꼭 보여야 할 항목은 머리에 `require "이름" [or "다른 이름"]` 줄로 적는다([그림 품질](diagramplay-quality.md) 1절 3번). 정본은 DiagramPlay `docs/design/figure-quality.md`다.
- 아키텍처, 카드 흐름, ERD, 클래스 그림의 정지 SVG는 장면과 상관없이 선언한 모든 선을 그린다. 순서 그림은 [그림 품질](diagramplay-quality.md#품질이-무너지는-원인)의 장면 규칙을 따른다.
