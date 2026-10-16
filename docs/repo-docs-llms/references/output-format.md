# llms.txt 형식

llmstxt.org 형식(2026-09-30 확인)

```text
# {이름}

> {한 줄 소개}

{소개 문단}

## Docs

- [{문서 제목}]({URL}): {내용}

## Optional

- [{문서 제목}]({URL}): {내용}
```

자리 → 원본:

- 이름 → `README.en.md`, 없으면 `README.md`의 `#` 제목
- 한 줄 소개 → 같은 파일의 제목 다음 첫 문단. 언어 전환 줄·링크만 있는 줄(절 이동·배지) 제외
- 소개 문단 → 같은 파일의 한 줄 소개 다음 문단. 없으면 해결하는 문제(`Why`)·문제와 제약 절 첫 문단(repo-docs-readme 틀)
- 문서 → `docs/README.md` 목록 링크 줄 중 `experiments/`, `decisions/` 경로가 아닌 줄. 같은 순서, 제목·설명 원문 그대로
- Optional → `docs/README.md`의 `experiments/`, `decisions/` 경로 줄과 `CHANGELOG.md`(링크 글자는 그 파일의 `#` 제목, 설명 없음)
- URL → `https://raw.githubusercontent.com/{소유자}/{저장소}/{기본 브랜치}/docs/{파일}`. 원문 마크다운 주소. 다른 호스트는 저장소 원문 URL 정책 적용

- `## Docs`, `## Optional`: 영어 제목 고정. `Optional`은 형식이 정한 이름으로 건너뛰어도 되는 문서라는 뜻
