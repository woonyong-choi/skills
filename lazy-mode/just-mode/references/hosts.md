# 호스트 대응표

lazy-mode 스킬이 공통으로 쓰는 동작을 Claude Code CLI, Codex CLI, OpenCode에서 실행하는 방법. 스킬 본문은 동작 이름만 쓰고 이 표를 가리킨다. 호스트 이름으로 지시를 나누는 곳은 이 파일 하나다.

## 현재 호스트 알아내기

- Claude Code: `Agent`(또는 `Task`) 도구와 `/` 명령이 있음. 환경 변수 `CLAUDECODE=1`
- Codex: `apply_patch` 도구가 있음. 스킬은 `$이름`으로 부름
- OpenCode: `task` 도구와 `skill` 도구가 있음
- 모르면 셋 다 아닌 것으로 보고 "서브에이전트 없음" 방식으로 진행

## 동작별 실행 방법

| 동작 | Claude Code | Codex | OpenCode |
|---|---|---|---|
| 스킬 부르기 | `/이름` | `$이름` | `/이름`(`opencode/slash` 메타데이터가 있을 때) 또는 `skill` 도구 |
| 서브에이전트 실행 | `Agent` 도구. 같은 프롬프트를 여러 개 동시에 보내면 병렬 | 같은 세션 서브에이전트가 없으면 셸에서 `codex exec --cd <작업 폴더> "<프롬프트>"`를 백그라운드로 실행하고 출력 파일을 읽음 | `task` 도구(`general`, `explore` 서브에이전트) |
| 읽기 전용 서브에이전트 | `Agent` 도구의 탐색용 에이전트 또는 프롬프트에 "파일 수정 금지" | `codex exec --sandbox read-only` | `explore` 서브에이전트 |
| 다른 회사 모델로 검토 | 셸에서 `codex exec "<프롬프트>"` | 셸에서 `claude -p "<프롬프트>"` | 설정한 다른 제공자 모델로 `task` 실행, 없으면 셸에서 `claude -p` 또는 `codex exec` |
| 주기적으로 다시 깨우기 | `/loop <간격> <프롬프트>` | 내장 기능 없음. 세션 안에서 대기 명령(`sleep`)과 확인을 반복하거나 셸 반복문으로 `codex exec` 재실행 | 내장 기능 없음. 셸 반복문으로 `opencode run` 재실행 |
| 사람에게 묻기 | 질문 도구가 있으면 사용, 없으면 답변으로 질문 | 답변으로 질문 | 답변으로 질문 |
| 프로젝트 전용 스킬 위치 | `.claude/skills/<이름>/` | `.agents/skills/<이름>/` | `.claude/skills/`, `.agents/skills/`, `.opencode/skills/` 모두 읽음 |
| 항상 적용 규칙 | `CLAUDE.md` | `AGENTS.md` | `AGENTS.md` |
| 대화 기록 위치 | `~/.claude/projects/<프로젝트 경로를 -로 바꾼 이름>/*.jsonl` | `~/.codex/sessions/**/rollout-*.jsonl` | `~/.local/share/opencode/` 아래 세션 저장소 |

## 서브에이전트 공통 규칙

- 프롬프트에 파일 내용을 붙이지 않고 파일 경로를 넘김
- 쓰기 작업 서브에이전트마다 별도 git 워크트리(`git worktree add`)를 주어 같은 파일을 동시에 고치지 않게 함
- 모델은 [역할별 모델](models.md)에서 고름
- 서브에이전트 정의 파일(`just-agent`, `comment-sicko`)이 설치돼 있으면 그 이름을 쓰고, 없으면 같은 지시를 프롬프트 첫머리에 넣음
- 결과는 그대로 전달하지 않고 부모가 diff를 직접 확인한 뒤 요약

## 없는 기능을 만날 때

- 호스트에 없는 동작은 표의 대체 방법으로 하고, 대체도 불가능하면 그 단계를 건너뛴 이유를 답변에 한 줄로 적음
- 클라우드 실행, 자동 리뷰 봇 같은 외부 서비스는 있으면 쓰고 없으면 로컬 서브에이전트로 대신함
