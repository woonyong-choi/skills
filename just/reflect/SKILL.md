---
name: reflect
description: 현재 대화 기록에서 오래 남을 교훈을 찾아 기존 스킬의 구체적인 수정으로 연결할 때 쓴다. 검토 서브에이전트 셋을 병렬로 띄운다. 사용자가 reflect라고 말할 때 쓴다.
disable-model-invocation: true
---

# Reflect

현재 대화에서 오래 남을 교훈을 캐내고, 그것을 스킬 수정으로 연결한다.

사용자가 "reflect"라고 말하거나 이 스킬을 부를 때 실행한다. 대화가 사소하거나, 주제에서 벗어났거나, 부모가 제대로 따른 기존 스킬이 이미 다루는 내용이면 건너뛴다. 한 번뿐인 일은 교훈이 아니다.

## 1. 현재 대화 기록 찾기

병렬 분배 전에 이 대화의 대화 기록을 현재 호스트의 대화 기록 위치([호스트 대응표](../just-mode/references/hosts.md))에서 찾는다. 현재 프로젝트의 폴더만 본다. 모든 프로젝트의 대화 기록 폴더를 가로질러 glob하지 않는다. 그러면 작업 공간 경계를 넘어 상관없는 프로젝트의 비공개 대화를 읽게 된다.

```bash
ls -t <transcripts>/*.jsonl <transcripts>/*/*.jsonl <transcripts>/*/subagents/*.jsonl 2>/dev/null | head -10
```

이 명령은 평평한 배치(`<id>.jsonl`), 중첩 배치(`<id>/<id>.jsonl`), 서브에이전트 배치(`<parent>/subagents/<child>.jsonl`)를 모두 다룬다. 호스트가 날짜별 폴더 같은 다른 배치를 쓰면 호스트 대응표의 패턴으로 바꾼다. 후보마다 첫 사용자 메시지를 읽는다. 그 메시지가 이 대화의 첫 사용자 프롬프트와 같은 파일을 고른다. 맞는 파일이 없으면 대신 세션을 간추린 요약을 넘긴다.

## 2. 검토자 셋을 병렬로 띄우기

한 메시지에서 서브에이전트 셋을 동시에 띄운다(호스트 대응표). 읽기 전용 모드로 띄우지 않는다. 검토자는 대화 기록이 가리키는 티켓, 채팅 스레드, 관측 트레이스를 MCP로 찾아봐야 하는데, 읽기 전용 모드는 MCP를 막을 수 있다. 파일 수정 금지는 프롬프트 템플릿이 정한다.

각 검토자와 종합자의 모델은 [역할별 모델](../just-mode/references/models.md)의 역할로 고른다. 지정한 모델이 거부되면 다른 이름을 추측하지 않고 호스트 기본 모델로 진행하고 그 사실을 알린다. 각 서브에이전트의 추론 수준은 일에 맞게 고른다(**just-mode** 스킬의 서브에이전트 절).

| 관점 | 역할 | 프롬프트 템플릿 |
|---|---|---|
| 판단 | `judgment` | `references/judgment-reviewer.md` |
| 도구 | `code` | `references/tooling-reviewer.md` |
| 발산 | `judgment` | `references/divergent-reviewer.md` |

각 템플릿을 그대로 넘기고, 표시된 자리에 대화 기록 경로나 요약을 넣는다. 검토자는 지적을 서브에이전트 응답 본문으로 돌려준다.

## 3. 종합

서브에이전트 하나를 `judgment` 역할로 띄운다. 이것도 읽기 전용 모드로 띄우지 않는다. 종합자가 MCP로 인용을 표본 확인하기 때문이다. `references/synthesizer.md`를 그대로 넘기고, 표시된 자리에 각 검토자의 전체 출력을 넣는다. 종합자는 Accepted / Rejected / Backlog 목록을 돌려준다.

## 4. 구조적 강제 확인

린트 규칙, 스크립트, 메타데이터 플래그, 런타임 검사가 더 확실하게 강제할 Accepted 항목은 Backlog로 옮긴다. **principle-encode-lessons-in-structure** 원칙 스킬을 본다.

## 5. 적용

종합자의 Accepted / Rejected / Backlog 출력 전체를 보여 주고, Accepted 수정을 적용하기 전에 명시적인 승인을 기다린다. 사용자가 일부를 고르고 연결 대상을 바꿀 수도 있다. 스킬 변경은 조직의 앞으로의 모든 에이전트에 영향을 준다. 자동으로 적용하지 않는다.

Backlog 항목은 기다리지 않고 팀의 개발 경험 또는 백로그 트래커에 등록한다. 승인을 기다리는 것은 Accepted 목록뿐이다.

승인된 행마다 Routing을 그대로 따른다.

- 사소한 기존 스킬 수정(한 줄 항목, 다듬은 문장, 낡은 사실 고치기): 부모가 직접 한다.
- 실질적인 기존 스킬 수정(새 절, 새 패턴 표, 약 10줄 넘음): `skill-creator` 스킬이 있으면 넘겨서 초안 / 테스트 / 반복 루프를 돌린다. 없으면 부모가 SKILL.md 형식(frontmatter `name`·`description`)을 지켜 직접 고친다.
- `tune description: <skill path>`(스킬은 있지만 호출돼야 할 때 호출되지 않음): `skill-creator`가 있으면 넘겨서 description 최적화 루프를 돌린다. 없으면 부모가 description을 직접 고친다.
- `new skill via skill-creator: <kebab-name>`: 생성을 `skill-creator`에 넘긴다. 없으면 SKILL.md 형식(frontmatter `name`·`description`)을 직접 작성한다. 모양을 즉석에서 지어내지 않는다.

환경에 SKILL.md 검증기가 있으면 완료를 선언하기 전에 건드린 모든 스킬에 돌린다.

## 6. 사용자에게 요약

서두 없이 짧은 목록으로 쓴다.

- 적용한 수정: `<skill path>`. 바뀐 내용을 한 줄씩.
- 새로 만든 스킬: `<skill path>`. 한 줄씩(드묾).
- 개발 경험 트래커에 등록한 Backlog: `<issue title>` (`<tags>`). 한 줄씩.
- 버린 것: 기각한 지적마다 한 줄과 종합자가 준 이유.
