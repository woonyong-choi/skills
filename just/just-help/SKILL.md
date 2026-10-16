---
name: just-help
description: just 설정, /just-mode 사용법, 작업에 맞는 스킬·플레이북·원칙 고르기를 안내한다. 질문과 함께 /just-help를 부른다.
disable-model-invocation: true
---

# just 도움말

just에 관한 사용자 질문에 답하고, 사용자가 보낼 수 있는 프롬프트를 건네고, 답의 출처 파일을 링크한다. 도움말 질문이면 작업을 시작하지 않는다. 사용자는 방법을 물었고 just 실행은 실제 토큰을 쓰므로, 프롬프트는 사용자가 보내게 한다.

"just로 이 버그 고쳐 줘"처럼 작업을 요청하는 메시지는 도움말 질문이 아니다. [`just-mode`](../just-mode/SKILL.md)를 읽고 그 방식으로 작업하고, 항상 적용 규칙에 넣으면 매 턴 켜 둘 수 있다고 한 번 알린다.

이 파일은 질문을 답이 있는 스킬로 연결하는 지도다. 세부 내용은 그 파일들에 있다. 인용하기 전에 연결한 파일을 읽고, 이 지도와 다르면 그 파일을 믿는다. 여기의 링크는 설치된 스킬 폴더를 가리키므로 사용자가 열지 못할 수 있다. 사용자에게는 공개 사본을 준다. 주소는 `https://github.com/woonyong-choi/skills/blob/main/just/` 뒤에 스킬 폴더 기준 경로를 붙인 것이다.

호스트마다 다른 동작(스킬 부르기, 서브에이전트, 주기적으로 다시 깨우기, 규칙 파일)은 [호스트 대응표](../just-mode/references/hosts.md)에, 역할별 모델은 [역할별 모델](../just-mode/references/models.md)에 있다. 아래의 `/이름`은 Claude Code와 OpenCode 표기다. Codex에서는 `$이름`으로 바꿔 안내한다.

## 무엇이 필요한지 알아내기

메시지와 대화에서 필요를 추론한다. "PR 리뷰하는 스킬이 뭐야?"처럼 상황을 말했다면 바로 해당 절로 간다. 그래도 필요가 불분명하면 아래 선택지로 객관식 질문을 하나 하고, 고른 절만 답한다.

- 설정하기
- `/just-mode`로 작업 시작하기
- 상황에 맞는 스킬 고르기
- 잘못된 실행 고치기
- just를 내 것으로 만들기

답을 바꾸는 상태를 확인하고, 답이 바뀔 때만 언급한다.

- `~/.config/skills/models.json`이 없으면 이 사용자는 `/just-setup`을 돌리지 않았고, 모든 역할이 기본 모델을 쓴다.
- 프로젝트에 `verify-*` 스킬이나 다른 앱 검증 도구가 없으면 에이전트가 앱을 스크립트로 조작할 방법이 없다. 질문이 변경이 동작함을 증명하는 일에 관한 것이면 `/create-verification-skill`을 언급한다.

모델 설정이 없고 그것이 중요하면, 지금 역할마다 모델과 추론 예산을 고를지 사용자에게 질문한다. 사용자가 처음이거나, 질문이 설정이나 비용에 관한 것이거나, 답이 어떤 모델이 도는지에 달렸으면 중요하다. 대화당 한 번만 묻는다. 필요도 불분명하면 두 질문을 함께 묻는다. 선택지는 둘이다.

- 지금: 입력할 명령으로 `/just-setup`을 주고 질문에도 답한다.
- 나중에: 질문에 답하고, `/just-setup`을 돌리기 전까지 모든 역할이 기본 모델을 쓴다는 줄을 하나 더한다.

## 설정하기

