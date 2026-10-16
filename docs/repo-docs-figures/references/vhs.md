# VHS

VHS 녹화 원본을 쓰거나 실행할 때 쓰는 기본 설정이다. 모든 녹화 품질을 맞추려고 저장소 디자인 정책이 있으면 그 값을, 없으면 이 값을 그대로 쓴다.

```text
Output {실행 위치 기준 경로}.gif
Set Shell "bash"
Set FontFamily "JetBrains Mono"
Set FontSize 16
Set Width 960
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

- 준비 명령(폴더 이동, 빌드, 합성 데이터 준비)은 `Hide`와 `Show` 사이에 둔다. 저장소 루트에서 실행한다.
- 출력 줄이 화면 높이를 넘으면 명령을 나눠 `Type`과 `Sleep`을 여러 번 쓴다. 잘린 프레임을 올리지 않는다.
- 사용자 이름, 홈 경로, 키, 실제 사용자 데이터를 화면에 드러내지 않는다. VHS 화면과 대체 글에도 repo-docs 자리표시를 적용한다.
