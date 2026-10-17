<h1 align="center">Skills</h1>

<p align="center">
  Claude Code와 Codex의 작업 순서, Git 작업, 코드 스타일, 저장소 문서를 위한 스킬 모음<br>
  <a href="#설치">설치</a> · <a href="#사용법">사용법</a> · <a href="#스킬-목록">스킬 목록</a> · <a href="#측정-결과">측정 결과</a>
</p>

코드를 바꾸는 개발 작업은 입구 스킬 [just-mode](just/just-mode/SKILL.md)에서 시작합니다. just-mode가 맞는 작업 순서표를 고르고, 각 단계는 그 규칙을 맡은 스킬을 읽습니다. 작업 중 판단은 저장소의 결정 기록(`.local/decisions/<과업>.tsv`)에 남깁니다. 원본은 역할별 폴더에 두고, Claude Code와 Codex에는 같은 이름과 내용으로 설치합니다.

## 작동 방식

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/skill-exposure-dark.svg">
  <img src="docs/assets/skill-exposure-light.svg" alt="분류별 원본을 평평한 목록으로 설치하고 선택한 스킬의 본문과 참조를 읽는 구조">
</picture>

설치 폴더에는 스킬 이름과 짧은 description을 노출합니다. just-mode는 실행 순서와 스킬 고르기를, 하위 스킬은 주제별 규칙을 소유합니다. 하위 스킬은 상황별 내용을 `references/`에 두고, 그 조건이 맞을 때만 해당 파일을 읽습니다.

## 설치

