# CHANGELOG.md

`CHANGELOG.md`를 쓰거나 갱신하거나 검토할 때 이 틀과 분류 규칙을 쓴다.

````text
# 변경 기록

버전별 주요 변경을 적는다. 형식: [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/). 버전: [유의적 버전](https://semver.org/lang/ko/).

## {버전} - {YYYY-MM-DD}

### {분류}

- {PR 제목의 설명} ([#{번호}]({PR URL}))
````

## 분류

| 커밋 type | 분류 |
|---|---|
| `feat` 새 기능 | `추가` |
| `feat` 기존 동작 변경, `perf` | `변경` |
| 사용 중단 표시 | `사용 중단` |
| 기능 제거 | `제거` |
| `fix` | `수정` |
| 보안 수정 | `보안`. `fix`여도 `수정`보다 먼저다 |

- 분류는 위 표의 순서로 놓는다. 항목이 없는 분류는 제목까지 뺀다.
- 릴리스 PR에서 지난 태그 뒤에 머지된 PR마다 항목 하나를 쓴다. 글자는 PR 제목 `type(scope): 설명`의 설명 부분을 그대로 쓰고 번역하지 않는다. 사용자 동작, 호환, 보안에 영향이 없는 내부 변경만 빼고, 커밋 type만 보고 빼지 않는다.
- 호환이 깨지는 변경은 항목 앞에 `호환 깨짐:`을 붙인다.
- 버전은 최신을 위에 둔다.
- 작업 언어가 영어인 저장소는 제목 `Changelog`, 분류 `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`, 접두 `Breaking:`을 쓴다.
