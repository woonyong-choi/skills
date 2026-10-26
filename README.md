<h1 align="center">Skills</h1>

<p align="center">
  Claude Code와 Codex의 작업 순서, Git 작업, 코드 스타일, 저장소 문서를 위한 스킬 모음
</p>

> [!NOTE]
> 개발 중입니다. 배포판은 없고 저장소에서 설치합니다.

## 빠른 시작

Git과 Python 3.9 이상이 필요합니다. Claude Code와 Codex 중 사용하는 도구의 안내만 따라 설치하세요. 설치 스크립트는 Python 표준 라이브러리만 사용합니다.

```sh
git clone https://github.com/woonyong-choi/skills.git
cd skills
```

### Claude Code

저장소 루트에서 실행하세요.

```sh
mkdir -p "$HOME/.claude"
python3 tools/skill-sync/scripts/install.py --source . --tool claude-code
```

각 스킬 경로 뒤의 `설치 성공` 또는 `일치`와 종료 코드 0을 확인하세요. 스킬은 `~/.claude/skills/`에 설치합니다. Claude Code의 새 세션에서 아래 요청을 보내면 작업에 맞는 스킬과 호출 예시를 안내합니다.

```text
/just-help README를 고칠 때 어떤 스킬을 쓰는지 알려 줘.
```

### Codex

저장소 루트에서 실행하세요.

```sh
mkdir -p "$HOME/.codex"
python3 tools/skill-sync/scripts/install.py --source . --tool codex
```

각 스킬 경로 뒤의 `설치 성공` 또는 `일치`와 종료 코드 0을 확인하세요. 스킬은 `~/.codex/skills/`에 설치합니다. Codex의 새 세션에서 아래 요청을 보내면 작업에 맞는 스킬과 호출 예시를 안내합니다.

```text
$just-help README를 고칠 때 어떤 스킬을 쓰는지 알려 줘.
```

