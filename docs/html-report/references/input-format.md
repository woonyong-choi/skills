# 입력 JSON

입력 JSON 예(외부 파일 없이 생성 가능):

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

| 입력 | 필수·형식 |
|---|---|
| 최상위 | `title`, `intro`, `questions` 필수. `kind`는 `decision` 또는 `result`, 생략 시 decision |
| 질문 | `title`, `what`, `options`, `effect`, `rec` 필수 |
| 선택지 | `label` 필수. `images`, `table`, `text`, `mock`은 해당 자료가 있을 때 |
| 그림 | `dap`, `inline`, `src` 중 하나와 `alt`. 경로는 입력 폴더 기준. `max_height`의 의미는 [구성 절의 이미지 항목](../SKILL.md#구성) 참조 |
| 표 | `head`, `rows` 필수. `align`, `widths` 선택 |
| 보충 | `check`, `note`, `extra` 선택. extra 항목은 `title`과 실제 options 필요, 빈 예시 삽입 금지 |
