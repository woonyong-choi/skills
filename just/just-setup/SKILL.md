---
name: just-setup
description: "just가 역할마다 쓸 모델과 추론 예산, 자율 실행의 동시 작업 수를 정한다. 현재 호스트(Claude Code, Codex, OpenCode)와 쓸 수 있는 모델을 알아내고, 스킬 기본값보다 우선하는 ~/.config/skills/models.json과 ~/.config/skills/just.json을 쓴다. 역할별 모델, 추론 예산, models.json, 동시 작업 수를 정하거나 바꿀 때 쓴다. '모델 설정 바꿔 줘', '리뷰 모델 바꿔', '추론 수준 올려', /just-setup 같은 요청에 쓴다."
---

# just 설정

`~/.config/skills/models.json`을 써서 just가 역할마다 쓸 모델과 추론 수준을 정하고, `~/.config/skills/just.json`을 써서 자율 실행의 동시 작업 수를 정한다. 모델 파일 형식, 역할의 뜻, 기본값은 [역할별 모델](../just-mode/references/models.md)이 정본이다. 호스트를 알아내는 방법은 [호스트 대응표](../just-mode/references/hosts.md)를 따른다.

## 1. 호스트 알아내기

[호스트 대응표](../just-mode/references/hosts.md)의 "현재 호스트 알아내기"로 지금 호스트가 `claude`(Claude Code), `codex`(Codex), `opencode`(OpenCode) 중 무엇인지 정한다. 이 값이 설정 파일에서 이번에 고칠 열이다. 셋 다 아니면 사용자에게 어느 호스트에서 쓸지 질문한다.

다른 회사 CLI가 있는지도 확인한다. `command -v claude`와 `command -v codex`를 돌려 둘 다 기록한다. `review` 역할에 쓴다.

## 2. 쓸 수 있는 모델 알아내기

확인한 모델만 쓴다. 확인하지 않은 모델 이름을 파일에 쓰지 않는다. 빈 문자열(호스트 기본 모델)은 언제나 쓸 수 있다.

- Claude Code는 별칭 `opus`, `sonnet`, `haiku`를 쓸 수 있다. 사용자가 전체 모델 ID를 주면 그 값도 받는다.
- Codex는 모델 목록을 내는 명령이 없다. `~/.codex/config.toml`의 `model` 값이 있으면 그것을 현재 기본 모델로 본다. 기본값의 `gpt-6.1-sol`, `gpt-6-astra`, `gpt-6-luna`는 `codex exec -m <모델> "ok"`가 성공하면 확인한 것으로 본다. 실패한 모델은 빈 문자열(기본 모델)로 둔다.
- OpenCode는 `opencode models`를 돌려 나온 `<제공자>/<모델>` 목록을 쓴다.
- 다른 회사 CLI는 `claude`가 있으면 `claude:opus`, `claude:sonnet`, `claude:haiku`를 쓸 수 있다. `codex`가 있으면 `codex:`(Codex 기본 모델)와 위 방법으로 확인한 `codex:<모델>`(기본값 `codex:gpt-6.1-sol`)을 쓸 수 있다.

하나도 알아낼 수 없으면 모든 역할을 빈 문자열(호스트 기본 모델)로 두고, 사용자가 모델 이름을 알려 주면 바꿀 수 있다고 알린다.

## 3. 현재 상태 읽기

`~/.config/skills/models.json`이 있으면 읽고, 그 안의 `roles`와 `effort`를 현재 선택으로 본다. 없으면 [역할별 모델](../just-mode/references/models.md)의 기본값에서 시작한다. 파일이 JSON으로 읽히지 않으면 덮어쓰지 않고 사용자에게 알리고 멈춘다.

현재 예산은 `effort`를 기본값(`code` `medium`, `judgment` `high`, `review` `high`, `cheap` `low`)과 비교해 알아낸다. 단계가 다르게 섞여 있으면 "사용자 지정"으로 본다.

## 4. 예산 정하고, 모델 정하고, 확인받기

**(가) 예산을 묻는다.** 자유 입력보다 선택지 질문을 쓴다. 아래 네 선택지를 이 이름 그대로 주고, 현재 예산을 알면 함께 말한다. 설정 파일이 없으면 `large`가 스킬 기본값과 같다고 말한다.

- `unlimited — 최대 추론`
- `large — 기본 추론`
- `medium — 한 단계 낮춤`
- `small — 두 단계 낮춤`

**(나) 예산을 적용한다.** 추론 수준 순서는 `low` < `medium` < `high` < `xhigh` < `max`다. `large`는 역할별 기본값을 그대로 쓴다. `unlimited`는 모든 역할을 `max`로 올린다. `medium`은 기본값에서 한 단계, `small`은 두 단계 내린다. `low`보다 내려가지 않는다. 현재 호스트가 지원하지 않는 수준이면 그보다 낮은 수준 중 가장 가까운 것을 쓴다(예: Codex에는 `max`가 없으므로 `xhigh`).

**(다) 역할마다 모델을 고른다.** 다시 돌릴 때 사용자가 전에 바꾼 값은 그대로 둔다. 처음이면 기본값에서 출발한다.