두 도구에 모두 설치하려면 `--tool claude-code --tool codex`를 함께 지정하세요. 설치기는 Claude 계정용 zip도 로컬에 만들며, 계정에 업로드하지는 않습니다. 업데이트할 때는 저장소를 갱신한 뒤 같은 설치 명령을 다시 실행하세요. 같은 이름의 외부 스킬은 덮어쓰지 않고 충돌로 보고합니다. 별도 홈 설치, Antigravity, 제거 방법은 [skill-sync 설치 안내](tools/skill-sync/SKILL.md#설치)에 있습니다.

### just do 훅 설치

위 명령으로 설치한 스킬은 직접 불러 쓸 수 있습니다. 연결한 과업의 복원과 편집 전 규칙 확인도 받으려면 사용하는 도구에 just do 플러그인을 추가하세요. 편집 전 규칙 확인은 `/mode`로 켜고 `/mode off`로 끕니다. 새 세션은 꺼진 상태로 시작하며, 스킬 설치를 먼저 마쳐야 합니다.

Claude Code에서 실행할 명령입니다.

```sh
claude plugin marketplace add woonyong-choi/skills
claude plugin install just-do@woon-skills
```

Codex에서 실행할 명령입니다.

```sh
codex plugin marketplace add woonyong-choi/skills
codex plugin add just-do@woon-skills
```

Codex는 대화형 TUI의 `/hooks`에서 새 훅을 검토하고 신뢰해야 실행합니다. `codex exec`는 신뢰 전 훅을 건너뜁니다. 설치 성공만으로 현재 세션에서 훅이 활성화됐다고 판단하지 마세요. 위 명령 형식은 2026-10-18에 확인했습니다. 활성화 확인과 이벤트별 동작은 [just do 훅](just/mode/references/hooks.md)에 있습니다.

## 해결하는 문제

Claude Code와 Codex로 작업할 때 커밋 형식, 코드 규칙, 문서 기준을 요청마다 다시 설명해야 합니다. 이 저장소는 그 규칙을 스킬로 나누어 두 도구에 같은 내용으로 설치합니다. 스킬은 적용할 조건과 작업 방법을 적은 `SKILL.md`와 참조 파일의 묶음입니다.

개발 작업 전체를 맡길 때는 mode가 작업 종류에 맞는 순서표를 골라 재현, 구현, 검토, 검증으로 연결합니다. 한 저장소에서만 쓰는 짧은 규칙은 그 저장소의 `AGENTS.md`에 두는 편이 관리하기 좋습니다.

## 작동 방식

1. 설치기가 `git`, `code`, `docs`, `design`, `tools`, `just`의 스킬을 도구의 사용자 스킬 폴더에 같은 이름으로 설치합니다.
2. 사용자가 스킬을 부르거나 도구가 설명에 맞는 스킬을 고릅니다. mode는 사용자가 명시적으로 요청한 작업에서만 시작합니다.
3. 선택한 스킬이 본문을 읽고, 상황에 필요한 참조와 다른 스킬을 연결합니다.
4. mode는 이슈의 완료 조건에 맞춰 작업하고 결정과 실행 근거를 기록합니다. just do 훅을 활성화하면 `/mode`로 켠 세션에서 편집 전 규칙 확인과 기록 누락 안내도 받습니다.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/skill-exposure-dark.svg">
  <img src="docs/assets/skill-exposure-light.svg" alt="분류별 원본을 평평한 목록으로 설치하고 선택한 스킬의 본문과 참조를 읽는 구조">
</picture>

설치 구조와 충돌 처리는 [skill-sync](tools/skill-sync/SKILL.md#설치), 실행 순서는 [mode](just/mode/SKILL.md), 도구별 차이는 [호스트 대응표](just/mode/references/hosts.md)에 있습니다.

### 작업에 맞는 스킬

| 할 일 | 시작할 스킬 |
|---|---|
| 버그 수정, 기능 개발, 리팩터링 | [mode](just/mode/SKILL.md) |
| 코드가 어떻게 동작하는지 조사 | [how](just/how/SKILL.md) |
| 변경 검토 | [interrogate](just/interrogate/SKILL.md) |
| 커밋 분리와 메시지 작성 | [git-commit](git/git-commit/SKILL.md) |
| 이슈와 PR 작성 | [git-issue](git/git-issue/SKILL.md), [git-pull-request](git/git-pull-request/SKILL.md) |
| README 작성 | [repo-docs-readme](docs/repo-docs-readme/SKILL.md) |
| 채용 공고에 맞춘 이력서와 포트폴리오 | [career](personal/career/SKILL.md) |
| 역할별 모델과 추론 예산 설정 | [just-setup](just/just-setup/SKILL.md) |

Claude Code에서는 `/mode`, Codex에서는 `$mode` 뒤에 목표와 완료 조건을 적으세요. 문서 작업만 맡기려면 `/repo-docs-readme` 또는 `$repo-docs-readme`처럼 해당 스킬을 직접 부르세요. 파일 수정과 GitHub 게시 범위는 요청에 따릅니다. 나머지 just 스킬과 상황별 호출 예시는 [just 도움말](just/just-help/SKILL.md#스킬-고르기)에 있습니다.

## 상태

| 있는 것 | 아직 없는 것 | 남은 작업 |
|---|---|---|
| 스킬 원본, 도구별 설치기, just do 훅, 일관성 검사와 CI | 릴리스 배포판, PR 교차 리뷰 세션 구현 | [교차 리뷰 세션 #91](https://github.com/woonyong-choi/skills/issues/91), [이슈 제목 규칙 #6](https://github.com/woonyong-choi/skills/issues/6) |

현재 착수 여부는 [프로젝트 판](https://github.com/users/woonyong-choi/projects/16)에서 확인하세요. 규칙과 명령은 배포 전에도 바뀔 수 있습니다. 업데이트할 때는 사용하는 스킬의 변경 내용과 설치 결과를 확인하세요.

### 측정 결과

당시 스킬 27개의 노출 구조를 비교해 H-flat을 채택했습니다. H-flat은 짧은 설명을 전체 목록으로 보여 주는 방식입니다. gpt-5.6-luna로 요청 128개를 구조마다 3회 평가했고, gpt-6-astra로 같은 요청 중 16개를 3회씩 확인했습니다.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/skill-quality-dark.svg">
  <img src="docs/assets/skill-quality-light.svg" alt="H-flat은 대조와 가까운 재현율을 유지하며 H-tree와 H-hybrid의 정밀도 점추정은 더 높게 나타난 결과">
</picture>

주 모델의 H-flat 정밀도는 94.1% [90.6, 96.9], 재현율은 98.8% [97.4, 99.8]이며 대괄호는 요청 군집 bootstrap 95% 신뢰구간입니다. 초기 목록은 5,547바이트에서 3,336바이트로 줄었습니다. 후보 비교를 보정한 98.333% 동시 구간으로 품질·읽기량·지연 기준을 판정했고 H-flat만 모두 통과했습니다. 정밀도 점추정이 더 높은 tree와 hybrid는 다른 기준을 통과하지 못해 보류했습니다.

이 결과는 스킬 선택 실험이며 실제 개발 작업의 완성도를 검증하지 않습니다. 두 모델의 정답 합의에 인간 검증이 없고, 불일치 요청을 제외한 표본에는 선택 편향이 남습니다. 구조별 수치와 미통과 기준은 [2차 실험 결과](experiments/skill-exposure/report.md), 앞선 형식 통일 실험은 [1차 실험 결과](experiments/skill-format-unification/report.md)에 있습니다.

## 문서

- [작업 진행](just/mode/SKILL.md)
  - [just 도움말](just/just-help/SKILL.md)
  - [just do 훅](just/mode/references/hooks.md)
  - [호스트 대응표](just/mode/references/hosts.md)
  - [모델 설정](just/just-setup/SKILL.md)
- [Git과 GitHub](git/git-branch/SKILL.md)
  - [git-commit](git/git-commit/SKILL.md)
  - [git-issue](git/git-issue/SKILL.md)
  - [git-pull-request](git/git-pull-request/SKILL.md)
- [코드와 폴더](code/code-style/SKILL.md)
  - [code-refactoring](code/code-refactoring/SKILL.md)
  - [code-style-css](code/code-style-css/SKILL.md)
  - [code-style-typescript](code/code-style-typescript/SKILL.md)
  - [code-style-kotlin](code/code-style-kotlin/SKILL.md)
  - [code-style-python](code/code-style-python/SKILL.md)
  - [code-style-rust](code/code-style-rust/SKILL.md)
  - [folder-naming](code/folder-naming/SKILL.md)
- [저장소 문서](docs/repo-docs/SKILL.md)
  - [repo-docs-readme](docs/repo-docs-readme/SKILL.md)
  - [repo-docs-design](docs/repo-docs-design/SKILL.md)
  - [repo-docs-spec](docs/repo-docs-spec/SKILL.md)
  - [repo-docs-decision](docs/repo-docs-decision/SKILL.md)
  - [repo-docs-experiment](docs/repo-docs-experiment/SKILL.md)
  - [repo-docs-note](docs/repo-docs-note/SKILL.md)
  - [repo-docs-figures](docs/repo-docs-figures/SKILL.md)
  - [repo-docs-root](docs/repo-docs-root/SKILL.md)
  - [repo-docs-llms](docs/repo-docs-llms/SKILL.md)
- [개인 기록](personal/markdown-notes-agent/SKILL.md)
  - [career](personal/career/SKILL.md)
- [디자인](design/design-tokens/SKILL.md)
- [스킬 관리](tools/skill-sync/SKILL.md)
- [실험](experiments/skill-exposure/report.md)
  - [형식 통일과 조건부 읽기](experiments/skill-format-unification/report.md)
- [그림](docs/assets/README.md)

[전체 문서 목록](docs/README.md)

## 개발

설치 스크립트는 Python 3.9 이상, 개발 시험은 Python 3.10 이상을 사용합니다. CI는 Python 3.12, pytest 8.4.2, Node.js 22, Bun 1.4.2로 실행합니다. career PDF 컴파일 시험은 `typst` 명령 또는 Python 패키지가 있을 때 실행합니다.

스킬과 훅은 별도 빌드 없이 실행합니다. [스킬 작성 형식](tools/skill-sync/references/authoring.md)과 [일관성 검사 기준](tools/skill-sync/references/consistency.md)을 따르세요. 아래 명령은 [CI](.github/workflows/skills.yml)의 검사입니다. 첫 설치 명령은 훅 통합 시험을 위해 현재 사용자 홈의 스킬 설치본을 갱신합니다.

```sh
mkdir -p "$HOME/.codex" "$HOME/.claude"
python3 tools/skill-sync/scripts/install.py --source . --tool codex --tool claude-code
python3 -m pytest -q tools/skill-sync/tests git/git-issue/tests design/design-tokens/tests just/mode/scripts/hooks/tests docs/repo-docs/tests docs/repo-docs-llms/tests docs/repo-docs-figures/tests personal/career/tests
(cd just/mode/scripts && bun install --frozen-lockfile && bun test)
python3 tools/skill-sync/scripts/skill_check.py .
python3 docs/repo-docs/scripts/check_doc.py README.md
```

README 그림을 바꾸면 [그림 재현 안내](docs/assets/README.md)를 따라 다시 만들고 `git diff --exit-code -- docs/assets experiments/skill-exposure/results`로 생성물을 대조하세요. CI는 링크된 임시 경로에서도 훅 시험을 실행합니다. 플러그인 매니페스트를 바꾸면 `claude plugin validate --strict .`과 `claude plugin validate --strict just`도 실행하세요.

## 라이선스

[MIT](LICENSE)
