---
name: hanger
description: "저장소 코드·문서 작업과 JD 맞춤 이력서·포트폴리오 작성은 제외, Hanger closet에 등록한 Markdown 노트(경력 원본 포함)를 찾아 읽거나, 노트를 쓰고 고치고 병합·정리하거나, 메모·링크·파일을 inbox에 모으거나, closet을 등록하거나, Hanger 결정 질문에 답할 때 사용."
---

# Hanger

**노트 요청을 Hanger MCP 도구로 처리하고, Hanger의 말을 더하거나 빼지 않고 사용자에게 전달**

- 우선순위: 사용자 지시 → 저장소 규칙 → 이 스킬. 범위 밖은 명시한 소유 스킬 적용
- 범위: closet 확인·등록, 노트 검색·읽기, 노트 작성·수정·병합·정리, inbox 수집, 결정 질문, Hanger 메시지 전달

Hanger는 사용자의 Markdown 노트 폴더(closet)를 검색하고, 바꿀 내용을 초안으로 만들어 검토한 뒤, 그사이 노트가 바뀌지 않았을 때만 쓰는 MCP 서버. 노트 파일을 직접 고치지 않고 이 도구로만 처리

## 언제 쓰나

- 노트 찾기·읽기: "JWT 노트 찾아줘", "지난번 회의 메모 보여 줘"
- 노트 쓰기·고치기·병합·정리: "이 내용으로 노트 만들어 줘", "두 노트 합쳐 줘"
- 경력 원본(`career/master.md`, `cases/`, 프로젝트 폴더)에 사실 추가·수정: "경력 원본에 이 프로젝트 추가해줘". JD 맞춤 이력서·포트폴리오 작성은 career
- 메모·링크·파일을 그대로 보관: "이 링크 inbox에 넣어 둬"
- closet 등록, Hanger가 낸 결정 질문(`decision_required`)

## 쓰지 않을 때

- 저장소 코드·문서(README, `docs/`, 스킬 원본) 작업: just-mode
- Hanger MCP 도구가 연결되지 않은 세션: 노트 파일 직접 편집으로 대신하지 않고 연결 필요를 보고

## 시작

1. `list_closets` 호출
2. closet이 없으면 사용자에게 closet 경로를 받아 그 절대 경로로 `register_closet`. 폴더 추측 금지
3. closet이 여럿이면 모든 호출에 `closet`(`list_closets`의 id 또는 그 closet 안의 경로). 현재 작업 폴더가 한 closet 안이면 묻지 않고 그 closet

## 노트 찾기

1. `search_documents`에 사용자 질문을 `query`로. 사용자가 위치를 말하면 `folders`(closet 기준 상대 경로)로 범위 축소
2. 상위 결과는 본문 포함, 목록에만 나온 문서는 `read_document`로 읽기
3. 사용자가 있다고 한 문서가 결과에 없으면 `fallback_reason: "user_reported_missing"`으로 다시 검색

## 노트 바꾸기

1. 요청마다 `issue_key`로 새 키 발급. 다른 요청에 같은 키 재사용 금지
2. 아래 요청 칸으로 `request_change` 호출
3. `accepted`는 접수 상태이고 완료 전. `job_status`를 `completed`·`deferred`·`conflict`·`failed`·`cancelled`·`expired` 중 하나가 될 때까지 확인
4. 결과 상태와 `message`를 사용자에게 전달
5. `conflict`: 작업 중 노트가 바뀐 상태. 다시 판단할지 사용자에게 묻고, 동의하면 새 키로 `resolve_conflict`

## 요청 칸

`request_change`의 `intent`:

- `kind`: `write`(새 내용), `edit`(있는 노트 수정), `organize`(병합, 나누기, 연결)
- `instruction`: 사용자 말 그대로. 사용자가 붙여 준 메모도 고치지 않고 그대로 포함(Hanger가 근거로 인용)
- `query`: 관련 노트를 찾을 검색어
- `paths`: 이미 있는 문서 중 사용자가 지목한 것만. 새로 만들 문서 경로는 제외
- `folders`, `profile`(`note`, `wiki`, `work_record`, `blog`, `creative`), `allow_delete`: 사용자가 요구했을 때만

## 그대로 보관

- 글이나 파일을 바꾸지 않고 보관: `collect`(`text`, 또는 `file`에 파일 절대 경로). 모델 없이 closet의 `inbox/`에 저장

## 결정 질문

`decision_required` 오류는 Hanger가 사용자의 결정을 기다리는 상태(주로 `.hangerignore` 수정·삭제 뒤)

1. 질문과 두 선택지(`approve`, `decline`)를 사용자에게 보여 줌
2. 사용자 답 대기. 한쪽이 뻔해 보여도 대신 선택 금지
3. 결정 id와 사용자 답으로 `decide` 호출 뒤 원래 요청 재시도

## 메시지 전달

- Hanger 결과·오류의 `Tell the user:` 부분: 더하거나 빼지 않고 사용자 언어로 번역해 그대로 전달
- `Then:` 부분: 사용자에게 전하지 않고 AI가 실행할 다음 행동
- 번역하지 않는 낱말: closet, Hanger, `.hangerignore`, `HANGER.md`, 명령, 경로, id. 예: "closet 경로를 알려 주세요"(맞음), "노트 폴더 경로를 알려 주세요"(틀림)

## 금지

- closet 제거: `remove_closet`은 항상 거절. 돌려받은 터미널 명령(`hanger closet remove`)만 사용자에게 안내
- `.hangerignore`·`HANGER.md` 직접 편집: 사용자가 요청할 때만. 사용자의 규칙 파일
- Hanger 대신 노트 파일을 직접 쓰는 우회: 실패·지연·거절 때도 금지

## 답변

- 검색: 찾은 문서 경로와 질문에 답하는 내용
- 변경: 최종 상태, `message`의 `Tell the user:` 번역, 바뀐 문서 경로
- 결정·충돌: 질문과 선택지, 사용자 답을 기다리는 상태
