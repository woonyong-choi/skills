# .github/SECURITY.md

````text
# 보안 정책

## 지원 버전

| 버전 | 보안 수정 |
|---|---|
| {확인한 버전 범위} | {지원, 미지원} |

## 취약점 신고

공개 이슈에 취약점을 올리지 않는다. 저장소 Security 탭의 [비공개 취약점 신고](https://github.com/{소유자}/{저장소}/security/advisories/new)를 사용한다. 영향받는 버전, 재현 단계, 예상 영향을 함께 적는다.

## 처리 절차

| 단계 | 기한 |
|---|---|
| 접수 확인 | 신고 후 7일 이내 |
| 영향 평가 | 신고 후 14일 이내 |
| 수정 공개 | 신고 후 90일 이내 |
````

- 지원 버전: 실제 유지보수 정책에서 확인한 범위만
- 기한: 위 값이 기본. 사용자가 다른 값을 정하면 그 값
- 신고 경로: 작성 전 `gh api repos/{소유자}/{저장소}/private-vulnerability-reporting`로 활성 여부 확인. 꺼져 있으면 저장하지 말고 보고(설정 변경은 사용자 결정). 다른 경로·주소 임의 생성 금지
- 영어 작업 언어 저장소 절 이름: `Security policy`, `Supported versions`, `Reporting a vulnerability`, `Response process`
