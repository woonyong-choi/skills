# 호스트 연결

기록·복구 공통 계약은 [작업 기록과 복구](continuity.md). 해당 절만 읽기. 실제 시험의 환경·결과·미검증 범위는 연결 이슈와 검증 기록에 두며 규칙으로 승격 금지

## 실행 환경

Python 3.9 이상, macOS/Linux, 표준 라이브러리, git, 인증된 gh. 기록 기본 루트는 `~/workspace/woon/.local/orchestration`, 다른 환경은 continuity.py 전역 `--root`로 지정. 개인 경로를 공통 필수 경로로 간주 금지

## 훅

- 이 스킬 폴더가 work-continuity 플러그인 루트. 플러그인은 훅만 제공(스킬은 skill-sync 설치), 두 제품이 같은 scripts 사용, 훅 JSON만 제품별
- 사용량: Claude는 status line의 현재 context_window, Codex는 아래 세션 메타데이터 어댑터. 검증 불가 시 unknown, 계정 한도·누적 사용량으로 추정 금지
- PostToolUse 75%: 다음 안전한 작업 경계에서 저장 요청. 80% 이상: 미저장 기록 정리를 새 작업보다 우선. 압축 주기마다 임계값별 한 번만. 작업 중단·강제 압축 없음
- PreToolUse: 구조화된 파일 도구의 문서 경로 검사와 셸 문서 쓰기 거부(정본 repo-docs `references/project-context.md`). Vault·프로젝트 미등록, 영역 이탈은 거부. 필수 원문 미전달 시 조회 명령 안내와 함께 거부
- PreCompact: 작성된 기록 동기화 시도, 실패는 로컬 보존. 새 의미 요약 생성 없음
- PostCompact·SessionStart·UserPromptSubmit: 복구 필요 표시 또는 복구 명령 연결. 모든 요청에 전체 이슈 재주입 금지
- SessionStart: 등록 Vault·프로젝트·두 진입점 검사 결과 안내. 미등록 환경은 자동 추정 대신 등록 오류 보고. 안내 훅이 임의 셸·외부 앱 쓰기를 차단한다고 표현 금지
- Stop: continuity.md의 Stop 알림 조건에서 한 번 보완 요청. Stop 재진입 무한 반복 금지
- SessionEnd: 종료 표시만. 강제 종료 시 새 기록 생성 보장 없음
- 계획 모드: 원격 쓰기 없음. 실행 작업으로 자동 전환 금지
- 과업 선택: 현재 세션의 명시 bind 우선, 중복 연결이면 자동 선택 거부. `ISSUE_CONTINUITY_TASK`는 미등록 세션의 초기 힌트이며 새 bind를 덮지 않음. 검증된 관리 창에서는 창의 활성 과업을 따르고 시작 cwd·옛 환경변수로 복귀 금지
- 훅 파일 누락·처리 오류: 구조화된 파일 쓰기는 거부, 셸·그 밖 이벤트는 진단 후 비차단 종료(설치 복구 경로 보존, 문서 검사 완료 의미 아님). 기록·초기화 준비 실패 유지, 재시도 루프·종료 0의 성공 해석 금지

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

- Codex: CLI `/hooks`에서 훅 정의 검토·신뢰 필요. 신뢰 우회 옵션 금지
- 실행 중 호스트의 새 훅 재로드는 별도 확인. 설치 성공을 현재 대화 활성화로 보고하거나 반복 재시작 요구 금지
- Claude status line: `install_statusline.py install|remove [--home]`. 기존 설정 전체와 훅 보존, 원래 명령의 입력·출력·종료 코드 유지. remove는 원래 status line 복구, 이후 사용자가 바꾼 설정은 덮어쓰기 거부. 출력: 변경 여부와 종료 0, 실패 stderr·2
- 누락 훅 종료 검증: `python3 -m pytest <이 스킬 폴더>/tests`(pytest 필요). 실제 셸 명령의 종료·진단만 확인, 호스트 초기화·복구는 아래 실제 창 합격 조건으로 별도 검증

