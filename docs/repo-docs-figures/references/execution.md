# 설치와 실행

daphnis 직접 실행 전 [검사](validation.md) 필수 확인

- 실행 환경: Node.js 20 이상. 설치·배포 정본: [README](https://github.com/woonyong-choi/daphnis/blob/main/README.md#installation). 패키지 버전만으로 npm 배포 여부 판단 금지
- `<daphnis 경로>`: 의존성이 설치된 기존 작업본의 절대 경로. 아래 명령은 문서 저장소 루트에서 실행

```sh
node <daphnis 경로>/src/cli.js --help
```

```sh
node <daphnis 경로>/src/cli.js check docs/assets/architecture.dap --strict
node <daphnis 경로>/src/cli.js render docs/assets/architecture.dap --strict
node <daphnis 경로>/src/cli.js render docs/assets/architecture.dap --strict --static
```

- 실행 전 사용할 버전의 도움말에서 명령 형식과 성공·실패 시 종료 코드를 확인·기록
- 같은 원본·같은 도구 커밋으로 재현. 확인한 커밋과 Node 버전 기록
- 두 render 명령은 같은 SVG 경로 사용. 전달할 순서·전이·시간 정보 여부로 한 가지 선택, 비교 검증만 `--out`으로 폴더 분리