1. 이 저장소 README의 설치 명령으로 스킬을 설치한다. Claude Code와 Codex의 사용자 스킬 폴더에 같은 내용이 들어간다. OpenCode는 `~/.claude/skills/`를 함께 읽는다.
2. [`/just-setup`](../just-setup/SKILL.md)을 돌린다. 추론 예산을 묻고, 역할마다 모델을 정하고, `~/.config/skills/models.json`을 쓴다. 설정은 그 뒤에 띄우는 서브에이전트부터 적용된다.
3. `/just-mode`와 목표, 통과하거나 실패할 수 있는 확인 조건으로 실제 작업을 시작한다.

설치만으로는 아무것도 바뀌지 않고, 사용자가 스킬을 불러야 동작한다. 사용자의 말만으로 호출되는 스킬은 `/just-setup` 하나다. 첫 프롬프트를 [`references/prompting.md`](references/prompting.md)에 따라 함께 다듬어 주겠다고 제안한다.

비용이 걱정이면 토큰이 어디에 쓰이고 어떻게 줄이는지 말한다. just는 서브에이전트와 검토 패널에 토큰을 더 쓴다. `/just-setup`을 다시 돌려 더 작은 예산이나 더 싼 모델을 고른다. 역할 값을 빈 문자열로 두면 호스트 기본 모델을 쓰므로, 호스트를 싼 모델로 돌릴 때 토큰이 줄어든다. `review` 목록의 항목 하나마다 서브에이전트 하나가 돌므로, 목록이 짧을수록 서브에이전트가 적게 돈다. `/just-mode`는 엄격함이 필요한 작업에만 쓴다.

just 스킬은 Agent Skills 형식이라 Claude Code, Codex, OpenCode가 모두 읽는다. 서브에이전트, 다른 회사 모델 검토, 주기적으로 다시 깨우기는 호스트마다 방법이 다르고, 호스트에 없는 기능은 [호스트 대응표](../just-mode/references/hosts.md)의 대체 방법으로 한다.

## `/just-mode`로 작업 시작하기

`/just-mode`는 작업을 플레이북에 맞추고, 플레이북 단계를 할 일 목록에 옮기고, 단계가 필요로 할 때 다른 스킬을 돌린다. 건너뛴 단계는 `skip: <이유>`로 목록에 남는다. 좋은 프롬프트는 목표와 끝났음을 알아보는 방법을 말한다. 스킬 목록은 적지 않는다. 손으로 쓴 순서는 플레이북이 지킬 단계를 빠뜨리거나 뒤섞기 쉽다. 프롬프트를 다듬어 주기 전에 [`references/prompting.md`](references/prompting.md)를 읽는다. 예시는 [`references/recipes.md`](references/recipes.md)에 있다.

`/just-mode`가 계속 켜져 있는지는 시작 방법에 달렸다.

- `/just-mode`로 메시지를 보내면 그 메시지에 스킬이 붙는다. 대화가 이어질수록 효과가 약해진다.
- 항상 적용 규칙 파일(호스트 대응표)에 "사소하지 않은 작업은 just-mode 스킬 방식으로 한다"를 넣으면 매 턴 적용된다.
- 둘 다 아니면 새 작업마다 `/just-mode`로 시작한다.

대화 중에 "새 작업"이라고 말하면 모드가 새 플레이북을 맞춘다. `/just-mode`는 플레이북 단계가 띄우는 서브에이전트에 이미 `just-agent`를 쓴다. 직접 띄우는 서브에이전트에서 같은 방식을 쓰려면 `just-agent` 서브에이전트로 띄운다. 정의가 설치되지 않은 호스트에서는 같은 지시를 프롬프트에 넣는다(호스트 대응표).

## 스킬 고르기

기본 답은 `/just-mode`다. 단계가 필요로 할 때 다른 스킬 대부분을 돌린다. 사용자가 플레이북이 하는 것보다 무언가를 더 원하거나 덜 원할 때 스킬을 직접 추천한다. 추천하기 전에 그 스킬을 읽고, 예시 프롬프트 하나를 준다.

