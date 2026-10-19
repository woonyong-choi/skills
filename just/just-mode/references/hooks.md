# just do 훅

플러그인 `just-do`(표시 이름 "just do")의 훅이 언제 무엇을 하는지, 과업 연결과 결정 기록이 어디에 남는지, 어떻게 설치하고 확인하는지를 적는다.

## 언제 읽나

- 훅·설치·사용량 표시를 바꾸거나 고칠 때, 훅 안내가 예상과 다를 때 읽는다.
- 평소 작업에는 읽지 않는다. 필요한 안내는 훅이 대화에 넣는다.

## 과업 연결과 결정 기록

- 과업 연결은 "이 세션이 어느 과업·이슈인지"만 기록한다. 목표·제약·계획은 이슈 본문에, 진행 상태는 판 상태에 둔다. 이슈에 진행 로그 댓글을 달지 않는다.
- 연결은 `python3 <just-mode 폴더>/scripts/hooks/task.py bind --session-id <세션 ID> --task <과업> --issue <이슈 URL>`로 한다. 세션 ID는 세션 시작 안내에 나온다. Codex는 생략하면 `CODEX_THREAD_ID`를 쓴다. `--task`를 생략하면 현재 브랜치 이름의 `/`를 `-`로 바꾼 이름을 쓴다. 확인은 `show`, 해제는 `unbind`다.
- 결정 기록은 `.local/decisions/<과업>.tsv` 하나다. 형식, 쓰는 방법, 과업 이름 규칙은 **show-me-your-work** 스킬이 맡는다.
- 결정 기록과 상태 파일은 워크트리가 아니라 기본 체크아웃(`git rev-parse --git-common-dir`의 상위)의 `.local/`에 둔다. 워크트리를 지워도 남는다. 워크트리 안에서 `log.sh`에 워크트리의 `.local/` 경로를 줘도 기본 체크아웃으로 옮겨 쓴다.
- 상태 파일은 `.local/sessions/` 아래 세션마다 하나(연결, 요청 시작 지문, 사용량)와 세션·서브에이전트마다 하나(규칙 전달 기록)다. 지워도 연결과 규칙 전달 기록만 처음으로 돌아간다.
- `.local/`이 git 무시 대상이 아니면 훅, `log.sh`, `orch`가 `.local/.gitignore`(`*`)를 만들어 스스로 무시되게 한다.

## 이벤트별 동작

| 이벤트 | 동작 |
|---|---|
| SessionStart | 규칙 전달 기록을 비운다. 이미 연결한 과업이 있을 때만 이슈 URL과 결정 기록 마지막 5줄을 복원한다. 연결이 없으면 아무 안내도 넣지 않는다. just-mode를 읽거나 과업을 연결하라는 자동 지시는 하지 않는다. |
| UserPromptSubmit | 요청 시작 시점의 작업본 지문과 결정 기록 줄 수를 저장한다. 압축 뒤 첫 요청이면 이미 연결한 과업의 복원 정보를 다시 넣는다. |
| PreToolUse | 편집 대상 경로가 git 작업본 안인 코드 파일 편집(Write, Edit, MultiEdit, apply_patch, 셸 apply_patch) 전에 필수 규칙 원문이 도구 결과로 전달됐는지 본다. 남았으면 조회 명령과 함께 거부한다. 규칙 조회 명령은 미전달분만 내는 `--pending` 조회로 바꾼다. 작업본은 편집 대상 경로마다 판정하므로 세션 폴더 밖의 형제 워크트리(`../{저장소}.wt/`)도 든다. 연결 과업이 없어도 동작한다. |
| PostToolUse | 도구 출력에 들어간 규칙 원문을 전달됨으로 기록한다. 성공한 편집의 대상 작업본을 이번 요청 상태에 더한다. 문맥 사용량이 80% 이상이면 한 번 "결정 기록 후 새 서브에이전트에 인계"를 안내한다. 셸 PR 머지가 성공하면 경력 원본에 남길 성과인지 판단해 사실과 근거를 정리하고 markdown-notes-agent 스킬에 기록을 요청하라는 한 줄을 넣는다(markdown-notes-agent 스킬이 설치돼 있을 때만). |
| PreCompact | 이번 요청 이후 결정 기록에 새 줄이 없으면 알리고, 압축 뒤 첫 요청 안내에 "결정을 먼저 남긴다"를 덧붙인다. 이슈로 아무것도 보내지 않는다. |
| PostCompact | 규칙 전달 기록과 사용량 안내를 비우고 다음 요청에 안내를 다시 넣도록 표시한다. |
| Stop | 이번 요청에서 편집한 코드의 규칙 원문이 남았으면 한 번 막는다. 이번 요청에서 세션 작업본이나 편집한 작업본의 파일이 바뀌었는데 결정 기록(연결 과업의 기록, 연결이 없으면 `.local/decisions/` 전체)에 새 줄이 없으면 한 번 막고 남길 기록 경로와 `log.sh` 명령을 알린다. 이 확인은 과업을 연결했거나 바뀐 작업본이 기본 브랜치가 아닐 때만 한다. 같은 요청에서는 다시 막지 않고, `stop_hook_active`이면 막지 않는다. 계획 모드에서는 막지 않는다. |

