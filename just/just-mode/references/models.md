# 역할별 모델

스킬은 모델 이름 대신 역할 이름만 쓴다. 실제 모델은 사용자 설정 파일 `~/.config/skills/models.json`이 정하고, 없으면 아래 기본값을 쓴다. 설정은 `/just-setup`(Codex는 `$just-setup`)이 만든다.

## 역할

| 역할 | 맡는 일 |
|---|---|
| `code` | 기능·리팩터링·버그·성능 코드 작성, 기계적 수정, 검증 워커 |
| `judgment` | 설계 판단, 가장 어려운 변경(여러 모듈에 걸친 설계, 까다로운 동시성, 미묘한 알고리즘), 글쓰기 |
| `review` | 교차 검토 패널. 서로 다른 회사 모델 두 개 이상(예: Claude 하나, GPT 하나) |
| `cheap` | 읽기 검토·요약처럼 가벼운 일 |

## 기본값

| 역할 | Claude Code | Codex | OpenCode | 추론 수준 |
|---|---|---|---|---|
| `code` | `opus` | `gpt-6.1-sol` | 호스트 기본 모델 | `medium` |
| `judgment` | `opus` | `gpt-6-astra` | 호스트 기본 모델 | `high` |
| `review` | `opus` + 셸 `codex exec -m gpt-6.1-sol` | `gpt-6.1-sol` + 셸 `claude -p --model opus` | 설정된 두 제공자, 없으면 셸 `claude -p --model opus`·`codex exec -m gpt-6.1-sol` | `high` |
| `cheap` | `haiku` | `gpt-6-luna` | 가장 싼 모델 | `low` |

## 설정 파일 형식

```json
{
  "roles": {
    "code": {"claude": "opus", "codex": "gpt-6.1-sol", "opencode": ""},
    "judgment": {"claude": "opus", "codex": "gpt-6-astra", "opencode": ""},
    "review": {"claude": ["opus", "codex:gpt-6.1-sol"], "codex": ["gpt-6.1-sol", "claude:opus"], "opencode": []},
    "cheap": {"claude": "haiku", "codex": "gpt-6-luna", "opencode": ""}
  },
  "effort": {"code": "medium", "judgment": "high", "review": "high", "cheap": "low"}
}
```

- 빈 문자열은 호스트 기본 모델을 뜻한다.
- `review` 목록의 `codex:<모델>`, `claude:<모델>`은 다른 회사 CLI를 셸로 부른다는 뜻이다. `codex:gpt-6.1-sol`은 `codex exec -m gpt-6.1-sol`, `claude:opus`는 `claude -p --model opus`로 부른다.
- `effort`는 추론 수준이다. Claude Code는 `/effort`, Codex는 `-c model_reasoning_effort=<값>`, OpenCode는 에이전트 설정 `reasoningEffort`로 정한다.

## 고르는 규칙

- 일의 난이도에 따라 추론 수준만 한 단계 올리거나 내린다. 모델 계열은 역할이 정한 대로 유지해 교차 검토의 다양성을 지킨다.
- 지정한 모델이 거부되면 다른 이름을 추측하지 않는다. 그 모델을 낸 회사의 기본 모델로 진행하고 답변에 한 줄로 알린다. 호스트 모델이면 호스트 기본 모델을, 셸로 부른 다른 회사 CLI면 모델 인자 없이(`codex exec`, `claude -p`) 다시 부른다.
- 교차 검토는 거부가 나도 다른 회사 모델을 유지한다. 다른 회사 검토자를 같은 회사 모델로 바꾸지 않는다. 그 회사 CLI 자체를 쓸 수 없으면 그 검토자를 빼고 답변에 적는다.
