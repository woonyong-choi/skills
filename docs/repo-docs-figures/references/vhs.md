# VHS

기본 설정. 저장소 디자인 정책이 있으면 그 값, 없으면 그대로 사용해 모든 녹화의 품질을 같게 유지

```text
Output {실행 위치 기준 경로}.gif
Set Shell "bash"
Set FontFamily "JetBrains Mono"
Set FontSize 16
Set Width 1200
Set Height 640
Set Padding 24
Set TypingSpeed 40ms
Hide
Type "export PS1='$ ' && {준비 명령} && clear"
Enter
Show
Type "{명령}"
Enter
Sleep {출력 마지막 줄까지 읽는 초}s
Screenshot {같은 경로}.png
```

- 준비 명령(폴더 이동, 빌드, 합성 데이터 준비)은 `Hide`와 `Show` 사이. 실행 위치: 저장소 루트
- 출력 줄이 화면 높이를 넘으면 명령을 나눠 여러 `Type`·`Sleep`으로. 잘린 프레임 게시 금지
- 사용자 이름, 홈 경로, 키, 실제 사용자 데이터의 화면 노출 금지. VHS 화면·대체 글에도 repo-docs 자리표시 적용
