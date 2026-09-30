# 스킬 안내

이 폴더는 저장소 작업용 AI 스킬의 원본이다. Codex, Claude, Antigravity가 같은 내용을 쓴다. 스킬을 읽거나 고치는 AI는 이 문서를 먼저 읽는다.

## 만든 이유

| 문제 | 드러난 곳 |
|---|---|
| 같은 요청에도 AI가 매번 다른 구조, 문체, 용어로 문서를 쓴다 | 2026-09-29 문서 점검에서 한 문서 안에 `-다`와 `-합니다`가 섞였고 상태 표시가 문서마다 다섯 가지였다 |
| 결정이 바뀌어도 앞선 문서에 반영되지 않는다 | 구현 언어, 명령 표기, 폴더 구조가 문서마다 달랐고 어느 문서가 정본인지 알 수 없었다 |
| AI가 말하지 않은 것을 알아서 정하고 없는 사실을 채운다 | 설계만 있는 기능이 현재형으로 쓰였다 |
| 문서마다 수정을 요청하는 데 시간과 토큰이 든다 | 방향만 주는 이전 글쓰기 스킬은 결과가 매번 달랐다 |

목표는 포매터처럼 좁은 규칙이다. 고정 템플릿, 칸마다 채우는 기준, 없을 때 빼는 규칙, 문체 규칙, 저장 전 검사를 정해 누가 써도 같은 문서가 나오게 한다.

## 문서가 쓰이는 곳

| 독자 | 쓰는 문서 | 요구 |
|---|---|---|
| 오픈소스 사용자와 기여자 | README, docs, CONTRIBUTING | 설치와 사용이 첫 화면에 있고 사실만 있다 |
| 채용 담당 CTO | README, 설계 문서, 실험, 결정 기록 | 판단의 근거와 깊이가 보인다 |
| 랜딩 페이지, 링크드인, 블로그 독자 | 데모 GIF, 홍보 영상, 비공개 기록에서 다시 쓴 글 | 가짜 없이 정갈하다 |
| AI 에이전트 | AGENTS.md, llms.txt, docs | 기계가 읽기 쉬운 고정 형식이다 |
| 작성자 본인 | 비공개 판단 기록 | 문제, 생각, 설계, 검증, 변경의 흐름과 놓친 것이 남는다 |

- 공개 문서는 한국어로 먼저 쓰고 영어 번역은 나중에 한다
- 오픈소스 라이선스는 MIT다. 판매는 클라우드 서비스와 학습한 모델 API를 분리해서 한다

## 공통 원칙

모든 스킬이 따른다. 새 스킬도 같다.

| 원칙 | 이유 |
|---|---|
| 작업 중인 저장소 안에 같은 역할의 규칙이 있으면 그것을 따르고, 없으면 스킬이 다른 규칙보다 우선한다 | 다른 프로젝트의 관례를 덮어쓰지 않고, 관례가 없을 때는 결과를 고정하기 위해서다 |
| 스킬에 특정 프로젝트, 제품, 사람 이름을 넣지 않는다. D2, GitHub, Rust 같은 표준 도구 이름은 쓴다 | 다른 저장소에도 그대로 쓰기 위해서다 |
| 공통 규칙은 공통 스킬 하나가 정본이고, 종류별이나 언어별 스킬은 맡긴 부분(템플릿, 그 종류에만 있는 규칙)만 정한다 | 같은 규칙이 두 곳에서 어긋나지 않기 위해서다 |
| 긴 설명 대신 AI가 골라 쓰는 표와 목록으로 쓴다 | 토큰을 줄이고 판단 여지를 없애기 위해서다 |
| 채울 사실이 없으면 저장하지 않고 빠진 칸을 보고한다 | 지어낸 내용을 막기 위해서다 |
| 개발자가 실제로 쓰는 말을 쓴다. 책 번역어를 쓰지 않는다 | 읽는 사람이 바로 알아듣게 하기 위해서다 |
| 커밋, 작성자, 문서 어디에도 AI 작성 흔적을 남기지 않는다. 작성자는 사용자 git 설정이다 | 공개 저장소의 기록을 사용자 것으로 두기 위해서다 |
| 승인 전 스킬은 이름 끝에 `-demo`를 붙이고 기존 스킬을 대체하지 않는다 | 검토 전 규칙이 실제 작업에 섞이지 않기 위해서다 |
| 스킬을 고치면 다른 스킬과 우선순위 문구, 용어, 서로 참조하는 규칙, 금지 항목을 교차 확인한다 | 스킬끼리 모순되지 않기 위해서다 |
| 모든 스킬은 아래 작성 형식을 따른다 | 형식이 같아야 AI가 어느 스킬이든 같은 방식으로 읽고, 검사 스크립트로 확인할 수 있다 |

