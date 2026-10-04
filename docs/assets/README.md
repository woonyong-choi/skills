# README 그림

README와 그림은 한국어다. 분류와 설치 목록의 관계, 구조별 정밀도·재현율을 별개 그림으로 보여 준다. 정지 SVG는 모든 노드와 계열을 표시한다.

## 재현

Python 3.9 이상과 의존성이 설치된 daphnis 작업본이 필요하다. 저장소 루트에서 실행한다.

```sh
python3 experiments/skill-exposure/scripts/03-analyze.py
python3 scripts/render_readme.py <daphnis 경로>/src/cli.js
```

확인한 도구는 daphnis `a899e9ec40fc69b581226460b70f13b8f45a03df`, Node.js `v26.9.0`이다. CI는 같은 daphnis 커밋과 Node.js 22를 사용한다. `check --strict --no-deprecated` 통과 뒤 `render --static`으로 생성한다. 차트에는 `--require-data --require-ci`도 적용한다. 정상 종료 코드는 0이며 검사 실패 시 렌더를 시작하지 않는다.

렌더 스크립트는 SVG 루트의 `data-theme`만 light 또는 dark로 고정한다. 색·글꼴·배치는 daphnis 산출물을 유지한다. 생성 파일을 손으로 수정하지 않는다. 같은 원본과 집계, 도구 커밋으로 두 번 생성한 바이트가 같은지 확인한다.

## 파일

| 원본 | 산출물 | 입력 |
|---|---|---|
| [skill-exposure.dap](skill-exposure.dap) | [밝은 화면](skill-exposure-light.svg), [어두운 화면](skill-exposure-dark.svg) | README 작동 방식 |
| [skill-quality.dap](skill-quality.dap) | [밝은 화면](skill-quality-light.svg), [어두운 화면](skill-quality-dark.svg) | [실험 집계](../../experiments/skill-exposure/results/summary.json)의 chart 배열 |
