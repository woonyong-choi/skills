# VHS

아래 값은 실행 형식을 보여 주는 예시이며 그대로 사용할 의무 없음. 글꼴·색·크기는 저장소 디자인 기준으로 결정. 길이·용량은 게시 환경 제한을 확인해 결정. 재생 속도는 실제로 재생하며 글을 다 읽을 수 있는지 확인해 결정

```text
Output docs/assets/{이름}.gif
Set Shell "bash"
Set FontFamily "D2Coding"
Set FontSize 18
Set Width 1200
Set Height 600
Set Theme "Catppuccin Mocha"
Set Padding 24
Set Margin 30
Set BorderRadius 12
Set WindowBar Colorful
Set TypingSpeed 60ms
Hide
Type "export PS1='$ ' && {준비 명령} && clear"
Enter
Show
Type "{명령}"
Enter
Sleep {초}s
```

- 준비 명령(빌드, 합성 데이터 준비): `Hide`와 `Show` 사이
- 사용자 이름, 홈 경로, 키, 실제 사용자 데이터의 화면 노출 금지
- VHS 화면·대체 글에도 repo-docs 자리표시 적용
- 실행 위치: 저장소 루트. `Output`은 저장소 루트 기준 경로