## 작성 형식

frontmatter:

```text
---
name: {이름}
description: "{언제} 사용. {담긴 것 명사구, 쉼표로}"
---
```

- description: 사용자가 쓸 법한 낱말(README, 커밋, PR, 리팩터링 등) 포함, o200k 60토큰 이내. 다른 스킬 이름과 `함께 적용` 금지
- description은 항상 올라가는 카탈로그라 짧게, 본문은 쓸 때만 올라가므로 규칙을 빠짐없이

`# 제목` 바로 아래 머리 목록(이 순서, 이 글자):

```text
- 저장소 안에 같은 역할의 규칙이 있으면 그것 우선. 없으면 이 스킬이 다른 규칙보다 우선
- 기반: {기반 스킬} 먼저 적용. 이 스킬 범위: {맡는 것}
- 필요할 때만 읽기: {조건} → {스킬}; {조건} → {스킬}
```

- 기반 스킬이 없는 스킬(repo-docs, code-style, git-*, folder-naming, design-tokens, skill-sync): 둘째 줄 `- 범위: {맡는 것}`
- 조건부 참조가 없으면 셋째 줄 생략
- 본문에서 다른 스킬 규칙을 가리킬 때: `({스킬} {절 이름})` 출처 표시만. 읽어야 하는 참조는 셋째 줄 조건으로
- 목록 항목, 표 칸: 명사구 끝. 동작은 동작 명사(추가, 삭제, 저장), 금지는 `금지`, 필수는 `필수`
- 쓰지 않는 끝: `-다`, `-한다`, `-함`, `-음`(없음, 다음 같은 명사 제외), `-임`, `-됨`, `-ㅁ`형
- 템플릿 코드 블록과 백틱 안 예시는 문서에 그대로 나올 글자라 문체 규칙 밖
- 형식 검사: `python3 skill-sync/scripts/skill_check.py .`, 출력 `total 0`까지 수정
- 실행 코드: 본문 대신 `scripts/*.py`. 본문에는 실행 한 줄 `python3 <이 스킬 폴더>/scripts/{이름}.py`와 쓰는 순간 필요한 규칙만. Python 3.9 이상 표준 라이브러리 우선, 외부 도구는 그 도구의 명령이나 공식 패키지
- 스크립트 함수: code-style 비용 주석

## 스킬 연결

스킬은 기반 줄로만 항상 함께 올라가고, 나머지는 조건이 참일 때만 올라간다.

