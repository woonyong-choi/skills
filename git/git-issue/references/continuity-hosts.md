# 호스트 연결

기록·복구 공통 계약은 [작업 기록과 복구](continuity.md). 해당 절만 읽기. 실제 시험의 환경·결과·미검증 범위는 연결 이슈와 검증 기록에 두며 규칙으로 승격 금지

## 실행 환경

Python 3.9 이상, macOS/Linux, 표준 라이브러리, git, 인증된 gh. 기록 루트: 환경 변수 `ISSUE_CONTINUITY_ROOT` 하나(훅·status line·continuity.py 공통, 판정 정본 continuity.py `default_root`). 없으면 등록 Vault의 `legacy/orchestration`(이전 기본 위치의 기록은 첫 실행 때 한 번 옮김, Vault 미등록이면 오류). 다른 위치가 필요하면 호스트를 실행하는 환경에 이 변수 설정. continuity.py 전역 `--root`는 그 실행 한 번만 변경, 훅 미적용. 개인 경로를 공통 필수 경로로 간주 금지

## 훅

- 이 스킬 폴더가 work-continuity 플러그인 루트. 플러그인은 훅만 제공(스킬은 skill-sync 설치), 두 제품이 같은 scripts 사용, 훅 JSON만 제품별
- 사용량: Claude는 status line의 현재 context_window를 과업 폴더 `meter.json`에 기록. Codex는 검증한 사용량 출처 없음(unknown). 검증 불가 시 unknown, 계정 한도·누적 사용량으로 추정 금지
- PostToolUse 75%: 다음 안전한 작업 경계에서 저장 요청. 80% 이상: 미저장 기록 정리를 새 작업보다 우선. `checkpoint --sync` 후 남은 범위는 새 서브에이전트에 인계. 압축 주기마다 임계값별 한 번만. 작업 중단·강제 압축 없음
- PostToolUse 머지: 셸의 `gh pr merge`·`gh api` PUT `pulls/N/merge` 성공 뒤 career-record → repo-docs-journal 기록 확인 안내(Vault 등록 필요, career-record는 Vault에 `career/`가 있을 때만). 웹 화면·MCP 머지는 감지 안 함, 머지한 에이전트가 직접 확인(git-branch 머지 절)
- PreToolUse: 구조화된 파일 도구의 문서 경로 검사와 셸 문서 쓰기 거부(정본 repo-docs `references/project-context.md`). 로그 리디렉션은 `.log`, `.txt`·`.md` 등 문서 확장자 리디렉션은 문서 쓰기로 거부. Codex 셸(`tool_name` `Bash`)의 `apply_patch`·`applypatch`(heredoc 포함)는 구조화 apply_patch와 같은 경로 검사, 패치 본문이 명령에 없으면 거부. Vault·프로젝트 미등록, 영역 이탈은 거부. 편집 도구(셸 `apply_patch` 포함)는 필수 원문 미전달 시 조회 명령 안내와 함께 거부, 읽기·실행 명령은 비대상. SessionStart 주입·bind 안내는 git 작업본에서만
- PreCompact: 작성된 기록 동기화 시도 후 실제 파일·원격 재조회 대조, 실패는 로컬 보존·SessionStart 안내. 새 의미 요약 생성 없음
- PostCompact·SessionStart·UserPromptSubmit: 복구 필요 표시 또는 복구 명령 연결. 모든 요청에 전체 이슈 재주입 금지
- SessionStart: 등록 Vault·프로젝트·두 진입점 검사 결과와 실제 checkpoint 대조 실패 안내. 미등록 환경은 자동 추정 대신 등록 오류 보고. 안내 훅이 임의 셸·외부 앱 쓰기를 차단한다고 표현 금지. 같은 상태의 주입 문구는 같은 바이트(시각·임의 순서 금지)
- 요청·응답 원문: 두 제품 모두 UserPromptSubmit `prompt`, Stop `last_assistant_message` 우선, 없으면 아래 호스트별 출처의 transcript 끝부분. 둘 다 없으면 있는 값만 저장. 저장 위치·상한은 continuity.md
- Stop: continuity.md의 Stop 알림 조건에서 한 번 보완 요청. PostToolUse에서 본 checkpoint 명령은 주장으로만 기록, Stop에서 실제 저장·동기화 대조. Stop 재진입 무한 반복 금지
- SessionEnd: 종료 표시와 로컬 기록 대조 결과만. 강제 종료 시 새 기록 생성 보장 없음
- 계획 모드: 원격 쓰기 없음. 실행 작업으로 자동 전환 금지
- 과업 선택: 현재 세션의 명시 bind 우선, 중복 연결이면 자동 선택 거부. `ISSUE_CONTINUITY_TASK`는 미등록 세션의 초기 힌트이며 새 bind 덮어쓰기 금지. 둘 다 없으면 같은 저장소 binding이 하나일 때만 선택
- 시간 예산: `hook_entry.py` `HOOK_TIMEOUTS`가 훅 JSON의 이벤트별 timeout과 같고(시험이 대조), 진입점은 그보다 먼저 런타임을 끊고 런타임 내부 git·gh 대기 상한은 넘겨받은 마감 시각(`WORK_CONTINUITY_DEADLINE`) 이내. 마감 초과는 처리 오류
- 훅 파일 누락·처리 오류·시간 초과: 구조화된 파일 쓰기와 셸 `apply_patch`·`applypatch`는 거부, 그 밖 셸·이벤트는 진단 후 비차단 종료(설치 복구 경로 보존, 문서 검사 완료로 해석 금지). 기록·초기화 준비 실패 유지, 재시도 루프·종료 0의 성공 해석 금지

