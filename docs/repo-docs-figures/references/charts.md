# 실험 차트

DiagramPlay로 실험 결과 차트를 쓰거나 바꿀 때 값을 결과 파일에서 읽어 오게 한다.

## 값

- 값을 손으로 적지 않는다. 부제의 표본 수만 예외다.
- `data "../experiments/{실험}/results/summary.json" at "/배열"`로 원본 기준 상대 경로와 JSON Pointer를 준다(charts 값 출처).
- JSON 배열 형식이 다르면 `03-analyze`가 차트용 배열을 `results/summary.json` 안에 만든다. 원소에는 그 종류의 이름 키(막대는 `label`), 계열 키, `.low`, `.high`만 둔다. 다른 키는 `--strict`에서 실패하므로 표본 수 n 같은 값은 같은 파일의 다른 키에 둔다.
- 계열 키는 `series`의 `key=`나 계열 이름이다. 신뢰구간은 같은 키의 `.low`, `.high`다. 행 키, 결측값, 계열 수는 charts 값 출처 정본을 따른다.
- `data`와 인라인 `row`, `point`, `cell`을 섞지 않는다. 예시 데이터만 자리표시 규칙에 따라 인라인 값을 쓸 수 있다(repo-docs 자리표시).

## 글

- `title`은 측정 대상 명사구다. 문서 안 블록이면 대체 글 규칙을 적용한다.
- `subtitle`은 표본 수와 기준선 설명이다. 표본 수는 `results/summary.json`의 n 값을 옮겨 적고 검사에서 대조한다.
- 값 축 제목에는 괄호 안에 단위를 쓴다.

## 구분

- 통계와 신뢰구간이 필요한지는 실험 계획과 repo-docs-experiment 통계 규칙이 정한다.
- 계열 역할과 색은 DiagramPlay docs-integration 정본이 정한다.