| 스킬 | 기반 | 필요할 때만 읽기 |
|---|---|---|
| repo-docs | 없음 | 코드 주석 → code-style; 커밋, PR, 이슈, 브랜치 → git-* 스킬; 그림 파일, 대체 글 → repo-docs-figures |
| repo-docs-readme | repo-docs | 대표 그림, 흐름 그림, 측정 결과 차트, 데모 GIF 제작 → repo-docs-figures; README 갱신 뒤 `llms.txt` 재생성 → repo-docs-llms |
| repo-docs-design | repo-docs | 코드에 들어간 인터페이스 문서 → repo-docs-spec; 맥락, 구성 요소, 순서, 상태 그림 → repo-docs-figures |
| repo-docs-spec | repo-docs | 데이터 그림 → repo-docs-figures |
| repo-docs-decision | repo-docs | 비공개 판단 기록에서 옮길 때 → repo-docs-journal |
| repo-docs-experiment | repo-docs | 결과 차트 → repo-docs-figures |
| repo-docs-note | repo-docs | 없음 |
| repo-docs-figures | repo-docs | 없음 |
| repo-docs-root | repo-docs | 단계 판정, 필요한 도구 문장 → repo-docs-readme; CONTRIBUTING 커밋과 PR 절 → git-branch, git-commit, git-pull-request |
| repo-docs-llms | repo-docs | 없음 |
| repo-docs-journal | repo-docs | 판단이 공개 설계를 정했을 때 → repo-docs-decision |
| repo-docs-promo | repo-docs | 없음 |
| git-commit | 없음 | 없음 |
| git-branch | 없음 | 커밋 메시지, PR 제목, squash 메시지 → git-commit; PR 본문 → git-pull-request |
| git-issue | 없음 | build, docs 제목의 끝말, 영역 라벨의 scope 단어 → git-commit |
| git-pull-request | 없음 | 없음 |
| code-style | 없음 | 리팩터링 기법 선택 → code-refactoring |
| code-refactoring | code-style | 없음 |
| code-style-rust, code-style-kotlin, code-style-python | code-style | 없음 |
| code-style-javascript | code-style | CSS 문자열, 인라인 style, SVG 속성 값 작성 → design-tokens |
| code-style-css | code-style, design-tokens | 없음 |
| design-tokens | 없음 | CSS 작성 → code-style-css; JavaScript 작성 → code-style-javascript; 문서 그림 색 → repo-docs-figures |
| folder-naming | 없음 | 없음 |
| skill-sync | 없음 | 원본 저장소 커밋 → git-commit |

## 크기

2026-10-01 기준. o200k는 GPT, Codex 토크나이저 정확값, Claude 구는 공개된 Claude 구 토크나이저 근사치다. 카탈로그 줄은 `{이름}: {description}` 한 줄이며 모든 대화에 항상 올라간다. `scripts/` 파일은 읽지 않고 실행만 하므로 표에 넣지 않는다.

| 스킬 | 바이트 | o200k | Claude 구 | 카탈로그 줄 o200k |
|---|---|---|---|---|
| repo-docs | 16734 | 4782 | 7393 | 65 |
| repo-docs-readme | 10752 | 2956 | 4518 | 65 |
| repo-docs-design | 9004 | 2593 | 4110 | 57 |
| repo-docs-spec | 6949 | 2179 | 3302 | 46 |
| repo-docs-decision | 5379 | 1503 | 2523 | 65 |
| repo-docs-experiment | 11580 | 3703 | 5349 | 63 |
| repo-docs-note | 2809 | 841 | 1270 | 59 |
| repo-docs-figures | 8276 | 2601 | 3704 | 65 |
| repo-docs-root | 6710 | 2000 | 3009 | 58 |
| repo-docs-llms | 2993 | 881 | 1296 | 60 |
| repo-docs-journal | 6204 | 1830 | 2978 | 60 |
| repo-docs-promo | 4042 | 1239 | 1801 | 57 |
| git-commit | 5118 | 1496 | 2275 | 36 |
| git-branch | 4636 | 1355 | 2084 | 60 |
| git-issue | 5209 | 1581 | 2526 | 53 |
| git-pull-request | 4205 | 1230 | 2013 | 51 |
| code-style | 16123 | 4587 | 7181 | 52 |
| code-refactoring | 12020 | 2947 | 4832 | 42 |
| code-style-rust | 7764 | 2234 | 3135 | 55 |
| code-style-kotlin | 6553 | 1894 | 2716 | 64 |
| code-style-python | 5534 | 1631 | 2349 | 58 |
| code-style-javascript | 6262 | 1820 | 2551 | 63 |
| code-style-css | 7409 | 2149 | 3106 | 58 |
| design-tokens | 7084 | 2197 | 3123 | 62 |
| folder-naming | 3093 | 923 | 1390 | 60 |
| skill-sync | 2541 | 727 | 1118 | 43 |
| 합계 | 184983 | 53879 | 81652 | 1477 |

요청별로 실제 올라가는 양과 형식 통일 전후 비교는 [실험 결과](experiments/skill-format-unification/report.md)에 있다.

## 스킬 목록

### 저장소 문서

