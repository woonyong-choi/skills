# 실험 차트

- 값 손 기재 금지. `data "../experiments/{실험}/results/summary.json" at "/배열"`로 원본 기준 상대 경로와 JSON Pointer 지정(charts 값 출처)
- JSON 배열 형식이 다르면 `03-analyze`에서 차트용 JSON 생성. 수치 재입력 금지
- 계열 키: `series`의 `key=` 또는 계열 이름. 신뢰구간: 같은 키의 `.low`, `.high`. 행 키·결측값·계열 수: charts 값 출처 정본
- `data`와 인라인 `row`·`point`·`cell` 혼용 금지. 예시 데이터만 자리표시 규칙에 따른 인라인 값 허용(repo-docs 자리표시)
- `title`: 측정 대상 명사구. 문서 안 블록은 대체 글 규칙 적용. `subtitle`: 표본 수와 기준선 설명. 값 축 제목: 괄호 안 단위
- 통계·신뢰구간 필요 여부: 실험 설계와 통계 규칙(repo-docs-experiment 통계 규칙). 계열 역할·색: docs-integration 정본
