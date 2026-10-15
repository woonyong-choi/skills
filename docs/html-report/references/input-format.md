# 입력 JSON

설명 페이지 예:

```json
{
  "kind": "explain",
  "title": "주문 처리 구조",
  "lead": "주문은 API가 받고 큐를 거쳐 워커가 처리한다",
  "sections": [
    {"title": "전체 흐름", "text": ["API는 주문을 큐에 넣고 바로 응답한다"], "figure": "overview.thinkflow", "caption": "주문이 저장되기까지"}
  ]
}
```

- `explain` → `title`, `lead`, `sections` 필수. 절은 `title`, `text`(문단 배열) 필수. 선택: `figure`(`.thinkflow`, 파일 이름 중복 금지), `image`(png·gif·jpg·webp·svg), `caption`, `files`(내려받을 데이터 경로 배열). `image`·`files`는 `attachments/`에 복사

비교 보고서 예(외부 파일 없이 생성 가능):

```json
{
  "kind": "decision",
  "title": "배치 비교",
  "intro": "아래는 배치 모형이며 실제 제품 화면이 아님",
  "questions": [{
    "title": "목록 위치", "what": "목록과 상세의 읽는 순서 비교",
    "options": [
      {"label": "A", "mock": true, "text": "모형: 목록 다음 상세"},
      {"label": "B", "mock": true, "text": "모형: 목록과 상세 병렬"}
    ],
    "effect": [["A", "읽는 순서 유지", "상세까지 이동 필요"], ["B", "동시 비교 가능", "표시 폭 필요"]],
    "rec": ["A", "순차 읽기가 수용 조건인 경우"]
  }]
}
```

입력 → 필수·형식:

- 비교 최상위 → `title`, `intro`, `questions` 필수. `kind`는 `decision` 또는 `result`, 생략 시 decision
- 질문 → `title`, `what`, `options`, `effect`, `rec` 필수
- 선택지 → `label` 필수. `images`, `table`, `text`, `mock`은 해당 자료가 있을 때
- 그림 → `thinkflow`, `inline`, `src` 중 하나와 `alt`. 경로는 입력 폴더 기준. `max_height`: (SKILL 비교 보고서)
- 표 → `head`, `rows` 필수. `align`, `widths` 선택
- 보충 → `check`, `note`, `extra` 선택. extra 항목은 `title`과 실제 options 필요, 빈 예시 삽입 금지

## 선택 기능

- 켜기: 최상위 `review`에 검토 대상 버전 문자열(`"review": "화면 초안 1"`). 후보별 선택 버튼·의견 입력칸, 질문별 재작업·보류·필터·결과 복사. 생략 시 읽기 전용 보고서
- 후보 식별자: 질문·선택지 순서로 생성. 입력·그림·버전 변경 시 HTML 재생성
- 판정 보관: 생성 내용과 외부 그림 바이트의 해시별 브라우저 저장, 이전 승인 승계 없음. 저장 실패는 화면 표시
- 복사 결과: 대상 제목·버전·보고서 해시·질문 ID·후보 ID와 이름·의견. 복사가 막히면 결과 텍스트 직접 복사 후 대화에 붙여넣기. 페이지 선택만으로 AI 전송 없음. AI는 해당 보고서와 값 대조, 미판정·보류 유지
- 질문별 결과: `choice`와 `options`. `options`는 모든 후보의 `id`, `label`, `note`, 선택하지 않은 후보의 의견도 보존. 의견 입력은 선택과 독립