| 스킬 | 맡는 것 | 만든 이유 |
|---|---|---|
| repo-docs | 원칙, 문서 목록(위치, 독자, 답할 질문, 만드는 조건, 맡는 스킬), 언어, 절 구성, 한국어와 영어 문체, 용어, 사실 상태, 자리표시, 기계 검사와 독자 검사 | 모든 문서의 공통 규칙을 한 곳에 두고, 형식보다 독자 질문을 기준으로 삼기 위해서다 |
| repo-docs-readme | 영어 README와 한국어 번역본의 단계별 필수 절, 절 이름 목록, 번역 규칙 | 처음 온 사람이 무엇인지, 어떻게 쓰이는지, 지금 어떤 상태인지 바로 알게 하기 위해서다 |
| repo-docs-design | 새 기능을 넣는 자리, `docs/README.md`, 아키텍처(코드 지도, 불변 조건), RFC형 기능 설계(미해결 질문 포함), 용어 | 설계 단계에도 정한 것과 미정인 것을 구분해 기여자가 읽을 수 있게 하기 위해서다 |
| repo-docs-spec | 프로토콜, 명령, 화면, 데이터, 설정, 오류 문서 | 찾아보는 문서를 표 형식으로 고정하기 위해서다 |
| repo-docs-decision | 공개 결정 기록 | 고른 이유와 버린 선택지를 공개로 남기기 위해서다 |
| repo-docs-experiment | 사전 등록 설계, 데이터, 스크립트, 보고서 | 설계 값의 근거를 논문 수준으로 남기기 위해서다 |
| repo-docs-note | 짧은 개발 기록(insight, reference) | 알게 된 것을 흩어지지 않게 남기기 위해서다 |
| repo-docs-figures | D2, Vega-Lite, VHS 원본과 변환 스크립트, 공통 색표 | 그림을 코드로 만들어 다시 만들 수 있게 하기 위해서다 |
| repo-docs-root | AGENTS.md, CLAUDE.md 링크, CHANGELOG, CONTRIBUTING, SECURITY | 루트 파일의 위치와 형식을 고정하기 위해서다 |
| repo-docs-llms | llms.txt, 선택으로 llms-full.txt | AI가 문서를 한 번에 찾게 하기 위해서다 |
| repo-docs-journal | 비공개 판단 기록, 서사, 원칙 | 판단 흐름과 놓친 것을 블로그 재료로 남기기 위해서다 |
| repo-docs-promo | 홍보 영상 촬영 준비물 | 사용자가 녹화할 때 합성 데이터 데모와 규격을 바로 쓰게 하기 위해서다 |

### Git과 GitHub

| 스킬 | 맡는 것 | 만든 이유 |
|---|---|---|
| git-commit | 커밋 형식 `type(scope): 한글 설명` | 영어 부담 없이 일관된 기록을 남기기 위해서다 |
| git-branch | 브랜치 이름과 이슈 단위 작업 | 브랜치와 이슈를 한 줄로 잇기 위해서다 |
| git-issue | 이슈 종류와 템플릿, 상태 관리 | 설계, 구현, 버그, 실험 상태를 문서가 아니라 이슈로 관리하기 위해서다 |
| git-pull-request | PR 종류, 본문, 문서 동반, 검토 | 계약을 먼저 합의하고 구현을 믿을 수 있게 하기 위해서다 |

### 코드와 폴더

| 스킬 | 맡는 것 | 만든 이유 |
|---|---|---|
| code-style | 언어 공통 원칙, 수치 기준, 이름, 조건식, 선언 순서, 에러와 로그, 주석, 비용 주석, 테스트 | 언어가 달라도 같은 기준으로 코드를 보기 위해서다 |
| code-refactoring | 문제 신호별 해결 기법, 『리팩터링 2판』 기법 목록 | 리팩터링 기법을 고를 때만 불러 평소 코드 작업의 토큰을 줄이기 위해서다 |
| code-style-rust, code-style-kotlin, code-style-python, code-style-javascript, code-style-css | 언어별로 공통 스킬이 맡긴 부분 | 언어 고유 규칙만 따로 두기 위해서다 |
| design-tokens | 화면 값 토큰 정본, 이름, 세 층, 다크 모드, 하드코딩 금지, 생성·검사 스크립트 | 색과 크기를 코드마다 다르게 적어 화면 톤이 흩어지는 것을 막기 위해서다 |
| folder-naming | 저장소 폴더 구조와 이름 | 폴더마다 구현 언어 경계가 드러나게 하기 위해서다 |

