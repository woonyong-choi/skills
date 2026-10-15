# 새 저장소 보드 초기화

- 개발 요청은 해당 저장소의 작업 보드 생성·설정까지 포함. 별도 설정 요청 대기 금지. GitHub 원격 없음·사용자 생략 지시는 제외([과업 연결](../SKILL.md#과업-연결과-기록)). 소유 조직의 금지 정책·권한 부족은 우회 금지
- 첫 실행: `python3 <이 스킬 폴더>/scripts/project_bootstrap.py --repo owner/name`. macOS/Linux, Python 3.9 이상, 표준 라이브러리, 인증된 gh와 프로젝트 쓰기 권한 필요. 출력 JSON의 project.number·url 사용, 번호 추정 금지
- 보드 없음: 비공개 프로젝트 생성·저장소 연결·다섯 상태·BOARD·완료 제외 필터 설정. 기존 연결 하나는 재사용, 복수·닫힌 보드는 `--project`로 선택. 기존 보드의 값·뷰 임의 초기화 금지
- 재실행: `~/.config/skills/project-locks`의 저장소별 잠금 안에서 원격 재조회. 생성 직후 연결 실패 시 출력 URL 확인 후 복구, 새 보드 재생성 금지. 다른 호스트의 동시 생성은 막지 못하므로 생성 담당자 하나 유지
- 쓰기 범위: 제한된 CLI는 잠금 디렉터리와 현재 작업 기록 경로만 허용. 전체 샌드박스 해제·권한 거부 우회 금지. `--audit`는 원격 읽기 전용, 잠금 파일 없음, 오류 종료 2
- 종료 0은 구조 조회·설정 성공만 의미. `automation_verified=false`는 브라우저 검증 미완료, 전체 준비 성공으로 해석 금지
- 실행자가 출력 URL을 인증된 브라우저 도구로 열고 아래 설정·재조회 수행. 사용자에게 떠넘기거나 수동 명령만 제시하고 완료 금지. 브라우저 도구가 없으면 미완료 기록, 사용 가능한 연결부에서 이어서 설정
- 호스트 연결: Claude Code는 공식 Chrome 연동의 실제 도구 호출과 `/chrome`의 Enabled by default 확인. Codex는 현재 도구 목록의 브라우저 연결 확인. MCP 목록만으로 접근 가능·불가 단정 금지. 사이트 승인·인증 거부는 실패 동작과 이유 보고 후 승인 요청, 다른 도구 우회 금지

위치 → 필수 설정·재조회:

- 지정 작업 뷰 → Board, Group by Status, 보류 표시, 완료 제외 필터 저장
- Workflows → Auto-add to project → 저장소를 정확히 선택, `is:open` 필터, Enabled. Save 후 다시 열어 저장소·필터·Enabled 확인
- Item added to project → 이슈와 PR 모두, Status 대기, Enabled
- Item closed → 이슈와 PR 모두, Status 완료, Enabled
- Pull request merged → Status 완료, Enabled
- Auto-close issue → Disabled. 카드 이동으로 완료 판정·이슈 닫기 금지

- 브라우저 UI의 현재 이름·대상을 조회하여 조작. 비공개 API·쿠키 추출·고정 좌표 추정·워크플로 이름만으로 설정 확인 대체 금지
- 실제 검증: 첫 열린 이슈 생성 → set/bind/check --fix 없이 자동 등록·대기 조회 → 착수 bind → 상태별 checkpoint → 완료 근거 기록·닫기 → 수동 보정 없이 자동 완료 조회. 실패하면 설정 위치로 복귀, check --fix로 고친 결과를 자동화 통과로 표시 금지
- 검증용 독립 이슈는 실제 보드 동작의 관측 조건으로 작성하고 성공 근거 후 닫기. 재실행은 열린 검증 이슈 재사용. 업무와 무관한 운영 이슈를 시험 대상으로 변경 금지
- 기존 저장소에서 자동화가 없어지거나 동작하지 않으면 같은 절차 재개. 브라우저 전체 검사는 최초 설정·변경·실패 시에만, 매 checkpoint 반복 금지