## 호스트별 출처

정본: continuity.py `HOSTS` 어댑터 하나. 다른 위치의 호스트 분기 추가 금지

- Claude transcript: payload `transcript_path`. 요청·응답: `user`·`assistant` 줄의 `message.content` text 블록, `isMeta`·`isCompactSummary`·도구 결과 제외
- Codex transcript: payload `transcript_path`, 없으면 `session_id`로 `$CODEX_HOME/sessions/*/*/*/rollout-*-<ID>.jsonl` 조회. 세션 폴더 안 일반 파일·첫 줄 session_meta ID 일치의 유일한 후보만, 링크·중복 거절
- Codex 요청: `event_msg` `user_message`(입력 원문) 또는 `item_completed` `UserMessage`의 `content[].text`(0.162). `response_item` user 메시지는 환경·지침 주입 포함이라 제외. 응답: `agent_message`, `item_completed` `AgentMessage`, `task_complete` `last_agent_message`, `response_item` assistant `output_text`
- 캐시 지표 Claude: `message.usage`의 `input`(캐시 밖)·`cache_read`·`cache_creation`, 같은 `message.id` 중복 줄 병합
- 캐시 지표 Codex: `token_count` `last_token_usage`의 `input`(캐시 포함)·`cached_input`, `cache_write_input_tokens`가 있으면 `cache_write`, 없으면 `uncached_input`(차이). Claude `cache_creation`과 동일 지표 주장 금지. 같은 `total_token_usage` 반복 줄 제외

## 캐시 측정

- `continuity.py cache-report --transcript <JSONL> [--host claude|codex]`: 요청별 호스트 지표와 읽기 비율 JSON, 본문 출력 없음. `--host` 생략 시 내용으로 판정, 판정 불가는 종료 2. 훅 매 턴 출력 없음
- 읽기 비율: Claude `cache_read / (input + cache_read + cache_creation)`, Codex `cached_input / input`
- 경계: 첫 요청·세션 변경(Claude `sessionId`, Codex `session_meta`)은 `start`, `compact_boundary`·`compacted` 뒤는 `compact`. `spike_metric`(Claude `cache_creation`, Codex `cache_write`, 없으면 `uncached_input`)이 1024와 경계 밖 중앙값 2배 중 큰 값 이상이면 spike, 경계 spike는 `boundary_spikes`
- 판정: 같은 상태의 SessionStart 재시작 뒤 `boundary_spikes` 반복이면 주입 문구 변동 후보. 첫 요청의 생성은 정상 비용, 단일 기록으로 원인 확정 금지