### 스킬 관리

| 스킬 | 맡는 것 | 만든 이유 |
|---|---|---|
| skill-sync | 형식 검사, 세 도구 설치, Claude 계정 zip | 스킬을 고칠 때마다 같은 검사와 설치를 한 번에 하기 위해서다 |

## 주요 결정

| 결정 | 이유 | 버린 선택지 |
|---|---|---|
| 스킬 원본은 프로젝트 저장소와 분리한 별도 저장소에 둔다 | 여러 프로젝트가 같은 스킬을 쓰고, 프로젝트의 비공개 폴더와 섞이지 않는다 | 프로젝트 `docs/archive/skills` 복사본 |
| `AGENTS.md` 명령 절은 CI나 검사 스크립트의 명령만 쓰고, 없으면 절을 뺀다 | 설계 단계에는 README 개발 절이 없어 명령을 가져올 곳이 없다. 없는 명령을 지어내지 않는다 | 설계 단계에도 README 개발 절 추가 |
| `LICENSE`는 라이선스를 정한 저장소에만 만든다 | 미정이거나 비공개 배포인 저장소에서 AI가 라이선스를 임의로 고르거나 문서를 못 만드는 교착을 막는다 | 모든 저장소에 필수 |
| 스킬 이름은 `repo-docs-*`, `git-*` | GitHub에 배포되는 문서라는 목적이 이름에 드러나고, 저장소 밖 마크다운에서 켜지지 않는다 | `markdown-*`: 형식 이름이라 켜지는 범위가 넓고 마크다운이 아닌 산출물(D2, JSON, `.tape`, llms.txt)과 맞지 않는다 |
| 방향만 주는 글쓰기 스킬 대신 고정 템플릿 | 결과가 매번 같아야 수정 요청이 줄어든다 | 이전 `writing-*-demo` 스킬 |
| 설계 문서 목록을 닫는다 | 새 기능마다 파일이 생기면 정본이 흩어진다. 새 내용은 정해진 파일의 행이나 절로 넣는다 | 기능마다 설계 파일 |
| 설계 문서에는 현재 설계만, 상태는 GitHub 이슈 | 문서가 항상 최신이고 사실만 남는다 | 문서 안 진행 상태와 이력 |
| README 단계는 설계, 개발 중, 실행 가능, 배포 | 단계마다 들어갈 절이 정해져야 없는 기능을 쓰지 않는다 | 자유 구성 |
| 아직 없는 기능은 `로드맵`이라고 쓴다 | 한 단어로 통일해야 상태가 헷갈리지 않는다 | `계획`, `예정`, `향후`, `TODO` |
| 문체는 위치로 정한다. README와 루트 대외 문서는 합쇼, docs와 기록은 평서, 제목·목록·표는 명사형, 요청은 `-세요` | 번역된 주요 오픈소스 문서 7곳이 모두 합쇼였고, 국내 기술 문서(K8s 개념 문서, NHN)는 평어였다. 한 파일 안 혼용이 가장 큰 문제였다 | 모든 문서 평서, 해요체(토스, 당근), `-십시오` |
| 가짜 대신 표시가 붙은 자리표시 | 공개 문서와 포트폴리오에 가짜 수치나 화면이 있으면 신뢰를 잃는다 | 가짜 화면 이미지, 예상 수치 |
| 구조도는 D2, 손그림 모드 금지 | mermaid는 보기 좋지 않고 연구 저장소 느낌이 나지 않는다. 손그림은 문서 톤과 맞지 않는다 | mermaid, D2 손그림 |
| 차트는 Vega-Lite와 vl-convert | 브라우저 없이 같은 SVG를 다시 만들 수 있다 | matplotlib, Observable Framework(배포 명령이 폐기됨) |
| D2와 Vega-Lite가 공통 색표를 쓴다 | 흰 바탕에 핵심 색 두 개로 그림 톤을 맞춘다 | 도구별 기본 색 |
| README와 docs 데모 GIF는 VHS | 스크립트로 같은 영상을 다시 만들고 CI에서도 돌릴 수 있다 | 화면 녹화 앱 |
| 홍보 영상은 사용자가 화면 녹화 앱(Recordly)으로 직접 찍는다 | AI가 조작해 보니 녹화 앱 조작 창이 AI 화면 캡처에 잡히지 않고, 커서 기반 자동 확대가 키보드 화면에서 거의 일어나지 않았으며, 매번 같은 영상이 나오지 않았다 | AI가 녹화 앱 조작 |
| 변환 스크립트는 스킬 폴더 안에 둔다 | 저장소마다 변환 스크립트가 흩어지고 달라지는 것을 막는다 | 저장소별 스크립트 |
| 실행 코드는 SKILL.md 본문 대신 `scripts/` 파일로 둔다 | AI가 코드 본문을 읽지 않고 실행만 해서 문서 작업마다 토큰이 준다. Codex, Claude, Antigravity 모두 스킬 폴더의 `scripts/`를 지원한다 | 본문 코드 블록(읽을 때마다 토큰 소비), 저장소 안 스크립트 |
| README 그림은 대표 그림, 결과 차트, 구성 그림 하나씩까지 | 첫 화면을 짧게 두고 나머지는 docs로 보낸다 | 그림 여러 장 |
| README 수치는 실험 보고서 링크와 함께만 | 근거 없는 성능 주장을 막는다 | 링크 없는 수치 |
| 배지, 굵게, HTML 금지 | 주요 오픈소스(codex, ollama)도 배지 없이 설치 명령을 첫 화면에 둔다. 서식이 단순해야 검사할 수 있다 | 배지 줄 |
| AGENTS.md가 원본, CLAUDE.md는 심볼릭 링크 | 여러 에이전트가 한 지침을 읽는다. 조사한 오픈소스 18곳 중 15곳이 AGENTS.md를 둔다 | 에이전트별 지침 파일 |
| llms.txt를 둔다 | AI가 문서 목록과 원문을 한 번에 찾는다. 손으로 쓰지 않고 스크립트로 만든다 | 없음 |
| CONTRIBUTING, SECURITY는 `.github/`, CHANGELOG는 루트 | GitHub는 커뮤니티 파일을 `.github`, 루트, `docs` 순서로 찾는다. CHANGELOG는 그 대상이 아니다 | 모두 루트 |
| 공개 결정 기록은 비공개 기록을 다시 쓴다 | 비공개 기록의 가정, 추정, 놓친 것은 공개하지 않고 확인된 사실만 옮긴다 | 비공개 기록 복사, 링크 |
| 공개 문서에서 `docs/archive` 링크 금지 | 비공개 폴더는 git에서 제외되어 링크가 깨지고 내용이 새어 나간다 | 없음 |
| 실험은 사전 등록과 원자료 보존 | 결과를 본 뒤 가설을 바꾸는 것을 막고 재현을 보장한다 | 결과만 남기는 보고서 |
| 스킬끼리는 기반 줄과 조건부 줄로만 부른다 | description의 `함께 적용`은 필요 없는 스킬까지 항상 불러왔다. 조건부 로드로 요청 14개의 로드 합이 13.8% 줄었다 | description에 다른 스킬 이름, 본문 곳곳의 읽기 지시 |
| 스킬 카탈로그 문서를 따로 두지 않는다 | 이름과 description이 이미 모든 대화에 올라가는 카탈로그다(o200k 1248). 문서 종류 라우팅은 repo-docs 문서 목록 표가, 관리용 목록은 이 문서가 맡아 실행 중 추가 토큰이 없다 | 카탈로그 스킬(요청마다 추가 로드, 두 곳 관리) |
| 문서 목록 표는 repo-docs에 둔다 | 인터페이스 문서를 쓸 때 repo-docs-design을 함께 부를 필요가 없어 명령 문서 작성 로드가 46.1% 줄었다 | repo-docs-design 안 문서 목록 |
| 리팩터링 기법은 code-refactoring으로 분리 | 기법 목록이 code-style의 절반 가까이를 차지했고 리팩터링 기법을 고를 때만 필요하다 | code-style 한 파일 |
| 디자인 토큰은 CSS 스킬과 나눈 별도 스킬이고 CSS 스킬의 기반이다 | 토큰은 CSS뿐 아니라 JavaScript가 만드는 SVG, 인라인 style에도 걸린다. CSS를 쓸 때는 항상 필요해 기반 줄로 함께 올린다 | code-style-css 안의 절 |
| 하드코딩 금지는 검사 스크립트로 강제한다 | 규칙 문장만으로는 AI가 한 번만 쓰는 값을 직접 적는다. hex 색, 단위 붙은 길이와 시간, 글꼴 이름, breakpoint 밖 `@media` 숫자를 `check_tokens`가 찾아 `total 0`까지 고치게 한다 | 리뷰에서 눈으로 확인 |
| 스킬 문체는 명사구 끝 | 끝말은 토큰 차이가 거의 없고, 설명 문장을 `{대상}: {값}` 명사구로 줄일 때 토큰이 줄었다. 끝이 하나면 검사할 수 있다 | `-다` 문장, `-함`, `-음` 혼용 |

