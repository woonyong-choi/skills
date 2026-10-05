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

| 자리 | 원본 |
|---|---|
| 이름 | README `#` 제목 |
| 한 줄 소개 | README 제목 다음 첫 문단. 언어 전환 줄 제외 |
| 소개 문단 | 한 줄 소개 다음 문단 |
| 문서 | `docs/README.md` 표의 행 중 `experiments/`, `decisions/`가 아닌 행. 같은 순서 |
| Optional | `docs/README.md` 표의 `experiments/`, `decisions/` 행과 `CHANGELOG.md`(링크 글자는 그 파일의 `#` 제목, 설명 없음) |
| URL | `https://raw.githubusercontent.com/{소유자}/{저장소}/{기본 브랜치}/docs/{파일}`. 원문 마크다운 주소. 다른 호스트는 저장소 원문 URL 정책 적용 |

- `## Docs`, `## Optional`: 영어 제목 고정. `Optional`은 형식이 정한 이름으로 건너뛰어도 되는 문서라는 뜻
