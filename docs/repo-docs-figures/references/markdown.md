# Markdown과 CI

Markdown 그림 생성·검사 전 [검사](validation.md) 필수 확인

- 문서 안 그림 관리: `daphnis md`로 `dap` 코드 블록에서 SVG 생성과 이미지 줄 갱신. 블록·파일 이름·출력 위치·오래된 SVG 정리 규칙: [markdown](https://github.com/woonyong-choi/daphnis/blob/main/docs/design/markdown.md). 문법·기본값 복제 금지
- 원본 문서와 생성 SVG 함께 커밋. 생성 이미지 줄의 대체 글은 블록의 `title`에서 결정하므로 `title`도 대체 글 규칙 적용
- 읽기 전용 최신성 검사: 아래 명령. 사용 버전에서 성공·실패 코드와 파일 변경 여부 확인·기록

```sh
node <daphnis 경로>/src/cli.js md <문서 경로>.md --check --strict
node <daphnis 경로>/src/cli.js md <문서 경로>.md --check --strict --static
```

- 생성 명령과 GitHub Action 연결 예: [README 사용법](https://github.com/woonyong-choi/daphnis/blob/main/README.md#keep-figures-in-a-markdown-document). 위 검사와 생성에 같은 출력 옵션 사용
- Action 정본: [action.yml](https://github.com/woonyong-choi/daphnis/blob/main/action.yml). 추적 파일 대상으로 원본 검사와 Markdown 최신성 검사, 생성 모드는 파일 갱신만 수행하고 자동 커밋 없음. 입력 문법·기본값은 정본 참조
- Action 검증 결과에는 로컬 파일을 `action.yml`과 대조했는지, GitHub에서 실제 실행 결과를 확인했는지 각각 기록