## 검증

- 같은 가상 사실로 에이전트 둘이 각자 문서를 만들고 비교했다. 2026-09-29 검증에서 `docs/README.md`와 실험 목록은 같았고 README는 네 줄만 달랐다. 2026-09-30 검증에서 `docs/README.md`와 결정 목록은 같았고, 그림 식별자, AGENTS.md 규칙, 결정 문장처럼 달라진 곳은 규칙을 좁혀 고쳤다
- 처음 보는 에이전트 하나가 스킬 사이 모순, 문체 위반, 스크립트 오류를 따로 검사했고 찾은 18건을 고쳤다
- `check_doc`(repo-docs)는 Python 표준 라이브러리로 문체, 금지어, 서식, 비공개 경로를 검사한다. 합쇼 파일과 평서 파일을 경로로 나눠 검사한다
- `render_figures`(repo-docs-figures)는 두 번 실행해도 결과가 같은 바이트인지 확인했다
- 세 스크립트를 본문에서 `scripts/`로 옮길 때 옮기기 전과 같은 결과를 확인했다. `check_doc`은 Markdown 251개와 반례 20개, `gen_llms`는 정상 저장소 두 곳의 출력 바이트, `render_figures`는 D2와 Vega-Lite SVG 바이트로 비교했다. VHS 변환은 설치 환경이 없어 비교하지 못했다
- `gen_llms`는 비공개 폴더 직접 링크, 심볼릭 링크, 상위 경로, 대소문자 변형, 코드 블록 안 행을 넣은 반례에서 두 파일을 쓰지 않고 중단한다
- 2026-09-30 형식 통일 실험: 누락 대조 26건 중 소실 6건 포함 24건 수정, 기반 줄을 따른 스킬 선택 30/30, 에이전트 둘의 줄 차이 14.4%에서 5.8%로 감소. 가설, 기준, 원자료, 판정은 [실험 결과](experiments/skill-format-unification/report.md)
- 그림 견본(D2 테마 비교, 차트 6종, VHS 데모)을 만들어 사용자가 보고 골랐다

