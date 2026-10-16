# 설치와 실행

Torso를 설치하거나 소스 작업본에서 직접 실행할 때 명령 형식과 재현 조건을 정한다.

## 환경

- Node.js 20 이상이 필요하다. 설치와 배포의 정본은 [Torso README](https://github.com/woonyong-choi/torso/blob/main/README.md#installation)다. 패키지 버전만 보고 npm 배포 여부를 판단하지 않는다.
- `<Torso 경로>`는 의존성을 설치한 기존 작업본의 절대 경로다. 아래 명령은 문서 저장소 루트에서 실행한다.

```sh
node <Torso 경로>/src/cli.js --help
```

```sh
node <Torso 경로>/src/cli.js check docs/assets/architecture.thinkflow --strict
node <Torso 경로>/src/cli.js render docs/assets/architecture.thinkflow --strict
node <Torso 경로>/src/cli.js render docs/assets/architecture.thinkflow --strict --static
```

## 확인

- 실행 전에 쓸 버전의 도움말에서 명령 형식과 성공, 실패 때의 종료 코드를 확인하고 남긴다.
- 같은 원본과 같은 도구 커밋으로 재현한다. 확인한 커밋과 Node 버전을 남긴다.
- 두 render 명령은 같은 SVG 경로에 쓴다. 전할 순서, 전이, 시간 정보가 있는지로 하나를 고른다. 비교 검증할 때만 `--out`으로 폴더를 나눈다.
