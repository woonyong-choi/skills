<h1 align="center">Skills</h1>

<p align="center">
  Claude Code와 Codex의 Git 작업, 코드 스타일, 저장소 문서를 위한 스킬 모음<br>
  <a href="#설치">설치</a> · <a href="#사용법">사용법</a> · <a href="#스킬-목록">스킬 목록</a> · <a href="#측정-결과">측정 결과</a>
</p>

코드를 고치고 문서를 쓰는 작업에서 이름, 형식, 검증 절차를 반복해서 설명하지 않도록 작업별 규칙을 제공한다. 필요한 스킬을 선택하면 그 본문과 관련 규칙을 읽는 구조다. 원본은 역할별 폴더에 두고, Claude Code와 Codex에는 같은 이름과 내용으로 설치한다.

## 작동 방식

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/skill-exposure-dark.svg">
  <img src="docs/assets/skill-exposure-light.svg" alt="분류별 원본을 평평한 목록으로 설치하고 선택한 스킬의 본문과 참조를 읽는 구조">
</picture>

설치 폴더에는 스킬 이름과 짧은 description을 모두 노출하는 H-flat 구조를 사용한다. 스킬 본문을 합치거나 선택을 중계하는 별도 스킬을 추가하지 않는다. 본문의 `기반`은 항상 읽는 규칙, `필요할 때만 읽기`는 해당 조건에서 읽는 규칙이다.

## 설치

