# Markdown과 CI

Markdown 문서 안의 `diagramplay` 코드 블록으로 그림을 관리하거나 CI에 연결할 때 따른다.

## 문서 안 그림

- `diagramplay md`로 `diagramplay` 코드 블록에서 SVG를 만들고 이미지 줄을 갱신한다. 블록, 파일 이름, 출력 위치, 오래된 SVG 정리 규칙은 [markdown](https://github.com/woonyong-choi/diagramplay/blob/main/docs/design/markdown.md)이 정본이다. 문법과 기본값을 옮겨 적지 않는다.
- 원본 문서와 생성 SVG를 함께 커밋한다. 생성 이미지 줄의 대체 글은 블록의 `title`에서 오므로 `title`에도 대체 글 규칙을 적용한다.

## 최신성 검사

읽기만 하는 최신성 검사는 아래 명령으로 한다. 쓰는 버전에서 성공과 실패 코드, 파일이 바뀌는지를 확인하고 남긴다.

```sh
node <DiagramPlay 경로>/src/cli.js md <문서 경로>.md --check --strict
node <DiagramPlay 경로>/src/cli.js md <문서 경로>.md --check --strict --static
```

## CI

- 생성 명령과 GitHub Action 연결 예는 [사용법](https://github.com/woonyong-choi/diagramplay/blob/main/docs/usage.md)에 있다. 위 검사와 생성에 같은 출력 옵션을 쓴다.
- Action의 정본은 [action.yml](https://github.com/woonyong-choi/diagramplay/blob/main/action.yml)이다. 추적 파일을 대상으로 원본 검사와 Markdown 최신성 검사를 하고, 생성 모드는 파일만 갱신하며 자동 커밋은 하지 않는다. 입력 문법과 기본값은 정본을 따른다.
- Action 검증 결과에는 로컬 파일을 `action.yml`과 대조했는지와 GitHub에서 실제 실행 결과를 확인했는지를 따로 적는다.
