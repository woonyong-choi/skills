# README 그림

README와 그림은 한국어다. 분류와 설치 목록의 관계, 구조별 정밀도·재현율을 별개 그림으로 보여 준다. 두 원본 모두 장면이 없어 정지 SVG에 모든 카드와 계열이 보인다.

## 재현

Python 3.9 이상, Node.js 22와 DiagramPlay 작업본이 필요하다. 저장소 루트에서 실행한다. 앞의 네 줄은 DiagramPlay를 CI와 같은 커밋으로 `.runtime/diagramplay`에 받고 의존성과 Chromium을 설치한다.

```sh
git clone https://github.com/woonyong-choi/diagramplay .runtime/diagramplay
git -C .runtime/diagramplay fetch origin 0f35b9b1c400355e769f8302a3f3f348a07d69f5
git -C .runtime/diagramplay checkout 0f35b9b1c400355e769f8302a3f3f348a07d69f5
npm --prefix .runtime/diagramplay ci
python3 experiments/skill-exposure/scripts/03-analyze.py
python3 scripts/render_readme.py .runtime/diagramplay/src/cli.js
```

Node.js 22에서 확인한 도구는 DiagramPlay main 커밋 `0f35b9b1c400355e769f8302a3f3f348a07d69f5`이다. 브랜치에 남아 있는 커밋으로 고정해 GitHub가 정리하지 않게 한다. CI는 같은 커밋을 `.runtime/diagramplay`에 받아 쓰고, 다시 만든 SVG가 커밋된 파일과 같지 않으면 실패한다. `check --strict` 통과 뒤 `render --strict --static`으로 생성한다. 정상 종료 코드는 0이며 검사 실패 시 렌더를 시작하지 않는다.

렌더 스크립트는 SVG 루트의 `data-theme`만 light 또는 dark로 고정한다. 색·글꼴·배치는 DiagramPlay 산출물을 유지한다. 생성 파일을 손으로 수정하지 않는다. 같은 원본과 집계, 도구 커밋으로 두 번 생성한 바이트가 같은지 확인한다.

## 파일

| 원본 | 산출물 | 입력 |
|---|---|---|
| [skill-exposure.diagramplay](skill-exposure.diagramplay) | [밝은 화면](skill-exposure-light.svg), [어두운 화면](skill-exposure-dark.svg) | README 작동 방식 |
| [skill-quality.diagramplay](skill-quality.diagramplay) | [밝은 화면](skill-quality-light.svg), [어두운 화면](skill-quality-dark.svg) | [실험 집계](../../experiments/skill-exposure/results/summary.json)의 chart 배열 |
