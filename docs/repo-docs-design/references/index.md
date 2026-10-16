# docs/README.md

````text
# 문서

{제품 이름}의 설계 문서다. 문서는 {작업 언어}로 쓴다. 처음이면 {시작 문서}부터 읽는다.

- 시작
  - [아키텍처](architecture.md): 구성 요소, 코드 지도, 불변 조건
  - [용어](glossary.md): 이 프로젝트만의 말
- 설계
  - [{문서 제목}](design/{주제}.md): {답하는 것}
    - [{하위 문서}](design/{주제}-{세부}.md): {답하는 것}
- 명세
  - [CLI](cli.md): {답하는 것}
- 기록
  - [결정 기록](decisions/README.md): {답하는 것}
  - [실험](experiments/README.md): {답하는 것}
````

- 첫 문단: 문서 묶음 이름, 작업 언어, 읽기 시작점 세 문장
- 분류: 시작(architecture, glossary) → 설계(`design/`) → 명세(protocol·cli·ui·data·configuration·errors) → 기록(`decisions/README.md`, `experiments/README.md`). 문서가 없는 분류 생략. 분류 안은 읽는 순서
- 문서 줄: `[제목](경로): 답하는 것`(명사구, 20자 안팎). 루트 README의 같은 문서는 같은 제목·같은 설명
- 들여쓰기 최대 3단계(분류 → 문서 → 하위 문서). 하위 문서는 같은 폴더의 `{주제}-{세부}.md`, 목록에서만 들여쓰기. 폴더 추가 금지
