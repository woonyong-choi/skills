# README 그림

README와 그림은 한국어다. 분류와 설치 목록의 관계, 구조별 정밀도·재현율을 별개 그림으로 보여 준다. 두 원본 모두 장면이 없어 정지 SVG에 모든 카드와 계열이 보인다.

## 재현

Python 3.9 이상, Node.js 22와 DiagramPlay 작업본이 필요하다. 저장소 루트에서 실행한다. 앞의 네 줄은 DiagramPlay를 CI와 같은 커밋으로 `.runtime/diagramplay`에 받고 의존성과 Chromium을 설치한다.

```sh
git clone https://github.com/woonyong-choi/diagramplay .runtime/diagramplay
git -C .runtime/diagramplay fetch origin ebdc3e9c84c3d5443af7f1b6b5d9b2a18e5002ca
git -C .runtime/diagramplay checkout ebdc3e9c84c3d5443af7f1b6b5d9b2a18e5002ca
npm --prefix .runtime/diagramplay ci
python3 experiments/skill-exposure/scripts/03-analyze.py
python3 scripts/render_readme.py .runtime/diagramplay/src/cli.js
```

Node.js 22에서 확인한 도구는 DiagramPlay 후보 `76cdaacd39258174db4182393a19184cb7a7f001`이다. 고정 커밋 `ebdc3e9c84c3d5443af7f1b6b5d9b2a18e5002ca`은 후보와 Git 트리가 같다. CI는 같은 커밋을 `.runtime/diagramplay`에 받아 쓰고, 다시 만든 SVG가 커밋된 파일과 같지 않으면 실패한다. `check --strict` 통과 뒤 `render --strict --static`으로 생성한다. 정상 종료 코드는 0이며 검사 실패 시 렌더를 시작하지 않는다.

렌더 스크립트는 SVG 루트의 `data-theme`만 light 또는 dark로 고정한다. 색·글꼴·배치는 DiagramPlay 산출물을 유지한다. 생성 파일을 손으로 수정하지 않는다. 같은 원본과 집계, 도구 커밋으로 두 번 생성한 바이트가 같은지 확인한다.

## 파일

| 원본 | 산출물 | 입력 |
|---|---|---|
| [skill-exposure.diagramplay](skill-exposure.diagramplay) | [밝은 화면](skill-exposure-light.svg), [어두운 화면](skill-exposure-dark.svg) | README 작동 방식 |
| [skill-quality.diagramplay](skill-quality.diagramplay) | [밝은 화면](skill-quality-light.svg), [어두운 화면](skill-quality-dark.svg) | [실험 집계](../../experiments/skill-exposure/results/summary.json)의 chart 배열 |
