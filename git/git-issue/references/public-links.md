# 공개 웹 링크

- 적용: GitHub 이슈·PR 본문·리뷰·댓글의 파일·문서·코드 위치. 저장소 안 문서끼리의 상대 링크는 적용 제외
- 파일·문서 위치: 짧은 경로나 이름을 링크 글자로 쓴 웹 주소. 코드 줄은 `https://github.com/{소유자}/{저장소}/blob/{커밋 SHA}/{경로}#L{시작}-L{끝}`, 계속 바뀌는 문서는 기본 브랜치 주소 사용. 기본 브랜치는 저장소 조회 결과 사용
- 공개되지 않은 로컬·홈·저장소 밖 작업 폴더(worktree의 `{이름}.wt` 등)·미커밋 폴더(`.local` 등): 링크와 경로 표기 금지. 근거의 존재를 밝혀야 할 때는 `비공개 원자료`처럼 존재만 표시하고 공개 가능한 내용만 본문에 요약
- 경로 경계: 절대·홈·Windows 경로와 file URL은 토큰 시작(줄 시작, 공백, 여는 괄호·대괄호·중괄호·따옴표·백틱·`<` 뒤)에서만 비공개 경로 판정. 상대 경로 낱말 중간의 `/`는 제외, `.local` 경로 요소와 토큰 시작의 `../`는 차단 유지. HTML 닫는 태그는 경로 검사 제외
- worktree 경로: 같은 토큰 시작 경계에서 `{이름}.wt/`로 시작하거나 경로 마디 하나가 정확히 `{이름}.wt`인 경로 차단. 이름은 한 글자 이상, 백틱 안·밖과 링크 대상 모두 적용. `a.wt.md`, `docs/x.wtf/a.md`, `foo.wtx/a`처럼 `.wt` 뒤에 마디 이름이 이어지면 이 규칙 적용 제외
- 비공개 저장소 링크: 같은 저장소의 이슈·PR·리뷰·댓글에서만 허용. 다른 저장소에서 참조 금지
- 이슈·PR·댓글을 올리기 전에 아래 스크립트로 검사, 위반 0개 확인 필수

```sh
python3 <이 스킬 폴더>/scripts/public_links.py --repo <게시 대상 저장소 루트> <본문 파일>
python3 <이 스킬 폴더>/scripts/public_links.py --repo <게시 대상 저장소 루트> --fix <본문 파일>
```

- 실행 조건: Python 3.9 이상, 표준 라이브러리, Git, 인증된 GitHub CLI(`gh`). 원격은 `--remote`로 지정, 기본 origin, 공개 여부와 기본 브랜치는 `gh repo view` 조회
- 입력: UTF-8 파일, 생략 또는 `-`이면 표준 입력. 저장소 상대 경로는 게시 대상 저장소 루트 기준
- 출력: 검사 결과는 표준 출력에 줄 번호 포함. `--fix`는 수정한 본문만 표준 출력, 남은 위반은 표준 오류. 원본 파일 덮어쓰기 금지
- 링크 규칙 진단: `relative repository link: replace with a public web link` 또는 `repository path in code text: replace with a public web link`. HEAD에 있는 저장소 파일의 상대 링크·코드 표기는 공개 웹 링크로 변환 대상, 상대 경로 자체는 게시 금지 대상에서 제외
- 게시 금지 규칙 진단: `private path`, `path outside repository`, `unpublished file` 뒤 `do not publish; summarize without its location`. 비공개 위치는 공개 링크 변환 없이 위치를 뺀 내용만 요약 대상. 다른 비공개 저장소는 `private repository: do not publish; summarize without its address`
- 자동 수정: HEAD에 포함된 저장소 파일만 웹 링크로 변환, 줄 번호가 있으면 현재 HEAD SHA 고정. 비공개 경로·다른 비공개 저장소 주소는 원문 유지와 위반 보고만 수행
- 종료 코드: 통과 또는 모든 위반 수정 0, 남은 위반 1, 입력·Git·공개 여부 조회 실패 2. 수정 결과 재검사 후 게시