## 같은 창·제목의 자동 재개 계약

- 유지 대상: 사용자에게 보이는 작업 창·제목·저장소·이슈. 내부 세션 ID는 초기화 때 교체 가능. 기존 대화 기록 삭제 금지
- 플러그인은 준비 검증과 복구 자료 제공. 창을 소유하는 실행기가 초기화·제목 재설정·첫 입력 수행. 훅의 additionalContext 주입을 자동 실행으로 취급 금지
- 실행기 순서: 기존 창 ID·세션 ID·제목 확인 → 작업 종료와 사용자 입력 대기 확인 → 저장 검증 → 같은 창에서 새 문맥 생성 → 기존 제목 적용 → 새 세션 ID 확인 → 복구 입력 1회 → 목표·제약·다음 행동 일치 확인 → 다음 작업
- 전환마다 기록 버전과 고유 전환 ID 연결. 중단 후 새 세션이 이미 있으면 재사용. 제목이 같은 다른 창 검색·조작 금지
- 제목 적용·새 세션 확인·복구 중 실패: 중단하고 기존·새 세션 ID와 실패 단계 보존. 이전 창 닫기·복구 입력 중복 전송 금지
- Codex CLI: 공식 clear 명령은 같은 화면에서 새 대화를 만들고 인자로 제목 지정 가능. 작업 실행 중 사용 불가, 외부 실행기의 유휴 확인·입력 제어 필요
- 데스크톱: 실행 환경 도구 목록에서 같은 채팅 문맥 초기화·제목 유지·재개 입력 지원을 먼저 확인. 없으면 미지원 기록 후 중단. 새 채팅 생성을 같은 채팅 초기화로 취급, 접근 거부 시 내부 대화 DB·앱 번들 수정 우회, CLI 성공을 데스크톱 지원 근거로 사용 금지
- Claude Code: SessionStart의 sessionTitle은 startup·resume·fork에만 적용, clear 뒤 제목 복구에 단독 사용 금지. initialUserMessage는 비대화형 실행 한정. 대화형 clear 후 재개는 창 실행기에서 명령·입력과 결과 확인
- 합격: 두 제품 각각 실제 창 ID·전후 제목 동일, 세션 ID 교체, 이전 대화의 시험용 값 미전달, 이슈의 시험용 목표 복원, 후속 작업 정확히 1회 실행. 단위 시험으로 대체 금지