| 사용자가 원하는 것 | 스킬 |
|---|---|
| 사소하지 않은 작업을 엄격하게 하기 | [`/just-mode`](../just-mode/SKILL.md) |
| 시작 전에 에이전트가 목표와 문제를 이해했는지 확인하기 | [`/in-your-own-words`](../in-your-own-words/SKILL.md) |
| 시작 전에 작업 목표를 더 높이기: 더 전문가답게, 결과 중심으로, 과하게 정하지 않게 | [`/sharpen`](../sharpen/SKILL.md) |
| 지금 코드가 어떻게 동작하는지, 새 코드를 어디에 둘지 알기 | [`/how`](../how/SKILL.md) |
| 코드가 왜 이런 모양인지, 숫자가 어디서 왔는지 알기 | [`/why`](../why/SKILL.md) |
| 변경이나 하위 시스템을 쉬운 말로 이해하기 | [`/teach`](../teach/SKILL.md) |
| 한 주제에 대한 최근 내 작업 따라잡기 | [`/recall`](../recall/SKILL.md) |
| 마지막 메시지 뒤 이 대화에서 바뀐 것을 짧은 문장 몇 개와 작은 그림으로, 할 일마다 결정할 만큼의 맥락과 함께 따라잡기 | [`/ketchup`](../ketchup/SKILL.md) |
| 작은 diff가 바깥에서 무엇을 깨뜨릴 수 있는지 알기 | [`/blast-radius`](../blast-radius/SKILL.md) |
| 함수 경계를 넘는 코드 전에 타입과 모듈 모양 정하기 | [`/architect`](../architect/SKILL.md) |
| 한 지시로 여러 시도를 받아 가장 좋은 것으로 합치기 | [`/arena`](../arena/SKILL.md) |
| 나눈 조각마다 병렬 확인을 돌리거나, 워커끼리 경주시키기(독립 서브에이전트) | [`/swarm`](../swarm/SKILL.md) |
| 다른 모델들이 diff를 검토하고 깨뜨려 보게 하기 | [`/interrogate`](../interrogate/SKILL.md) |
| 싼 로컬 테스트가 있을 때 테스트 먼저 버그 고치기 | [`/tdd`](../tdd/SKILL.md) |
| `.ts`, `.tsx` 작업에 TypeScript 규칙 적용하기 | [`/typescript-best-practices`](../typescript-best-practices/SKILL.md) |
| 주석을 쓰지 않은 검토자로 리뷰 전에 주석 걷어 내기 | [`/no-comments`](../no-comments/SKILL.md) |
| 글에서 AI 티 걷어 내기 | [`/unslop`](../unslop/SKILL.md) |
| 문서, RFC, README, PR 설명, 커밋 메시지를 기준에 맞게 쓰기 | [`/technical-writing`](../technical-writing/SKILL.md) |
| 마지막 답변을 쉬운 말로 다시 듣기 | [`/bro`](../bro/SKILL.md) |
| 에이전트가 앱을 스크립트로 조작해 동작을 증명할 수단 만들기 | [`/create-verification-skill`](../create-verification-skill/SKILL.md) |
| 검증 스킬과 그 기능 맵을 앱에 다시 맞추기 | [`/maintain-verification-skill`](../maintain-verification-skill/SKILL.md) |
| 성능 숫자를 보고하거나 그 숫자로 행동하기 전에 검증하기 | [`/benchmark-checklist`](../benchmark-checklist/SKILL.md) |
| 크거나 여러 곳에 걸친 변경, 또는 자리를 비웠다가 검토할 변경 돌리기 | [`/figure-it-out`](../figure-it-out/SKILL.md) |
| 실행 중 결정 기록을 남기고 나중에 검토하기 | [`/show-me-your-work`](../show-me-your-work/SKILL.md) |
| 역할마다 모델과 추론 예산 고르기 | [`/just-setup`](../just-setup/SKILL.md) |
| 내 작업 습관을 개인 모드 스킬로 만들기 | [`/automate-me`](../automate-me/SKILL.md) |
| 끝난 작업에서 배운 것을 스킬 수정으로 바꾸기 | [`/reflect`](../reflect/SKILL.md) |
| 이 저장소에서 에이전트가 같은 실수를 되풀이하지 않게 하기 | [`/correct`](../correct/SKILL.md) |
| just 안에서 길 찾기 | `/just-help` |