## 설치와 검증

- 활성화 전 기존 훅 보존과 실제 환경 시험 필수. 설치와 훅 신뢰·활성화는 별도 확인
- 갱신 순서(사용자 요청 시): 정본 검사 → 기존 설치기로 두 제품 스킬 동기화(훅이 같은 설치 루트의 developer-thinking 원문·조회기 사용) → `scripts/upgrade_plugin.py codex`와 `claude` → 새 정의 신뢰 확인 → 실제 훅 검사. 제품 CLI 필요, 출력은 설치 결과·보존 경로 JSON, 실패 종료 2
- 안정된 진입점: 사용자 스킬 설정의 `work-continuity.py`. 공유 잠금으로 실행 중 런타임 보호, 설치기는 배타 잠금으로 교체. 갱신기는 공식 CLI 사용, 사라진 옛 훅 정의·진입점만 호환 복원. 캐시 경로만 참조하는 옛 훅은 공식 설치 중 경로 삭제 가능, 무중단 보장 금지. 가짜 성공 스크립트·신뢰 우회 금지
- 플러그인 카탈로그 정본: 저장소의 `.claude-plugin/marketplace.json`과 `.agents/plugins/marketplace.json`

```sh
python3 <skill-sync 스킬 폴더>/scripts/install.py --source <스킬 정본 경로> --tool codex --tool claude-code
claude plugin marketplace add <스킬 정본 경로>
claude plugin install work-continuity@woon-skills
codex plugin marketplace add <스킬 정본 경로>
codex plugin add work-continuity@woon-skills
python3 <이 스킬 폴더>/scripts/install_statusline.py install
```

- Codex: 대화형 시작 시 폴더 신뢰와 `Hooks need review` 확인 표시. `codex exec`는 신뢰 전 훅을 알림 없이 건너뜀, 대화형 TUI(`/hooks`)에서 한 번 신뢰 후 사용. 신뢰 우회 옵션 금지
- 실행 중 호스트의 새 훅 재로드는 별도 확인. 설치 성공을 현재 대화 활성화로 보고하거나 반복 재시작 요구 금지
- Claude status line: `install_statusline.py install|remove [--home]`. 기존 설정 전체와 훅 보존, 원래 명령의 입력·출력·종료 코드 유지. remove는 원래 status line 복구, 이후 사용자가 바꾼 설정은 덮어쓰기 거부. 출력: 변경 여부와 종료 0, 실패 stderr·2
- 누락 훅 종료 검증: 스킬 원본 저장소에서 `python3 -m pytest git/git-issue/tests`(pytest 필요, 설치본에 tests 없음). 실제 셸 명령의 종료·진단만 확인, 실제 호스트의 초기화·복구는 별도 검증

## 문맥 초기화

- 정상 흐름: 결정·결과·남은 행동 기록 → `checkpoint --sync --event 인계` → `restore --verify-clear` → 지원 호스트의 `/clear` → 연결 이슈 복구 → 필요한 규칙 조회 → 다음 행동
- `--verify-clear`: 로컬·원격 기록 동일, 미전송·충돌 없음, 저장 후 작업본 변경 없음, 필수 필드 유효성 검사. 실패 시 준비 완료 표시 금지. 의미 누락은 실행자가 목표·제약·가설·결과·다음 행동 대조. 확인 후 새 변경이 있으면 다시 저장·검증
- `/clear`는 대화 문맥만 비움, 이슈·파일 보존. 초기화 후 SessionStart가 복구 명령 제공. 연결 이슈 확인 없이 재개 금지
- 컨텍스트가 차면 checkpoint 저장·검증 후 남은 범위를 새 서브에이전트에 인계
- 훅은 `/clear` 호출 불가. 수동 `/clear`를 지원하는 호스트만 `/clear` 후 `연결 이슈에서 이어서 진행` 안내. 미지원이면 기록 보존·제한 보고. 자동 초기화·무인 재개 완료 표시 금지
- `/compact`는 정상 흐름에서 호출 금지. 자동 압축이 먼저 발생했을 때만 [훅](#훅)의 복구를 대비책으로 사용