근거: [Codex 명령](https://learn.chatgpt.com/docs/developer-commands), [Claude 훅](https://code.claude.com/docs/en/hooks).

## CLI 창 실행기

기존 이슈에 bind한 뒤 정본의 실행기 사용. 실행 중 플러그인 교체·앱 재시작 불필요

```sh
python3 <이 스킬 폴더>/scripts/continuity_window.py --task 작업명 --host codex --title '작업 제목' --prompt-file 요청.txt
# Claude Code는 --host claude. 출력된 tmux attach 명령으로 같은 창에 접속.
```

- 필요: tmux, 로그인한 해당 CLI, 인증된 gh, 열린 이슈 연결과 유효한 초기 checkpoint. 기존 보안·승인·훅 설정 유지, 새 신뢰 요청 자동 승인 금지
- 소유 범위: 실행기가 만든 tmux 창 하나. 기존 CLI·데스크톱 창을 제목으로 찾아 붙잡기 금지. 같은 작업의 두 번째 실행기는 거부
- 창 home(`--task`)과 활성 과업 분리. 창 ID·제목·meter는 home에 유지, 과업·저장 기준은 현재 세션 bind를 따름. checkpoint 대기 중 과업이 바뀌면 초기화 없이 중단
- 기본: 사용량 `--threshold`(기본 75)% 이상에서 유휴 확인 후 전환. 계정 한도 미사용, 사용량 미확인은 추정 없이 대기. 의미 요약은 AI, 구조·저장·원격 일치·작업본 확인은 코드
- 기록 작성 전 최신 이슈 복구. 자동 초기화 기록의 goal·constraints가 기존 값과 다르면 전환 거부, 정당한 범위 변경은 먼저 일반 checkpoint로 기록. 나머지 필드 의미 보존은 실행자 확인
- Claude는 기존 출력을 보존하는 status line 사용, 입력 제안은 실행기 전용 설정에서 끄고 전역 설정 보존
- `--cycles 1`: 한 번 전환 후 제어기만 종료, 창 유지. 기본 0은 지속 감시. 초기화 직후 사용량이 임계값 아래로 내려간 뒤에만 다음 전환
- `--attach`: 기록된 관리 창의 pane·프로세스·window ID·host·실제 제목·유휴 상태 확인 뒤 입력 없이 감시 재개. 중복 제어기·신뢰·인증 대기·초기화 진행 중이면 거부. 멈춘 옛 제어기 재개용 아님
- `--recover`: 저장된 같은 창에서 초기화 이후 확인 단계만 복구. 창·호스트·제목·기록 버전 일치 필수. 새 세션 미확인 시 재초기화 금지. 재개 입력을 이미 보냈거나 불명확하면 중복 전송 거부
- window.json의 resumed는 복구 입력 후 유휴 도달이며 업무 완료 증명 아님. 네트워크·권한·기록·창 확인 실패는 blocked에 이유, 자동 재시작 루프 없음

### Codex 세션 메타데이터 어댑터

- 입력: 검증된 관리 창의 실제 훅 payload의 session_id·transcript_path. 명시 세션 bind가 창의 옛 active_task보다 우선. 훅은 창 home의 meter만 기록, 활성 과업 갱신은 관리기
- 지원: codex-cli 0.158.0에서 관측한 rollout 형식, 공식 고정 형식으로 간주 금지. session_meta의 ID·버전·세션 폴더·일반 파일 경계 확인, 다른 세션·심볼릭 링크·폴더 밖 경로 거절
- 계산: 마지막 완전한 token_count의 last_token_usage.total_tokens / model_context_window. 표시줄 비율과 동일 주장 금지. metadata와 해당 숫자·시각·압축 표시만 판독, 대화 본문 출력 금지
- 미확인: 다른 버전·형식·잘못된 숫자·오래된 시각·미완성 마지막 줄·압축 이후 새 metric 부재는 unknown. 세션 ID가 별도 검증되면 ID만 유지하여 초기화 직후 새 세션 확인
- 실행 경계: 계측값만으로 초기화 금지. 실제 유휴 화면·제목·pane·checkpoint 동기화 검증 동반. 단위 시험·설치 성공과 실제 훅 입력·창 초기화·후속 작업 1회 실행은 별도 근거

## 문맥 초기화

- 정상 흐름: 결정·결과·남은 행동 기록 → `checkpoint --sync` → `restore --verify-clear` → 지원 호스트의 `/clear` → 연결 이슈 복구 → 필요한 규칙 조회 → 다음 행동
- `--verify-clear`: 로컬·원격 기록 동일, 미전송·충돌 없음, 저장 후 작업본 변경 없음, 필수 필드 유효성 검사. 실패 시 준비 완료 표시 금지. 의미 누락은 실행자가 목표·제약·가설·결과·다음 행동 대조. 확인 후 새 변경이 있으면 다시 저장·검증
- `/clear`는 대화 문맥만 비움, 이슈·파일 보존. 초기화 후 SessionStart가 복구 명령 제공. 연결 이슈 확인 없이 재개 금지
- 훅은 `/clear` 호출 불가. 초기화·자동 재개 전 [같은 창·제목의 자동 재개 계약](#같은-창제목의-자동-재개-계약) 확인. 제어기가 없고 수동 `/clear`를 지원하는 호스트만 `/clear` 후 `연결 이슈에서 이어서 진행` 안내. 미지원이면 기록 보존·제한 보고. 자동 초기화·무인 재개 완료 표시 금지
- `/compact`는 정상 흐름에서 호출 금지. 자동 압축이 먼저 발생했을 때만 [훅](#훅)의 복구를 대비책으로 사용
