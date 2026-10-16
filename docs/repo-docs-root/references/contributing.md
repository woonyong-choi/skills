# .github/CONTRIBUTING.md

````text
# 기여 안내

{기여 방법 한 문장}

## 시작 전에

{이슈 생성 조건}

## 개발 환경

{필요한 도구}

```sh
{받기 명령}
{빌드 명령}
```

## 검사

PR을 열기 전에 아래 검사가 모두 통과해야 한다.

```sh
{테스트 명령}
{린트 명령}
{포맷 검사 명령}
```

## 커밋과 PR

{브랜치·커밋 형식과 예}
{이슈 연결과 닫기 조건}

## 문서

{동작·계약·설정 변경 때 함께 고칠 문서}
````

절 → 규칙:

- 시작 전에 → 이슈 생성·연결은 git-issue 기준. 이슈 틀 링크는 실제 디렉터리가 있을 때만
- 개발 환경 → 필요한 도구 문장: repo-docs-readme 설치 절
- 커밋과 PR → git-branch, git-commit, git-pull-request의 형식과 예 복사
- 문서 → `docs/README.md`가 있을 때만
- 영어 작업 언어 저장소 절 이름: `Contributing`, `Before you start`, `Development environment`, `Checks`, `Commits and pull requests`, `Documentation`
