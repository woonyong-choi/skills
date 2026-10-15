# 변환

`.thinkflow` 변환 전 [검사](validation.md), `.tape` 변환 전 [VHS](vhs.md) 필수 확인

- 저장소 루트에서 실행. 기존 호출 경로 유지, `.thinkflow`는 ThinkFlow, `.tape`는 VHS 호출

```sh
python3 <이 스킬 폴더>/scripts/render_figures.py --thinkflow <ThinkFlow 경로> docs/assets/architecture.thinkflow
```

- `--thinkflow`: 작업본 루트 또는 `src/cli.js`. 생략 시 `THINKFLOW_PATH`, 없으면 PATH의 `thinkflow`. `--static`은 ThinkFlow에 전달. 옛 이름 별칭 없음
- 원본 인자 생략 시 git 추적 원본 탐색. 공백 포함 경로 지원. 새 원본은 경로 지정 또는 git 추가 후 실행
- 옛 형식 원본 발견 시 목록 출력 후 변환 전 실패. `.thinkflow`로 문법 이전 필요, 확장자만 변경 금지
- 모든 `.thinkflow`의 strict 검사 뒤 렌더. 검사 실패 시 이 호출의 렌더 시작 금지. 렌더 중 I/O 실패의 전체 파일 원자성 보장 없음
- `.tape`와 그림 전용 옵션 동시 사용 금지. VHS 실행 위치와 결과 계약: [VHS](vhs.md)
- 실패 시 원본 수정 후 재실행. 실패 전부터 있던 SVG를 새 성공 결과로 간주 금지