이 폴더 옆에 표에 없는 스킬 폴더가 있으면 그 frontmatter를 읽고 description으로 연결한다. `principle-*` 폴더는 아래 원칙에서 다룬다.

헷갈리기 쉬운 것:

- `/how`는 코드가 무엇을 하는지 설명한다. `/why`는 이유를 설명한다. `/teach`는 둘 중 하나나 둘 다 돌리고 결과를 쉬운 말로 설명한다.
- `/arena`는 모든 워커에게 같은 지시를 주고 가장 좋은 부분을 합친다. `/swarm`은 일을 조각이나 경주로 나누고 보고서 하나를 돌려준다.
- `/architect`는 설계를 정한 바로 뒤에 구현한다. 코드를 쓰기 전에 설계를 검토하려면 "체크포인트와 함께"를 덧붙인다.
- `/interrogate`는 diff를 검토한다. `/blast-radius`는 diff 바깥의 깨짐을 찾고, 변경을 안전하게 만드는 사실 하나를 증명한다.
- `/recall`은 최근 여러 대화에 걸친 맥락을 다시 세운다. `/ketchup`은 사용자의 마지막 메시지 뒤 이 대화만 다룬다. 특정 대화나 브랜치 하나를 재개하는 것은 세션 이어받기 플레이북이다.
- `/figure-it-out`은 엄격한 실행 하나를 설계한다. 오케스트레이션 플레이북은 여러 날과 많은 PR에 걸친 프로그램을 돌린다. 자율 실행 플레이북은 작업 하나를 종료 조건까지 몬다.

just에 없는 것:

- 주기적으로 다시 깨우기는 호스트 기능이다(호스트 대응표). 스킬 만들기 도구는 `skill-creator` 스킬이 설치돼 있을 때만 있다.
- just에는 `/orchestrate` 스킬이 없다. 오케스트레이션은 `/just-mode` 플레이북이다. 명령 목록에 `/orchestrate`가 보이면 다른 스킬 모음이 제공한 것이다.

## 플레이북과 원칙

플레이북은 스킬이 아니라 `/just-mode` 안의 단계 목록이라 따로 부르는 명령이 없다. `/just-mode` 안에서 작업을 설명하면 하나가 골라지고, 다음 표현은 플레이북을 직접 지목한다.

- "이 PR 봐 줘", "PR 123 확인해 줘"는 PR 돌보기를 돌린다. PR을 머지 준비 상태까지 끌고 가서 멈춘다. 사용자가 머지나 배포를 요청하지 않으면 머지하지 않는다.
- "스택 머지해 줘"는 배포를 돌린다.
- "이 브랜치 넘겨받아"는 세션 이어받기를 돌린다.
- "안전하게 멈춰"는 안전하게 멈추기를 돌린다.
- "이 대기열 완전 오토파일럿"은 오토파일럿 전체를 돌린다. "스택으로 쌓고 배포는 하지 마"는 오토파일럿 스택을 돌린다.
- "평가 플레이북 돌려"는 평가를 돌린다.

`/just-mode` 없이 "이 PR 봐 줘" 같은 표현을 쓰면 같은 일을 하는 다른 스킬이 대신 시작될 수 있다. [`just-mode`](../just-mode/SKILL.md)의 플레이북 절이 모든 플레이북과 적용 시점을 나열한다. PR 열기, PR 돌보기, 배포는 각각 `playbooks/opening-a-pr.md`, `playbooks/babysit.md`, `playbooks/shipping.md`에 있다.

