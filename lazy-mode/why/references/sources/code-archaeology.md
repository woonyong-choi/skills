# 코드 고고학(git과 저장소 안)

## 이 출처에 있는 것

- 커밋 이력(메시지, 날짜, 작성자, diff)
- PR 설명, 리뷰 댓글, 논의 스레드(`gh`로)
- 인라인 코드 주석, TODO, FIXME, 폐기 안내
- 저장소가 관리한다면 ADR(아키텍처 결정 기록)
- 테스트. 이름과 단언에 변경의 계기가 된 엣지 케이스가 담긴 경우가 많다
- 같은 커밋에서 함께 바뀐 관련 파일(동시 변경 신호)
- 저장소 안의 CHANGELOG 항목과 릴리스 노트
- 커밋 메시지와 PR 본문의 이슈·티켓 ID

코드와 직접 묶여 있어 가장 믿을 만하고, 가장 완전한 출처다. 저장소를 거친 모든 것은 여기에 있어야 한다.

## 검색하는 법

출발 커밋 목록을 넓힌다.

```bash
# History through renames
git log --follow --oneline -- <file>

# Pickaxe: commits that added or removed this exact text
git log -S '<exact_string_from_code>' -- <file>

# Or for patterns:
git log -G '<regex>' -- <file>

# Who wrote each line and when
git blame -L <start>,<end> <file>

# One commit's full diff
git show <hash>

# Commits between two points affecting this file
git log <old>..<new> -p -- <file>
```

코드 밖 문서를 찾는다.

```bash
# ADRs often live in docs/adr/ or similar
rg -l -i 'architecture.decision' --glob '*.md'

# TODOs and FIXMEs near the target
rg -n -C2 '(TODO|FIXME|HACK|XXX|NOTE)' <target_file>

# Related tests
rg -l '<symbol>' --glob '*test*'
```
