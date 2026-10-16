# docs/README.md

`docs/README.md` 문서 목록을 쓰거나 갱신하거나 검토할 때 이 틀을 쓴다.

````text
# 문서

{제품 이름}의 설계 문서다. 문서는 {작업 언어}로 쓴다. 처음이면 {시작 문서}부터 읽는다.

## 시작

- [아키텍처](architecture.md): 구성 요소, 처리 흐름, 지켜야 할 규칙
- [용어](glossary.md): 이 프로젝트만의 말

## 설계

- [{문서 제목}](design/{주제}.md): {답하는 것}
  - [{하위 문서}](design/{주제}-{세부}.md): {답하는 것}

## 명세

- [CLI](cli.md): {답하는 것}

## 기록

- [결정 기록](decisions/README.md): {답하는 것}
- [실험](experiments/README.md): {답하는 것}
````

- 첫 문단은 문서 묶음 이름, 작업 언어, 읽기 시작점 세 문장이다.
- 분류는 시작(architecture, glossary), 설계(`design/`), 명세(protocol, cli, ui, data, configuration, errors), 기록(`decisions/README.md`, `experiments/README.md`) 순서다. 문서가 없는 분류는 뺀다. 분류 안은 읽는 순서로 놓는다.
- 문서 줄은 `[제목](경로): 답하는 것`이다. 답하는 것은 20자 안팎의 명사구다. 루트 README에 같은 문서가 있으면 같은 제목과 같은 설명을 쓴다.
- 분류는 `##` 절이고 목록 줄은 모두 문서 줄이다. 링크 없는 목록 줄을 쓰지 않는다. repo-docs-llms가 오류로 끝난다.
- 단계는 분류, 문서, 하위 문서의 3단계까지다. 하위 문서는 같은 폴더의 `{주제}-{세부}.md`이고 목록에서만 들여 쓴다. 폴더를 더하지 않는다.