- `code`는 코드 작성, 기계적 수정, 검증 워커를 맡는다. 빠르고 충분히 강한 모델을 고른다.
- `judgment`는 설계 판단, 가장 어려운 변경, 글쓰기를 맡는다. 쓸 수 있는 가장 강한 모델을 고른다.
- `review`는 교차 검토 패널이다. 목록이고, 항목 하나마다 서브에이전트 하나가 돈다. **서로 다른 회사 모델 두 개 이상**이어야 한다(예: Claude 하나, GPT 하나). 현재 호스트의 모델 하나와 2단계에서 확인한 다른 회사 CLI 항목(`codex:<모델>` 또는 `claude:<모델>`) 하나를 기본으로 넣는다. 다른 회사 CLI가 없으면 "선택 필요"로 표시하고, 그 CLI를 설치하고 로그인해야 교차 검토가 다양해진다고 알린다.
- `cheap`은 읽기 검토, 요약 같은 가벼운 일을 맡는다. 쓸 수 있는 가장 싼 모델을 고른다.

**(라) 보여 주고 확인받는다.** 역할마다 모델과 추론 수준을 표로 보여 준다. 2단계에서 확인하지 못한 모델은 "선택 필요"로 표시한다. 그대로 받을지, 특정 역할을 바꿀지 사용자에게 질문한다. 선택지는 확인한 모델과 빈 문자열(호스트 기본 모델)이다.

## 5. 검증

- 쓰려는 모든 모델 이름이 2단계에서 확인한 목록에 있는지 본다. 빈 문자열은 언제나 통과한다.
- `review` 목록에 서로 다른 회사 모델이 두 개 이상 있는지 본다. `codex:`나 `claude:`로 시작하는 항목은 그 CLI가 2단계에서 확인된 경우에만 통과한다.
- 하나라도 실패하면 쓰지 않고 그 역할을 다시 질문한다.

## 6. 파일 쓰기

`~/.config/skills/models.json`에 병합해서 쓴다. 덮어쓰지 않는다.

- 이번 호스트 열(`roles.<역할>.<호스트>`)과 `effort`만 바꾼다.
- 다른 호스트 열, 모르는 역할, 모르는 최상위 키는 그대로 둔다.
- 폴더가 없으면 `mkdir -p ~/.config/skills`로 만든다.
- 같은 폴더의 임시 파일에 2칸 들여쓰기 JSON으로 쓴 뒤 이름을 바꿔 교체한다. 같은 입력으로 다시 돌리면 같은 파일이 나와야 한다.

병합 예시는 다음과 같다. `HOST`, `ROLES`, `EFFORT`를 고른 값으로 바꾼다.

```sh
python3 - <<'EOF'
import json, os, tempfile
path = os.path.expanduser("~/.config/skills/models.json")
HOST = "claude"
ROLES = {"code": "opus", "judgment": "opus", "review": ["opus", "codex:gpt-6.1-sol"], "cheap": "haiku"}
EFFORT = {"code": "medium", "judgment": "high", "review": "high", "cheap": "low"}
os.makedirs(os.path.dirname(path), exist_ok=True)
data = json.load(open(path)) if os.path.exists(path) else {}
roles = data.setdefault("roles", {})
for role, model in ROLES.items():
    roles.setdefault(role, {})[HOST] = model
data.setdefault("effort", {}).update(EFFORT)
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
with os.fdopen(fd, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
os.replace(tmp, path)
EOF
```

## 7. 동시 작업 수 정하기

[자율 실행](../just-mode/playbooks/autonomous-run.md)이 판의 대기 이슈를 동시에 몇 개까지 처리할지 `~/.config/skills/just.json`의 `parallel`에 둔다. 값은 1 이상의 정수이고, 파일이 없으면 3이다. 실행할 때 `JUST_PARALLEL` 환경 변수가 있으면 파일보다 먼저 쓴다.

```json
{
  "parallel": 3
}
```

1. 파일이 있으면 읽고 현재 값을 보여 준다. 없으면 기본값 3을 보여 준다.
2. 사용자가 값을 말하지 않았으면 그대로 둔다. 동시 작업이 많을수록 사용량 한도에 빨리 닿는다고 한 줄로 알린다.
3. 값을 바꿀 때는 6단계와 같은 방법(병합, 임시 파일 뒤 이름 바꾸기)으로 `parallel` 키만 고친다.

## 8. 확인

파일을 썼다고 알리고, 바뀐 역할과 값을 보여 준다. 설정은 그 뒤에 띄우는 서브에이전트부터 적용되고, 이미 돌고 있는 서브에이전트에는 적용되지 않는다고 말한다. 이 스킬을 다시 돌리면 갱신된다.

## 9. 검증 스킬 제안(선택)

프로젝트에 실제 앱을 조작해 동작을 증명할 방법(`verify-*` 스킬이나 기존 검증 도구)이 있는지 확인한다. 없으면 한 번만 제안한다. "에이전트가 사용자처럼 앱을 조작해 변경이 동작함을 증명할 수 있게 프로젝트 전용 검증 스킬을 만들까요? /create-verification-skill로 만들 수 있습니다." 그렇다고 하면 `/create-verification-skill`을 부른다(Codex는 `$create-verification-skill`). 아니라고 하면 더 권하지 않고 넘어간다.
