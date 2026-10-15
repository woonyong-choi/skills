# 프로젝트 맥락과 문서 위치

- 적용: 저장소·등록 폴더의 첫 작업, 재개, 문서 쓰기 전. 코드·실행 설정·기존 승인 README·제품 계약의 임의 이동 금지
- 등록 Vault: 명시한 `WOON_KNOWLEDGE_ROOT` 우선, 없으면 `--register-vault <절대 경로>`로 기존 스킬 설정 `vault.json`에 저장한 경로
- Vault 미등록·접근 불가: 문서 쓰기 거부 → 사용자에게 Vault 절대 경로 요청 → `--register-vault`로 등록. 에이전트의 경로 추정·생성·대체·읽음 처리 금지
- 식별: Git 원격 주소와 실제 로컬 경로 대조. SSH·HTTPS 원격 정규화, 같은 Git common directory의 worktree는 같은 영역 사용. 비 Git은 등록 절대 경로 사용
- 이름: 저장소명, 충돌 시 소유자-저장소명, 재충돌 시 사용자 별칭 확인. 이름만 같은 영역 재사용 금지. Vault의 `worktree/`와 Git worktree 생성 위치 구별

정본 → 위치:

- 지침·프로젝트 맥락 → `worktree/<프로젝트>/agent/`
- 필수 진입·조건별 읽기 목록 → 같은 영역의 `agent/index.md`
- 프로젝트 문서 → 같은 영역의 `docs/`
- 실제 문서 첨부 → Vault의 `assets/<확장자>/`
- 일반 대화 산출물·정리 전 입력·공개 지정 원고 → 각각 `legacy/`, `inbox/`, `publish/`
- 진행·결정·다음 행동·실행 근거 → 기존 이슈·Continuity 기록(git-issue) 재사용, Vault에 상태 사본 생성 금지. 요청한 회고 기록만 repo-docs-journal

## 진입과 이전

- 루트 AGENTS는 아래 연결 안내만 유지. CLAUDE 연결: repo-docs-root CLAUDE.md 절. 긴 사본 금지
- 기존 루트 지침의 유효 조건·범위·예외를 먼저 대조하여 agent 정본에 이전한 뒤 연결로 교체. 상위·전역 지침은 적용 범위 링크로 유지, 다른 프로젝트 지침 이동 금지
- index는 필수 규칙과 조건별 자료만 연결. agent 전체 자동 읽기 금지. 경로·읽기 버전·현재 결정은 작업 경계에서 기존 Continuity 결과·다음 필드에 기록, 공개 이슈에는 비공개 경로 전재 금지
- 읽어야 할 자료와 실제 조회한 자료 구별. 해시·조회 성공은 모델의 이해나 내부 맥락 전체 관측 증거가 아님. 압축 후 필수 규칙 재조회

```text
작업 전 <등록 Vault>/worktree/<프로젝트>/agent/index.md를 반드시 읽는다.
필수 규칙과 현재 작업에 필요한 자료만 읽는다. 연결 실패 시 작업을 보류한다.
지침·맥락과 신규 작업 문서는 등록 Vault의 지정 경로에서만 작성·갱신·조회한다.
사용자의 명시적 요청·승인 없이 프로젝트에 추가 문서나 맥락 사본을 만들지 않는다.
```

## 등록 및 검사 계약

index 첫 줄의 메타데이터로 프로젝트를 식별. 별도 상태 저장소 생성 금지

```text
<!-- project-context: {"identity":"github.com/owner/repo","paths":["/registered/project"],"common":"/registered/project/.git","approved_documents":[{"path":"README.md","approval":"기존 사용자 승인 문서"}]} -->
```

- 원격 없는 Git identity는 `git:<Git common directory>`, 비 Git은 `path:<등록 절대 경로>`. 경로 이동·원격 변경은 등록 대조 후 수정, 자동 병합 금지
- `approved_documents`는 명시적 사용자 승인 근거와 정확한 상대 파일 경로만. glob·전체 저장소 예외 금지. 기존 문서라는 사실만으로 새 사본 생성 허용 금지
- `source_document_roots`: 스킬 정의처럼 실행 제품 자체인 문서 소스의 상대 폴더와 보존 근거. 일반 작업 기록의 예외로 사용 금지
- 등록: `--register-project`, 이름 지정은 `--name`. 기존 긴 지침의 이전은 `--migrate` 명시 시에만 수행. 원문을 Vault agent에 보존한 뒤 루트 연결로 교체, 외부 심볼릭 링크의 지침 이전 거부
- Python 3.9 이상, 표준 라이브러리와 git 필요. git-issue 스킬의 `scripts/project_context.py --project <작업 경로>`로 진입 검사, `--write <문서 절대 경로>`로 쓰기 경로 검사. stdout JSON, 실패 종료 2
- `--read <선택한 agent 문서> --task-record <기존 checkpoint.json>`: 해당 파일만 출력하고 경로·SHA-256을 기존 로컬 기록의 context_reads에 갱신. 다른 프로젝트 기록이면 거부. 원격 이슈 자동 게시 없음
- 문서 검사 연결: `repo-docs/scripts/check_doc.py --project <작업 경로> <문서>` 사용. 연결·경로 실패 시 문체 검사에 앞서 종료 2
- 검사 범위: 등록·원격/로컬 일치·중복 identity·Vault 밖 심볼릭 링크·두 진입점·허용 경로. 지침 의미 보존·사용자 승인 진위는 원문 대조 필수
- 문서 작성자는 경로 검사 성공 후 작성. 일반 셸·외부 앱의 임의 쓰기까지 강제 차단하는 보안 경계로 표현 금지
- 자동 연결: Work Continuity의 `PreToolUse`가 Claude `Write/Edit/MultiEdit`, Codex `apply_patch`의 문서 경로 검사. 대상 확장자는 `md/mdx/rst/adoc/txt/docx/pdf`. 미등록·영역 이탈은 실행 전 거부
- 셸: 감지한 문서 쓰기는 구조화된 파일 도구 사용 안내와 함께 거부. 로그는 `.log`로 리디렉션(`.txt`·`.md` 리디렉션은 문서 쓰기로 거부), 요청 본문의 문서 경로는 쓰기 아님. 계산된 경로·임의 스크립트·MCP·외부 앱·HTML 전체 쓰기의 완전 차단은 미지원
