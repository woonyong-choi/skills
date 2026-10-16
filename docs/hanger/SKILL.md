---
name: hanger
description: "Hanger closet에 등록한 Markdown 노트(경력 원본 포함)를 찾아 읽거나, 노트를 쓰고 고치고 병합하고 정리하거나, 메모와 링크와 파일을 inbox에 모으거나, closet을 등록하거나, Hanger 결정 질문에 답할 때 쓴다. 저장소 코드와 문서 작업, JD 맞춤 이력서와 포트폴리오 작성은 맡지 않는다."
---

# Hanger

노트 요청을 Hanger MCP 도구로 처리하고, Hanger가 한 말을 더하거나 빼지 않고 사용자에게 전한다.

Hanger는 사용자의 Markdown 노트 폴더(closet)를 검색하고, 바꿀 내용을 초안으로 만들어 검토한 뒤, 그사이 노트가 바뀌지 않았을 때만 쓰는 MCP 서버다. 노트 파일을 직접 고치지 않고 이 도구로만 처리한다.

## 언제 쓰나

- 노트를 찾거나 읽을 때 쓴다("JWT 노트 찾아줘", "지난번 회의 메모 보여 줘").
- 노트를 쓰거나, 고치거나, 병합하거나, 정리할 때 쓴다("이 내용으로 노트 만들어 줘", "두 노트 합쳐 줘").
- 경력 원본(`career/master.md`, `cases/`, 프로젝트 폴더)에 사실을 더하거나 고칠 때 쓴다("경력 원본에 이 프로젝트 추가해줘"). JD에 맞춘 이력서와 포트폴리오 작성은 [career](../career/SKILL.md)가 맡는다.
- 메모, 링크, 파일을 그대로 보관할 때 쓴다("이 링크 inbox에 넣어 둬").
- closet을 등록하거나 Hanger가 낸 결정 질문(`decision_required`)에 답할 때 쓴다.

## 쓰지 않을 때

- 저장소 코드와 문서(README, `docs/`, 스킬 원본) 작업에는 쓰지 않는다. **just-mode** 스킬이 맡는다.
- Hanger MCP 도구가 연결되지 않은 세션에서는 노트 파일을 직접 고쳐 대신하지 않고 연결이 필요하다고 보고한다.

## 시작

1. `list_closets`를 부른다.
2. closet이 없으면 사용자에게 closet 경로를 받아 그 절대 경로로 `register_closet`을 부른다. 폴더를 짐작하지 않는다.
3. closet이 여럿이면 모든 호출에 `closet`(`list_closets`의 id나 그 closet 안의 경로)을 넣는다. 지금 작업 폴더가 한 closet 안이면 묻지 않고 그 closet을 쓴다.

## 노트 찾기

1. 사용자 질문을 `query`로 넣어 `search_documents`를 부른다. 사용자가 위치를 말하면 `folders`(closet 기준 상대 경로)로 범위를 좁힌다.
2. 상위 결과에는 본문이 들어 있다. 목록에만 나온 문서는 `read_document`로 읽는다.
3. 사용자가 있다고 한 문서가 결과에 없으면 `fallback_reason: "user_reported_missing"`으로 다시 검색한다.

## 노트 바꾸기

1. 요청마다 `issue_key`로 새 키를 받는다. 다른 요청에 같은 키를 다시 쓰지 않는다.
2. 아래 요청 칸 절에 따라 `request_change`를 부른다.
3. `accepted`는 접수만 된 상태이고 끝난 것이 아니다. `job_status`가 `completed`, `deferred`, `conflict`, `failed`, `cancelled`, `expired` 중 하나가 될 때까지 확인한다.
4. 결과 상태와 `message`를 사용자에게 전한다.
5. `conflict`는 작업 중에 노트가 바뀐 상태다. 다시 판단할지 사용자에게 묻고, 동의하면 새 키로 `resolve_conflict`를 부른다.

### 요청 칸

`request_change`의 `intent`는 다음 칸으로 채운다.

- `kind`는 `write`(새 내용), `edit`(있는 노트 수정), `organize`(병합, 나누기, 연결) 중 하나다.
- `instruction`에는 사용자 말을 그대로 넣는다. 사용자가 붙여 준 메모도 고치지 않고 그대로 넣는다. Hanger가 그 메모를 근거로 인용한다.
- `query`에는 관련 노트를 찾을 검색어를 넣는다.
- `paths`에는 이미 있는 문서 중 사용자가 지목한 것만 넣는다. 새로 만들 문서 경로는 넣지 않는다.
- `folders`, `profile`(`note`, `wiki`, `work_record`, `blog`, `creative`), `allow_delete`는 사용자가 요구했을 때만 넣는다.

## 그대로 보관

- 글이나 파일을 바꾸지 않고 보관할 때는 `collect`를 부른다(`text`, 또는 `file`에 파일 절대 경로). 모델을 거치지 않고 closet의 `inbox/`에 저장한다.

## 결정 질문

`decision_required` 오류는 Hanger가 사용자의 결정을 기다리는 상태다. 주로 `.hangerignore`를 고치거나 지운 뒤에 생긴다.

1. 질문과 두 선택지(`approve`, `decline`)를 사용자에게 보인다.
2. 사용자 답을 기다린다. 한쪽이 뻔해 보여도 대신 고르지 않는다.
3. 결정 id와 사용자 답으로 `decide`를 부른 뒤 원래 요청을 다시 한다.

## 메시지 전달

- Hanger 결과와 오류의 `Tell the user:` 부분은 더하거나 빼지 않고 사용자 언어로 번역해 그대로 전한다.
- `Then:` 부분은 사용자에게 전하지 않는다. AI가 실행할 다음 행동이다.
- closet, Hanger, `.hangerignore`, `HANGER.md`, 명령, 경로, id는 번역하지 않는다. "closet 경로를 알려 주세요"는 맞고, "노트 폴더 경로를 알려 주세요"는 틀리다.

## 하지 않는 것

- closet을 지우지 않는다. `remove_closet`은 항상 거절된다. 돌려받은 터미널 명령(`hanger closet remove`)만 사용자에게 안내한다.
- `.hangerignore`와 `HANGER.md`는 사용자의 규칙 파일이다. 사용자가 요청할 때만 직접 고친다.
- Hanger 대신 노트 파일을 직접 쓰는 우회를 하지 않는다. 실패하거나, 늦거나, 거절될 때도 하지 않는다.

## 답변

- 검색했으면 찾은 문서 경로와 질문에 답하는 내용을 적는다.
- 바꿨으면 최종 상태, `message`의 `Tell the user:` 번역, 바뀐 문서 경로를 적는다.
- 결정이나 충돌이면 질문과 선택지를 보이고 사용자 답을 기다리는 상태라고 적는다.

## 구분

- JD를 받아 이력서와 포트폴리오를 만드는 일은 [career](../career/SKILL.md)가 맡는다.
- 저장소 코드와 문서 작업은 **just-mode** 스킬이 맡는다.
