# docs/README.md

`docs/README.md` 문서 목록을 쓰거나 갱신하거나 검토할 때 이 틀을 쓴다.

````text
# 문서

{제품 이름}의 설계 문서다. 문서는 {작업 언어}로 쓴다. 처음이면 {시작 문서}부터 읽는다.

- 시작
  - [아키텍처](architecture.md)
  - [용어](glossary.md)
- 설계
  - [{주제}](design/{주제}.md)
    - [{세부}](design/{주제}-{세부}.md)
- 명세
  - [CLI](cli.md)
- 기록
  - [결정 기록](decisions/README.md)
  - [실험](experiments/README.md)
````

- 첫 문단은 문서 묶음 이름, 작업 언어, 읽기 시작점 세 문장이다.
- 분류는 시작(architecture, glossary), 설계(`design/`), 명세(protocol, cli, ui, data, configuration, errors), 기록(`decisions/README.md`, `experiments/README.md`) 순서다. 문서가 없는 분류는 뺀다. 분류 안은 읽는 순서로 놓는다.
- 분류부터 문서까지 키워드만 쓰는 글머리 목록으로 둔다. 하위 키워드는 공백 두 칸씩 들여 쓴다. 쌍점과 설명은 붙이지 않는다.
- 문서가 있는 키워드는 `[키워드](경로)`로 쓴다. 분류나 하위 주제 키워드는 링크 없이 쓸 수 있다. 루트 README에 같은 문서를 연결하면 같은 키워드를 쓰고, 링크는 루트 README 기준 상대 경로로 바꾼다.
- 단계는 분류, 문서, 하위 문서의 3단계까지다. 하위 문서는 같은 폴더의 `{주제}-{세부}.md`이고 목록에서만 들여 쓴다. 폴더를 더하지 않는다.