## 배포와 수정

| 대상 | 위치 |
|---|---|
| 원본 | 이 저장소 |
| Codex | `~/.codex/skills/` |
| Antigravity | `~/.gemini/config/skills/` |
| Claude Code | `~/.claude/skills/` |
| Claude 계정(웹, 데스크톱, 원격 세션) | `dist/claude/{스킬}.zip`을 설정의 스킬 메뉴에서 올림 |

- 세 도구 모두 같은 폴더 구조(`SKILL.md`, `scripts/`, `agents/`)를 그대로 읽는다
- 설치 스크립트: `skill-sync/scripts/install.py`. SKILL.md가 있는 폴더만 설치하고, 도구 폴더가 없는 도구는 건너뛴다
- 설치 스크립트가 설치한 스킬만 관리(도구 폴더의 `.repo-skills.json`). 원본에서 빠진 스킬과 `--remove`로 지정한 스킬은 지우지 않고 `~/.skill-trash/`로 이동

1. 이 저장소에서 스킬을 고친다
2. 관련 스킬을 모두 읽고 공통 원칙 표의 교차 확인을 한다
3. 작성 형식 검사를 `total 0`까지 돌린다. 스킬을 이어 부르는 줄을 바꾸면 스킬 연결 표를, 크기가 바뀌면 크기 표를 고친다
4. 스킬마다 `agents/openai.yaml`의 이름과 설명을 SKILL.md와 맞춘다
5. 새 스킬이면 이 문서의 스킬 목록에, 결정을 바꾸면 주요 결정에 행을 고친다
6. `python3 skill-sync/scripts/install.py`로 설치된 도구 폴더를 동기화하고 바뀐 스킬의 `dist/claude/*.zip`을 만든다. `--dry-run`은 바꿀 내용만 출력한다
7. Claude 계정에는 출력 마지막 줄의 zip을 올린다. 업로드 명령과 API가 없어 설정 화면에서 올린다. 저장 카드는 SKILL.md 하나만 저장하므로 쓰지 않는다
8. 커밋한다