Python 3.9 이상이 필요하다. 설치 스크립트는 표준 라이브러리만 사용한다. 저장소를 내려받은 뒤 루트에서 아래 명령을 실행한다. 설치 절차, 충돌 처리와 제거 방법의 정본은 [skill-sync](tools/skill-sync/SKILL.md#설치)다.

```sh
skills_target="${SKILLS_TARGET_HOME:-$HOME}"
mkdir -p "$skills_target/.claude" "$skills_target/.codex"
python3 tools/skill-sync/scripts/install.py --source . --target-home "$skills_target"
```

Claude Code와 Codex의 사용자 스킬 폴더에 설치한다. 기본 대상은 현재 사용자 홈이다. 별도 홈에서 확인하려면 실행 전에 `SKILLS_TARGET_HOME`을 그 경로로 지정한다. 성공 시 `설치 성공` 또는 `일치`와 배포 zip 목록을 출력하고 종료 코드 0을 반환한다. 스킬별 보조 도구의 요구 조건은 각 SKILL.md에 있다.

## 사용법

### Claude Code에서 README 작성

```text
/repo-docs-readme 현재 코드와 실행 결과를 근거로 README의 설치와 사용법을 갱신해 줘.
```

### Codex에서 PR 본문 작성

```text
$git-pull-request 현재 diff와 테스트 결과로 PR 본문을 작성해 줘.
```

요청과 스킬 설명이 맞으면 도구가 자동으로 선택할 수도 있다. 명시 호출은 원하는 규칙을 지정하는 방법이다. 파일 수정, Git 실행, 게시 범위는 함께 적은 요청에 따른다.

## 스킬 목록

### Git과 GitHub

| 스킬 | 용도 |
|---|---|
| [git-branch](git/git-branch/SKILL.md) | 작업 브랜치, PR 생성·머지, 머지 후 정리 |
| [git-commit](git/git-commit/SKILL.md) | 커밋 분리와 메시지 형식 |
| [git-issue](git/git-issue/SKILL.md) | 이슈의 계약·완료 조건, 우선순위, 프로젝트 판 |
| [git-pull-request](git/git-pull-request/SKILL.md) | PR 본문, 계약·문서·검증 검토 |

### 코드와 폴더

| 스킬 | 용도 |
|---|---|
| [code-style](code/code-style/SKILL.md) | 이름, 오류 처리, 주석, 테스트의 공통 규칙 |
| [code-refactoring](code/code-refactoring/SKILL.md) | 문제 원인에 맞는 리팩터링 기법 선택 |
| [code-style-css](code/code-style-css/SKILL.md) | CSS 선택자, 배치, 반응형, 접근성 |
| [code-style-javascript](code/code-style-javascript/SKILL.md) | JavaScript 코드와 ESLint·Prettier·node:test |
| [code-style-kotlin](code/code-style-kotlin/SKILL.md) | Kotlin JVM 서버·CLI와 ktlint·detekt |
| [code-style-python](code/code-style-python/SKILL.md) | Python 코드와 Ruff·mypy·pytest |
| [code-style-rust](code/code-style-rust/SKILL.md) | Rust 코드와 rustfmt·Clippy |
| [folder-naming](code/folder-naming/SKILL.md) | 소스 폴더 구조와 이름 |

### 저장소 문서

| 스킬 | 용도 |
|---|---|
| [repo-docs](docs/repo-docs/SKILL.md) | 문서 종류·위치, 문체, 용어, 사실 상태 |
| [repo-docs-readme](docs/repo-docs-readme/SKILL.md) | README 작성·갱신·번역 |
| [repo-docs-design](docs/repo-docs-design/SKILL.md) | 아키텍처, 기능 설계, 용어, 문서 안내 |
| [repo-docs-spec](docs/repo-docs-spec/SKILL.md) | 구현된 인터페이스와 명령·설정·오류 명세 |
| [repo-docs-decision](docs/repo-docs-decision/SKILL.md) | 공개 결정 기록 |
| [repo-docs-experiment](docs/repo-docs-experiment/SKILL.md) | 실험 설계, 수집, 분석, 결과 보고 |
| [repo-docs-note](docs/repo-docs-note/SKILL.md) | 개발 중 확인한 사실과 참고 자료 |
| [repo-docs-figures](docs/repo-docs-figures/SKILL.md) | daphnis 그림, 차트, 대체 글, 데모 GIF |
| [repo-docs-root](docs/repo-docs-root/SKILL.md) | AGENTS.md와 저장소 루트 문서 |
| [repo-docs-llms](docs/repo-docs-llms/SKILL.md) | 문서 색인 생성 |
| [repo-docs-journal](docs/repo-docs-journal/SKILL.md) | 비공개 판단 기록 |
| [repo-docs-promo](docs/repo-docs-promo/SKILL.md) | 홍보용 촬영 순서와 데모 준비 |
| [html-report](docs/html-report/SKILL.md) | 그림·코드·실행 결과 비교 HTML 보고서 |

### 디자인

| 스킬 | 용도 |
|---|---|
| [design-tokens](design/design-tokens/SKILL.md) | 색·글꼴·간격 값의 토큰 정의와 사용 검사 |

### 스킬 관리

| 스킬 | 용도 |
|---|---|
| [skill-sync](tools/skill-sync/SKILL.md) | 원본 검사, 도구별 설치, Claude 계정용 zip |

## 측정 결과

스킬 27개의 노출 구조를 비교한 2차 실험에서 H-flat을 채택했다. 주 모델은 gpt-5.6-luna이며 128개 요청을 구조마다 3회 평가했다. gpt-6-astra는 같은 요청 중 16개를 3회씩 확인했다. 표의 값은 선택한 스킬 집합의 정밀도와 재현율이며, 괄호는 요청 군집 bootstrap 95% 신뢰구간이다.

| 구조 | 처음 보여 주는 것 | 주 모델 정밀도(%) | 주 모델 재현율(%) | 판정 |
|---|---|---:|---:|---|
| 대조 | 기존 설명의 전체 목록 | 93.4 [90.4, 96.1] | 98.5 [97.1, 99.6] | 비교 기준 |
| H-flat | 짧은 설명의 전체 목록 | 94.1 [90.6, 96.9] | 98.8 [97.4, 99.8] | 채택 |
| H-tree | 분류와 선택한 하위 목록 | 96.3 [94.3, 98.1] | 95.7 [93.3, 97.8] | 보류 |
| H-hybrid | tree와 선택 본문의 연결 안내 | 97.0 [95.2, 98.6] | 97.2 [95.4, 98.7] | 보류 |

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/skill-quality-dark.svg">
  <img src="docs/assets/skill-quality-light.svg" alt="H-flat은 대조와 가까운 재현율을 유지하며 H-tree와 H-hybrid의 정밀도 점추정은 더 높게 나타난 결과">
</picture>

H-flat의 초기 목록은 5,547바이트에서 3,336바이트로 줄었다. 채택은 점추정 순위가 아니라 품질, 일관성, 연결 누락, 읽기량, 왕복·지연 기준의 동시 통과로 결정했다. 후보 선택을 고려한 98.333% 동시 구간을 사용했으며 H-flat만 모든 기준을 통과했다. tree는 재현율·정확 집합·일관성·연결 누락 기준을, hybrid는 일관성·연결 누락·목록 크기·연결 개선 기준 등을 통과하지 못했다.

보류는 열등함을 입증한 결과가 아니다. 두 모델의 정답 합의는 인간 검증이 아니며, 불일치 요청을 제외한 표본에는 선택 편향이 남는다. 이 수치는 제한된 스킬 선택 실험의 결과이며 실제 작업 완성도나 전체 도구 환경의 성능을 뜻하지 않는다. 확인 모델의 결과, 판정 기준과 공개 집계의 범위는 [2차 실험 결과](experiments/skill-exposure/report.md)에 있다. 앞선 형식 통일·조건부 읽기 실험은 [1차 실험 결과](experiments/skill-format-unification/report.md)에 있다.

## 상태

스킬 원본, 설치 스크립트, 일관성 검사와 CI를 제공한다. 릴리스 배포판은 없으며 저장소 원본에서 설치한다. 규칙과 명령은 변경될 수 있으므로 업데이트할 때 설치 결과를 확인한다.

## 개발

[스킬 작성 형식](tools/skill-sync/references/authoring.md)과 [일관성 검사 기준](tools/skill-sync/references/consistency.md)을 따른다. CI는 아래 일관성 검사와 Python 시험을 실행하며, daphnis와 Chromium을 설치해 HTML 보고서 시험도 실행한다.

```sh
python3 tools/skill-sync/scripts/skill_check.py .
python3 -m pytest -q tools/skill-sync/tests git/git-issue/tests docs/repo-docs/scripts/test_check_doc.py docs/html-report/tests/test_daphnis_cli.py
```

시험에는 pytest가 필요하다. 그림 원본, 밝은·어두운 SVG와 재생성 명령은 [그림 재현 안내](docs/assets/README.md)에 있다.

## 라이선스

[MIT](LICENSE).