just에는 계획 스킬이 없다. 호스트의 계획 모드가 있으면 함께 쓸 수 있다. 여러 단계나 쌓인 PR에 걸친 작업은 `/just-mode`에 계획을 요청하면 [여러 단계 또는 여러 PR 계획 플레이북](../just-mode/playbooks/multi-phase-plan.md)이 돈다. 이 플레이북은 계획을 쓰고 구현하지 않는다. 설계 질문은 프로토타입 플레이북이나 `/architect`가 코드로 먼저 정한다.

원칙은 `/just-mode`가 읽고 답변에서 인용하는 규칙 하나짜리 스킬이다. 사용자가 직접 부르지 않는다. 대신 "동작 증명 적용해. 실제 출력을 보여 줘"처럼 이름으로 방향을 잡는다. 원칙은 `/` 메뉴에 나오지 않는다(`user-invocable: false`). 원칙 목록은 [`just-mode`](../just-mode/SKILL.md)의 원칙 절에 있다.

## 잘못된 실행 고치기

| 증상 | 고치는 법 |
|---|---|
| 몇 턴 뒤 모드가 적용되지 않음 | 한 메시지에만 붙여 시작했다. 항상 적용 규칙에 넣거나, 작업마다 `/just-mode`로 시작한다. |
| 질문이 지난 작업의 다음 단계로 처리됨 | "새 작업"이라고 하거나, 이 턴에는 모드가 필요 없다고 말한다. |
| 새 모델 선택이 효과가 없음 | `/just-setup`이 쓴 `~/.config/skills/models.json`을 확인한다. 이미 돌고 있는 서브에이전트에는 적용되지 않으므로 새로 띄운다. |
| 실행 비용이 예상보다 큼 | 설정하기 절의 비용 문단을 본다. |
| 스킬이 저절로 호출되지 않음 | 사용자의 말만으로 호출되는 스킬은 `/just-setup`뿐이다. 나머지는 사용자가 치거나 `/just-mode`가 돌릴 때 호출되고, `/just-mode`가 모든 스킬을 돌리지는 않는다. |
| 병렬 에이전트가 서로 덮어씀 | 에이전트마다 별도 워크트리를 준다. |
| 밤새 돌았는데 움직이기만 하고 끝난 게 없음 | 주기적으로 다시 깨우기에는 시간이 아니라 통과하거나 실패할 수 있는 확인 조건이 필요하다. [`references/prompting.md`](references/prompting.md)의 자리 비우기 전 절을 본다. |
| 빌드의 CI 통과만으로 성공했다고 답함 | 실제 명령, 흐름, 저장된 값, 프로파일을 요구한다. 동작 증명 원칙이다. |

방향이 어긋난 실행을 한 줄로 바로잡는 말은 [`references/prompting.md`](references/prompting.md)에 있다. 따라 쓸 만한 프롬프트는 [`references/recipes.md`](references/recipes.md)에 있다.

## just를 내 것으로 만들기

- [`/automate-me`](../automate-me/SKILL.md)는 사용자 자신의 기록으로 `/just-mode`와 함께 쓸 개인 모드 스킬 초안을 만든다.
- 세션 뒤 [`/reflect`](../reflect/SKILL.md)는 그 세션의 교훈을 사용자가 승인하는 스킬 수정으로 바꾼다.
- `/just-mode <작업 흐름> 스킬 써 줘`는 스킬 작성·수정 플레이북을 돌린다. 평가 플레이북은 스킬 변경을 블라인드로 테스트한다.
- 이상하게 동작하는 스킬은 문제가 난 기능 작업 안에서가 아니라 별도 PR로 고친다.

## 답변

답부터 쓴다. 예시 프롬프트는 코드 블록으로 최대 하나만 주고, 맞는 것이 있으면 [`references/recipes.md`](references/recipes.md)에서 가져와 고친 뒤 그 파일을 링크한다. 사용자가 전체 지도를 요청하지 않았다면 짧게 쓴다.
