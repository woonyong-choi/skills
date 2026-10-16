# 변환

`render_figures.py`로 그림 원본을 SVG와 GIF로 바꾼다. 기존 호출 경로를 그대로 두고, `.thinkflow`는 Torso를, `.tape`는 VHS를 부른다.

```sh
python3 <이 스킬 폴더>/scripts/render_figures.py --thinkflow <Torso 경로> docs/assets/architecture.thinkflow
```

## 인자

- `--thinkflow`는 작업본 루트나 `src/cli.js`다. 빼면 `THINKFLOW_PATH`를, 그것도 없으면 PATH의 `thinkflow`를 쓴다. `--static`은 Torso에 그대로 넘긴다. 옛 이름 별칭은 없다.
- 원본 인자를 빼면 하위 폴더에서 실행해도 저장소 루트 `docs/assets/` 아래의 git 추적 원본만 찾는다. 공백이 든 경로도 된다. 새 원본은 경로를 주거나 git에 추가한 뒤 실행한다. 추적 원본이 없거나, git 밖이거나, git 오류가 나면 stderr에 쓰고 종료 코드 1로 끝난다.
- 찾아낸 `.tape`는 저장소 루트에서 VHS를 실행하고, 경로를 준 `.tape`는 지금 위치에서 실행한다.

## 실패 조건

- 옛 형식(`.dap`) 원본은 인자로 주든 찾아내든 목록을 출력하고 변환 전에 실패한다. `.thinkflow`로 문법을 옮겨야 하고, 확장자만 바꾸지 않는다.
- `.tape`가 있는데 PATH에 `vhs`가 없으면 렌더 전에 실패한다.
- 모든 `.thinkflow`를 strict로 검사한 뒤 렌더한다. 검사가 실패하면 그 호출에서 렌더를 시작하지 않는다. 렌더 중 I/O가 실패할 때 모든 파일이 한꺼번에 바뀌거나 그대로 남는다는 보장은 없다.
- `.tape`와 그림 전용 옵션을 함께 쓰지 않는다. VHS 실행 위치와 결과 계약은 [VHS](vhs.md)를 따른다.
- 실패하면 원본을 고친 뒤 다시 실행한다. 실패 전부터 있던 SVG를 새로 성공한 결과로 보지 않는다.
