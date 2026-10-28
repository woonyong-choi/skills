# 도구와 파일

DiagramPlay 작업을 시작하기 전에 그림 종류마다 쓰는 도구, 원본, 산출물을 정한다. DiagramPlay의 명령은 `diagramplay`, 원본 확장자는 `.diagramplay`, 저장소는 https://github.com/woonyong-choi/diagramplay 다.

| 그림 | 도구 | 원본 | 산출물 |
|---|---|---|---|
| 아키텍처, 카드 흐름, 시퀀스, ERD, 클래스 다이어그램 | DiagramPlay | `docs/assets/{이름}.diagramplay` | `docs/assets/{이름}.svg` |
| 문서 안에서 관리하는 그림 | `diagramplay md` | Markdown의 `diagramplay` 코드 블록 | 문서의 이미지 줄과 SVG(markdown 정본) |
| 터미널 데모 | VHS | `docs/assets/{이름}.tape` | `docs/assets/{이름}.gif` |

- `.diagramplay` 하나에 다이어그램 하나를 그린다. 요청·응답·이벤트·상태 변화의 실행 표현을 다룬다.
- 문법의 정본은 [figure-syntax](https://github.com/woonyong-choi/diagramplay/blob/main/docs/design/figure-syntax.md)와 [reference](https://github.com/woonyong-choi/diagramplay/blob/main/docs/reference)다. 문법과 기본값을 옮겨 적지 않는다.
- 테마와 토큰은 DiagramPlay가 의존하는 `@woonyong-choi/design-tokens` 패키지(`node_modules/@woonyong-choi/design-tokens/dist`)에서 온다. 색 역할과 대비는 [docs-integration](https://github.com/woonyong-choi/diagramplay/blob/main/docs/design/docs-integration.md)이 정본이다.
- 문서 안 원본은 `diagramplay` 블록과 생성 이미지 줄을 남긴다.

- 클라우드 구성도의 아이콘·그룹·선·생략 기준은 [클라우드 구성도 규칙](cloud-architecture.md)을 먼저 읽는다. 자산 이름은 설치한 카탈로그가 정하며 임시 SVG를 만들지 않는다.

## 기능 범위

통계 차트, 분석용 시계열 플롯과 측정 구간 전용 보기는 제공하지 않는다. 막대·선·영역·원형·분포·산점도·히트맵 등의 차트 선언과 중첩 차트, plot·time·timing 전용 보기 및 추적 구간 분석 기능은 제거 대상이다. 다이어그램의 메시지 시간, 요청 이동, 값 변화와 장면 재생은 유지한다. ERD·테이블·컬럼·PK/FK·복합 키·관계·클래스·인터페이스·API 필드는 유지한다. 데이터 표시를 통계 차트와 혼동해 삭제하지 않는다. 비트·메모리 격자와 전용 상태도는 별도 지원 범위가 아니며 상태 변화는 카드 흐름 안에서 표현한다.

도구를 수정하는 작업에서는 선언 문법, 해석·측정·배치·그리기, 시간표·재생기, 공개 API, 전용 테스트·예제·문서와 생성물의 참조를 함께 정리한다. 제거한 입력은 줄 위치가 있는 일반 문법 오류로 거절하고 출력물을 쓰지 않는다. 예제를 숨기거나 기능 플래그로 감춘 상태를 기능 삭제 완료로 보고하지 않는다. 스킬 기준의 변경과 도구 구현·배포 완료는 각각 확인한다.