이 순서는 skill-sync 스킬에도 있어 AI가 스킬을 고치면 같은 순서로 검사와 설치를 한다.

## 정리할 옛 스킬

| 옛 스킬 | 도구 | 대체한 스킬 |
|---|---|---|
| commit | Claude | git-commit |
| branch | Claude | git-branch |
| issue-demo | Claude | git-issue |
| pull-request-demo | Claude | git-pull-request |
| writing-demo, writing-note-demo, writing-intro-demo | Claude | repo-docs, repo-docs-note, repo-docs-readme |
| writing-design-demo, writing-experiment-demo, writing-journal-demo | Claude | repo-docs-design, repo-docs-experiment, repo-docs-journal |
| refactor, refactoring-2e | Codex | code-refactoring |
| naming, quality | Codex | code-style, folder-naming |
| writing | Codex | repo-docs |
| diagram | Codex | repo-docs-figures |
| demo-video | Codex | repo-docs-promo |

- Codex와 Claude Code 쪽: 2026-09-30 `install.py --remove`로 `~/.skill-trash/`에 이동했다
- Claude 계정 쪽: 2026-09-30 설정의 스킬 메뉴에서 삭제했다

## 이력

| 날짜 | 한 일 |
|---|---|
| 2026-09-29 | code-style, 언어별 스킬, folder-naming, commit, branch 정리. 글쓰기 스킬을 `-demo`로 만든 뒤 문서 점검에서 한계를 확인 |
| 2026-09-29 | repo-docs 계열과 git-* 스킬을 고정 템플릿으로 새로 만들고 에이전트 둘로 검증 |
| 2026-09-30 | 위치별 문체, 그림 도구와 색표, 자리표시, 루트 파일, llms.txt, 공개 결정 기록, 홍보 촬영 준비 추가 |
| 2026-09-30 | 22개 스킬 작성 형식 통일, 조건부 로드, 문서 목록 표 이동, code-refactoring 분리, 실험 기록 추가 |
| 2026-09-30 | code-style 비용 주석 추가, check_doc Python 전환, 실행 코드 세 개를 `scripts/`로 분리, gen_llms 비공개 경로 차단, install.py로 세 도구 동일 배포 |
| 2026-09-30 | 스킬 원본을 별도 저장소로 분리, skill-sync 추가, `LICENSE`를 라이선스를 정한 저장소에만 만들도록 변경, repo-docs-experiment 설명을 60토큰 안으로 축소 |
| 2026-09-30 | `AGENTS.md` 명령 절의 출처를 CI와 검사 스크립트로 고정, 명령이 없으면 절 삭제. 옛 스킬 정리 완료 |
| 2026-10-01 | code-style-javascript, code-style-css, design-tokens 추가. 토큰 생성(`build_tokens`)과 하드코딩 검사(`check_tokens`) 스크립트 추가 |
