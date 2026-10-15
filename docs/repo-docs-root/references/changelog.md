# CHANGELOG.md

````text
# Changelog

Notable changes by version. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [Semantic Versioning](https://semver.org/).

## {버전} - {YYYY-MM-DD}

### {분류}

- {변경} ([#{번호}]({PR URL}))
````

커밋 type → 분류:

- `feat` 새 기능 → `Added`
- `feat` 기존 동작 변경, `perf` → `Changed`
- 사용 중단 표시 → `Deprecated`
- 기능 제거 → `Removed`
- `fix` → `Fixed`
- 보안 수정 → `Security`. `fix`여도 `Fixed`보다 우선

- 분류 순서: 위 표 순서. 항목이 없는 분류는 제목까지 제외
- 릴리스 PR에서 지난 태그 뒤 머지된 PR마다 항목 하나. 글자는 PR 제목의 설명을 영어로 옮긴 문장. 사용자 동작·호환·보안 영향이 없는 내부 변경만 제외, 커밋 type만으로 제외 금지
- 호환이 깨지는 변경: 항목 앞에 `Breaking:`
- 버전: 최신이 위