Python 3.9 이상이 필요합니다. 설치 스크립트는 표준 라이브러리만 사용합니다. 저장소를 내려받은 뒤 루트에서 아래 명령을 실행합니다. 설치 절차, 충돌 처리와 제거 방법의 정본은 [skill-sync](tools/skill-sync/SKILL.md#설치)입니다.

```sh
skills_target="${SKILLS_TARGET_HOME:-$HOME}"
mkdir -p "$skills_target/.claude" "$skills_target/.codex"
python3 tools/skill-sync/scripts/install.py --source . --target-home "$skills_target"
```

Claude Code와 Codex의 사용자 스킬 폴더에 설치합니다. 기본 대상은 현재 사용자 홈입니다. 별도 홈에서 확인하려면 실행 전에 `SKILLS_TARGET_HOME`을 그 경로로 지정합니다. 성공 시 `설치 성공` 또는 `일치`와 배포 zip 목록을 출력하고 종료 코드 0을 반환합니다. 스킬별 보조 도구의 요구 조건은 각 SKILL.md에 있습니다. 사람이 직접 커밋할 때 같은 형식을 쓰려면 `git config --global commit.template ~/.claude/skills/git-commit/references/commit-template.txt`를 실행합니다.

## 사용법

### Claude Code에서 README 작성

```text
/repo-docs-readme 현재 코드와 실행 결과를 근거로 README의 설치와 사용법을 갱신해 줘.
```

### Codex에서 PR 본문 작성

```text
$git-pull-request 현재 diff와 테스트 결과로 PR 본문을 작성해 줘.
```

요청과 스킬 설명이 맞으면 도구가 자동으로 선택할 수도 있습니다. 명시 호출은 원하는 규칙을 지정하는 방법입니다. 파일 수정, Git 실행, 게시 범위는 함께 적은 요청에 따릅니다.

### 작업 기록과 훅

just do 플러그인(설치 ID `just-do`)의 훅이 세션 시작과 압축 뒤에 just-mode 진입 안내를 한 줄로 넣습니다. 세션을 과업에 연결하면 이슈 주소와 결정 기록(`.local/decisions/<과업>.tsv`)의 마지막 줄도 함께 넣습니다. 코드 파일을 고치기 전에는 필요한 규칙 원문을 읽었는지 확인하고, 파일을 바꾼 요청이 결정 기록 없이 끝나려 하면 한 번 멈춥니다. 동작과 설치 방법은 [just do 훅](just/just-mode/references/hooks.md), 판 상태는 [판 상태](git/git-issue/references/project-status.md)에 있습니다.

훅을 쓰려면 스킬 설치 뒤 플러그인도 설치합니다. 앞의 두 줄은 Claude Code, 뒤의 두 줄은 Codex 명령입니다.

```sh
claude plugin marketplace add woonyong-choi/skills
claude plugin install just-do@woon-skills
codex plugin marketplace add woonyong-choi/skills
codex plugin add just-do@woon-skills
```

설치와 실제 훅 실행은 별개입니다. Codex는 대화형 TUI의 `/hooks`에서 새 훅 정의를 검토·신뢰해야 실행합니다. `codex exec`는 신뢰 전 훅을 알림 없이 건너뜁니다. 사용량 신호가 없으면 80% 안내는 나오지 않습니다.

PR 머지 뒤 경력 기록은 [hanger](docs/hanger/SKILL.md)로 남깁니다. 세션 안에서 PR 머지(`gh pr merge`, `gh api` PUT 머지)가 성공하면 같은 훅이 경력 원본에 남길 성과인지 판단하라고 한 줄로 안내합니다. hanger 스킬이 설치돼 있을 때만 안내합니다. hanger는 Hanger MCP 서버로 노트와 경력 원본을 다루고, [career](docs/career/SKILL.md)는 그 원본을 읽어 JD에 맞춘 이력서와 포트폴리오 PDF를 만듭니다.

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
| [code-style-typescript](code/code-style-typescript/SKILL.md) | JavaScript·TypeScript 코드와 ESLint·Prettier·node:test·tsc |
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
| [repo-docs-experiment](docs/repo-docs-experiment/SKILL.md) | 실험 계획, 수집, 분석, 결과 보고 |
| [repo-docs-note](docs/repo-docs-note/SKILL.md) | 개발 중 확인한 사실과 참고 자료 |
| [repo-docs-figures](docs/repo-docs-figures/SKILL.md) | 그림, 차트, 대체 글, 데모 GIF |
| [repo-docs-root](docs/repo-docs-root/SKILL.md) | AGENTS.md와 저장소 루트 문서 |
| [repo-docs-llms](docs/repo-docs-llms/SKILL.md) | 문서 색인 생성 |
| [career](docs/career/SKILL.md) | JD 맞춤 이력서·포트폴리오와 지원 폴더 |
| [hanger](docs/hanger/SKILL.md) | Hanger closet 노트 검색·작성·정리와 경력 원본 기록 |

### 디자인

| 스킬 | 용도 |
|---|---|
| [design-tokens](design/design-tokens/SKILL.md) | 색·글꼴·간격 값의 토큰 정의와 사용 검사 |

### 스킬 관리

| 스킬 | 용도 |
|---|---|
| [skill-sync](tools/skill-sync/SKILL.md) | 원본 검사, 도구별 설치, Claude 계정용 zip |

### just

작업 순서표(플레이북)·검토·검증 스킬 묶음입니다. Claude Code CLI, Codex CLI, OpenCode에서 같이 씁니다.

- `/just-mode`(Codex는 `$just-mode`)에 요청을 붙이면 23개 순서표 중 맞는 순서를 고릅니다. 도움말은 `/just-help`입니다.
- 플러그인 just do(루트 `just/`)의 훅이 just-mode 진입 안내, 결정 기록 확인, 편집 전 규칙 확인을 맡습니다([just do 훅](just/just-mode/references/hooks.md)).
- 서브에이전트, 주기적 깨우기, 다른 회사 모델 검토의 호스트 차이는 [호스트 대응표](just/just-mode/references/hosts.md) 한 곳에서 정합니다.
- [자율 실행 순서표](just/just-mode/playbooks/autonomous-run.md)는 프로젝트 판의 대기 이슈를 위에서부터 PR로 처리하고, 판이 비면 감시합니다. 사용자가 "자율 멈춰"라고 할 때까지 이어 가며, 무한 실행은 Claude Code와 Codex에서만 합니다.
- 스킬 본문은 역할 이름(`code`, `judgment`, `review`, `cheap`)만 씁니다. 실제 모델은 `/just-setup`이 만드는 `~/.config/skills/models.json`이 정합니다([역할별 모델](just/just-mode/references/models.md)).
- 대부분 사람이 직접 부를 때만 켜집니다. Claude Code는 설명을 평소 문맥에 넣지 않고, Codex는 스킬마다 `agents/openai.yaml`이 자동 선택을 막습니다.
- 하위 에이전트 정의(`just-agent`, `comment-sicko`)는 [just/_agents](just/_agents/just-agent.md)에 있고 아직 자동 설치하지 않습니다. 설치되지 않은 호스트에서는 스킬이 같은 지시를 프롬프트에 넣습니다.
- just 스킬도 다른 스킬과 같은 문체 기준([스킬 작성 형식](tools/skill-sync/references/authoring.md))과 같은 검사를 받습니다.
- 라이선스는 [MIT](just/LICENSE)입니다.

## 측정 결과

스킬 27개(당시 기준)의 노출 구조를 비교한 2차 실험에서 H-flat을 채택했습니다. 주 모델은 gpt-5.6-luna이며 128개 요청을 구조마다 3회 평가했습니다. gpt-6-astra는 같은 요청 중 16개를 3회씩 확인했습니다. 표의 값은 선택한 스킬 집합의 정밀도와 재현율이며, 괄호는 요청 군집 bootstrap 95% 신뢰구간입니다.

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

H-flat의 초기 목록은 5,547바이트에서 3,336바이트로 줄었습니다. 채택은 점추정 순위가 아니라 품질, 일관성, 연결 누락, 읽기량, 왕복·지연 기준의 동시 통과로 결정했습니다. 후보 선택을 고려한 98.333% 동시 구간을 사용했으며 H-flat만 모든 기준을 통과했습니다. tree는 재현율·정확 집합·일관성·연결 누락 기준을, hybrid는 일관성·연결 누락·목록 크기·연결 개선 기준 등을 통과하지 못했습니다.

보류는 열등함을 입증한 결과가 아닙니다. 두 모델의 정답 합의는 인간 검증이 아니며, 불일치 요청을 제외한 표본에는 선택 편향이 남습니다. 이 수치는 제한된 스킬 선택 실험의 결과이며 실제 작업 완성도나 전체 도구 환경의 성능을 뜻하지 않습니다. 확인 모델의 결과, 판정 기준과 공개 집계의 범위는 [2차 실험 결과](experiments/skill-exposure/report.md)에 있습니다. 앞선 형식 통일·조건부 읽기 실험은 [1차 실험 결과](experiments/skill-format-unification/report.md)에 있습니다.

### 과거 실험의 본문 크기

기준 커밋 `d7e8489`와 #25 변경 후의 실제 스킬 27개를 비교했습니다. 표에는 지금 남은 24개와 삭제한 repo-docs-journal을 두고, 그 밖에 삭제한 스킬은 표와 합계에서 뺐습니다. 값은 frontmatter와 개행을 포함한 UTF-8 `SKILL.md` 전체 바이트입니다. 시험 fixture와 실험 보관본은 제외했습니다. 하위 문서로 옮긴 내용은 보존하며, 이 표는 저장소 용량이나 평균 호출 비용의 감소를 뜻하지 않습니다.

| 스킬 | 변경 전 | 변경 후 | 감소 |
|---|---:|---:|---:|
| [code-refactoring](code/code-refactoring/SKILL.md) | 12,758 | 4,865 | 7,893 |
| [code-style](code/code-style/SKILL.md) | 20,750 | 19,747 | 1,003 |
| [code-style-css](code/code-style-css/SKILL.md) | 7,479 | 6,523 | 956 |
| [code-style-typescript](code/code-style-typescript/SKILL.md)(측정 당시 JavaScript 전용) | 7,279 | 5,321 | 1,958 |
| [code-style-kotlin](code/code-style-kotlin/SKILL.md) | 7,125 | 5,536 | 1,589 |
| [code-style-python](code/code-style-python/SKILL.md) | 5,728 | 5,034 | 694 |
| [code-style-rust](code/code-style-rust/SKILL.md) | 8,073 | 6,251 | 1,822 |
| [design-tokens](design/design-tokens/SKILL.md) | 8,991 | 7,502 | 1,489 |
| [folder-naming](code/folder-naming/SKILL.md) | 3,399 | 3,213 | 186 |
| [git-branch](git/git-branch/SKILL.md) | 7,827 | 5,587 | 2,240 |
| [git-commit](git/git-commit/SKILL.md) | 5,753 | 5,017 | 736 |
| [git-issue](git/git-issue/SKILL.md) | 17,281 | 8,155 | 9,126 |
| [git-pull-request](git/git-pull-request/SKILL.md) | 6,169 | 5,026 | 1,143 |
| [repo-docs](docs/repo-docs/SKILL.md) | 20,511 | 11,048 | 9,463 |
| [repo-docs-decision](docs/repo-docs-decision/SKILL.md) | 5,568 | 2,881 | 2,687 |
| [repo-docs-design](docs/repo-docs-design/SKILL.md) | 10,869 | 4,274 | 6,595 |
| [repo-docs-experiment](docs/repo-docs-experiment/SKILL.md) | 12,990 | 6,463 | 6,527 |
| [repo-docs-figures](docs/repo-docs-figures/SKILL.md) | 14,171 | 4,151 | 10,020 |
| repo-docs-journal(삭제) | 6,458 | 3,473 | 2,985 |
| [repo-docs-llms](docs/repo-docs-llms/SKILL.md) | 3,693 | 2,596 | 1,097 |
| [repo-docs-note](docs/repo-docs-note/SKILL.md) | 3,141 | 2,352 | 789 |
| [repo-docs-readme](docs/repo-docs-readme/SKILL.md) | 12,684 | 11,218 | 1,466 |
| [repo-docs-root](docs/repo-docs-root/SKILL.md) | 6,999 | 2,815 | 4,184 |
| [repo-docs-spec](docs/repo-docs-spec/SKILL.md) | 7,736 | 1,941 | 5,795 |
| [skill-sync](tools/skill-sync/SKILL.md) | 8,231 | 5,405 | 2,826 |
| 합계 | 231,663 | 146,394 | 85,269 |

기본 본문 합계는 36.8% 줄었습니다. 아래 조건에 해당하는 작업은 하위 문서를 추가로 읽습니다. 이미 읽은 정본은 같은 작업에서 중복 합산하지 않으며, 원본 변경 시 다시 확인합니다.

### 읽기 연결

아래 읽기 연결과 읽기량은 #25 시점의 정적 값입니다. 지금 스킬 크기와 다르며 실제 호출 빈도나 평균 토큰 사용량을 잰 값이 아닙니다.

`기반`은 먼저 적용하는 스킬입니다. 종류별·언어별 스킬의 필수 규칙은 본문에 남기고, 하위 문서는 작업·파일·단계 조건이 맞을 때 읽습니다. 다른 스킬의 하위 문서는 이름으로 찾은 스킬 폴더 기준 경로입니다. 같은 스킬의 하위 문서는 상대 링크로 열 수 있으며, 설치본과 zip에도 같은 내용이 들어갑니다.

| 작업 | 먼저 읽는 정본 | 조건부 하위 문서 |
|---|---|---|
| Python 코드 검토 | code-style, code-style-python | 린트 설정 생성·변경·감사 시 Python의 `references/lint.md` |
| CSS 검토 | code-style, design-tokens, code-style-css | Stylelint 설정 작업 시 CSS의 `references/lint.md`; 토큰 분류·단계 신설·변경 시 `references/categories.md` |
| 커밋 메시지 작성 | git-commit, repo-docs의 `references/writing.md` | 메시지 작성 시 git-commit의 `references/commit-template.txt`; 실제 커밋 전 검사 시 code-style |
| 설계 문서 작성 | repo-docs, `references/writing.md`, repo-docs-design | 작성·갱신·검토 대상에 따라 `references/index.md`, `architecture.md`, `design.md`, `glossary.md` 중 해당 문서 |
| 이슈 본문 작성 | git-issue, repo-docs의 `references/writing.md` | 종류별 `references/{design,build,bug,experiment,docs}.md`; 게시 전 `public-links.md`; 상태 사건 발생 전 `project-status.md` |
| 스킬 검사 | skill-sync, `references/execution.md` | 형식 수정 시 `references/authoring.md`; 도구 설치 시 `installation.md`; 계정 배포 시 `claude-upload.md` |

위 연결에 따른 정적 읽기량입니다. Python·CSS 검토는 설정 변경이 없는 기본 경로입니다. 아키텍처 작성은 공통 문체와 선택한 템플릿까지 포함합니다.

| 작업 | 변경 전 바이트 | 변경 후 바이트 | 감소 |
|---|---:|---:|---:|
| Python 코드 검토 | 26,478 | 24,781 | 1,697 |
| CSS 검토 | 37,220 | 33,772 | 3,448 |
| 커밋 메시지 작성 | 26,264 | 14,534 | 11,730 |
| 아키텍처 문서 작성 | 31,380 | 27,543 | 3,837 |

공통 우선순위 정본은 [스킬 작성 형식](tools/skill-sync/references/authoring.md#적용-범위)에만 두고 각 스킬 본문에는 되풀이하지 않습니다. 스크립트 위치·Windows 명령은 [실행 규칙](tools/skill-sync/references/execution.md), Git 글의 문체는 [문서 작성 규칙](docs/repo-docs/references/writing.md), PR 생성·머지 후 판 상태는 [판 상태 절차](git/git-issue/references/project-status.md)에서 관리합니다.

## 상태

스킬 원본, 설치 스크립트, 일관성 검사와 CI를 제공합니다. 릴리스 배포판은 없으며 저장소 원본에서 설치합니다. 규칙과 명령은 변경될 수 있으므로 업데이트할 때 설치 결과를 확인합니다.

## 개발

[스킬 작성 형식](tools/skill-sync/references/authoring.md)과 [일관성 검사 기준](tools/skill-sync/references/consistency.md)을 따릅니다. CI([skills.yml](.github/workflows/skills.yml))와 같은 검사를 저장소 루트에서 아래 순서로 실행합니다. 설치 명령은 훅 통합 시험이 읽을 설치본을 홈 폴더에 만듭니다. 마지막 블록은 Torso를 `.runtime/torso`에 받아 둔 뒤 README 그림을 다시 만들고, 커밋된 그림과 실험 집계가 바뀌지 않았는지 확인합니다. Torso를 받는 명령은 [그림 재현 안내](docs/assets/README.md)에 있습니다.

```sh
python3 tools/skill-sync/scripts/skill_check.py .
mkdir -p "$HOME/.codex" "$HOME/.claude"
python3 tools/skill-sync/scripts/install.py --source . --tool codex --tool claude-code
python3 -m pytest -q tools/skill-sync/tests git/git-issue/tests just/just-mode/scripts/hooks/tests docs/repo-docs/tests docs/repo-docs-llms/tests docs/repo-docs-figures/tests docs/career/tests
(cd just/just-mode/scripts && bun install --frozen-lockfile && bun test)
python3 experiments/skill-exposure/scripts/03-analyze.py
python3 scripts/render_readme.py .runtime/torso/src/cli.js
git diff --exit-code -- docs/assets experiments/skill-exposure/results
```

CI는 macOS의 링크된 임시 폴더 경로를 흉내 내려고 `TMPDIR`을 심볼릭 링크로 바꿔 훅 시험(`just/just-mode/scripts/hooks/tests`)을 한 번 더 돌립니다. 플러그인 매니페스트를 바꾸면 `claude plugin validate --strict .`과 `claude plugin validate --strict just`도 실행합니다.

시험에는 pytest, Node.js 22, Bun 1.4.2가 필요합니다. career PDF 컴파일 시험은 `typst`(명령 또는 Python 패키지)가 있을 때만 돕니다.

## 라이선스

[MIT](LICENSE).