- 규칙 조회기는 `scripts/rules/read_rules.py`이고 훅은 `scripts/hooks/task.py`의 `RULE_READER` 한 곳에서 찾는다. 위치를 옮기면 이 값만 고친다.
- 어떤 편집에 어떤 규칙을 넘길지는 `scripts/rules/rule-map.json`이 정한다. `rules`는 규칙 이름마다 원문 위치(스킬, 파일, 고를 절이나 뺄 절)와 sha256이고, `select`는 확장자·경로·내용 조건이 모두 맞을 때 더할 규칙 목록이다. 규칙 단위는 원칙 파일 하나, code-style 절 하나, 언어별 스킬 하나다.
- 내용 조건은 편집 입력(새 내용, 바꿀 글)에만 맞추고, 편집 입력이 없는 직접 조회는 기존 파일에 맞춘다.
- 지금 대응은 이렇다. 모든 코드 파일에는 `principle-prove-it-works`와 code-style 머리·원칙 절이 간다. 로직이 있는 파일에는 `principle-foundational-thinking`과 `principle-laziness-protocol`이 더해진다. 확장자로 언어별 스킬을 고르고(`.js` `.mjs` `.cjs` `.jsx`는 `code-style-typescript`에서 TypeScript 전용 절을 뺀 것, `.ts` `.tsx`는 전체와 `principle-type-system-discipline`), 테스트 파일이면 code-style 테스트 문서와 `principle-test-behavior-not-implementation`, `principle-sequence-verifiable-units`가, 동시성 낱말이 있으면 code-style 데이터 절과 `principle-separate-before-serializing-shared-state`, `principle-make-operations-idempotent`가 더해진다. 나머지 조건은 대응표를 본다.
- 규칙 원문을 고치면 `python3 scripts/rules/read_rules.py --check`가 바뀐 규칙과 새 sha256을 알린다. 선택 조건이 여전히 맞는지 본 뒤 대응표의 값을 고친다. 고치기 전에는 훅이 그 규칙을 넘기지 않고 조회 실패를 알린다.
- 훅이 실패하면 진단을 stderr에 남기고 빈 응답으로 끝난다. 세션 폴더가 git 저장소 안인 편집 도구의 PreToolUse만 복구 명령과 함께 거부한다.
- 시간 상한은 `scripts/hooks/entry.py`의 `HOOK_TIMEOUTS`가 훅 정의의 timeout과 같고, 진입점이 그보다 먼저 런타임을 끊는다. 런타임 안의 git 대기는 넘겨받은 마감 시각(`JUST_DO_DEADLINE`) 안에서 끝난다.

## 설치

1. 스킬을 설치한다. 설치기가 just-mode를 설치할 때 안정된 진입점 `~/.config/skills/just-do.py`도 함께 바꾼다. 훅 정의는 이 진입점만 부르고, 진입점은 `~/.<claude|codex>/skills/just-mode/scripts/hooks/hook.py`를 실행한다.
2. 플러그인을 설치한다. 카탈로그 정본은 저장소의 `.claude-plugin/marketplace.json`과 `.agents/plugins/marketplace.json`이고 플러그인 루트는 `just/`다.
3. Claude는 사용량 기록을 원하면 status line을 연결한다. 기존 명령의 입력·출력·종료 코드는 그대로 두고 `remove`가 원래 설정으로 되돌린다. Codex는 확인한 사용량 출처가 없어 80% 안내가 나오지 않는다.

```sh
python3 tools/skill-sync/scripts/install.py --source . --tool codex --tool claude-code
claude plugin marketplace add <스킬 정본 경로>
claude plugin install just-do@woon-skills
codex plugin marketplace add <스킬 정본 경로>
codex plugin add just-do@woon-skills
python3 ~/.claude/skills/just-mode/scripts/hooks/install_statusline.py install
```

- Codex는 대화형 시작 때 `/hooks`에서 새 훅을 한 번 신뢰해야 동작한다. `codex exec`는 신뢰 전 훅을 알림 없이 건너뛴다. 신뢰 우회 옵션은 쓰지 않는다.
- 실행 중인 호스트가 새 훅을 다시 읽는지는 따로 확인한다. 설치 성공을 지금 대화의 활성화로 보고하지 않는다.

## 확인

- 원본 저장소에서 `python3 -m pytest just/just-mode/scripts/hooks/tests`를 돌린다. 진입 안내, 결정 기록 꼬리, Stop 막기, 형제 워크트리 판정, 규칙 거부, 진입점 실패 처리, 매니페스트를 본다.
- 실제 동작은 임시 git 저장소에서 이벤트 JSON을 만들어 설치된 진입점에 직접 넣어 본다. 시험 통과를 실제 호스트 동작 확인으로 보고하지 않는다.
