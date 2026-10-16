# 역할별 모델

스킬은 모델 이름 대신 역할 이름만 쓴다. 실제 모델은 사용자 설정 파일 `~/.config/skills/models.json`이 정하고, 없으면 아래 기본값을 쓴다. 설정은 `/just-setup`(Codex는 `$just-setup`)이 만든다.

## 역할

- `code`: 기능·리팩터링·버그·성능 코드 작성, 기계적 수정, 검증 작업자
- `judgment`: 설계 판단, 가장 어려운 변경(여러 모듈에 걸친 설계, 까다로운 동시성, 미묘한 알고리즘), 글쓰기
- `review`: 교차 검토 패널. 서로 다른 회사 모델 두 개 이상(예: Claude 하나, GPT 하나)
- `cheap`: 읽기 검토·요약처럼 가벼운 일

## 기본값

| 역할 | Claude Code | Codex | OpenCode |
|---|---|---|---|
| `code` | `sonnet` | 호스트 기본 모델 | 호스트 기본 모델 |
| `judgment` | `opus` | 호스트 기본 모델, 추론 수준 `high` | 호스트 기본 모델 |
| `review` | `opus` + 셸 `codex exec` | 기본 모델 + 셸 `claude -p --model opus` | 설정된 두 제공자, 없으면 셸 `claude -p`·`codex exec` |
| `cheap` | `haiku` | 가장 싼 모델 | 가장 싼 모델 |

## 설정 파일 형식

```json
{
  "roles": {
    "code": {"claude": "sonnet", "codex": "", "opencode": ""},
    "judgment": {"claude": "opus", "codex": "", "opencode": ""},
    "review": {"claude": ["opus", "codex:"], "codex": ["", "claude:opus"], "opencode": []},
    "cheap": {"claude": "haiku", "codex": "", "opencode": ""}
  },
  "effort": {"code": "medium", "judgment": "high", "review": "high", "cheap": "low"}
}
```

- 빈 문자열은 호스트 기본 모델
- `review` 목록의 `codex:<모델>`, `claude:<모델>`은 다른 회사 CLI를 셸로 부른다는 뜻
- `effort`는 추론 수준. Claude Code는 `/effort`, Codex는 `-c model_reasoning_effort=<값>`, OpenCode는 에이전트 설정 `reasoningEffort`

## 고르는 규칙

- 일의 난이도에 따라 추론 수준만 한 단계 올리거나 내림. 모델 계열은 역할이 정한 대로 유지해 교차 검토의 다양성을 지킴
- 지정한 모델이 거부되면 다른 이름을 추측하지 말고 호스트 기본 모델로 진행하고 답변에 한 줄로 알림
