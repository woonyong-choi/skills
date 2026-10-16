# 노트 만들기

노트 만들기는 사용자가 브라우저나 CLI에서 제목 있는 노트를 저장하고, 끝내지 않은 초안을 취소하고, 저장한 노트를 사용자에게 보이는 두 번째 화면에서 확인하게 한다.

## 하위 기능

- `create-open`은 브라우저 진입점마다 빈 편집기를 연다.
- `create-save`는 제목과 본문을 저장한다.
- `create-cancel`은 끝내지 않은 브라우저 초안을 버린다.
- `create-cli`는 터미널에서 같은 모양의 노트를 만든다.

## 들어가는 방법(사용자 관점)

- 브라우저 도구 막대에서 `New note` 버튼을 고른다.
- 브라우저에서 초점이 편집 가능한 필드 밖에 있을 때 `n`을 누른다.
- 터미널에서 `notes create --title <title> --body <body>`를 실행한다.

## control-notes로 조작하기

전제 조건:

- Notes가 `http://127.0.0.1:4173`에서 정상이다.
- 제목이 `Release checklist`인 노트가 없다.
- `control-notes doctor`가 기대한 URL과 버리는 데이터 폴더를 보고한다.

- **편집기 열기.** `New note`를 고른다. `control-notes browser click --role button --name "New note"`를 실행한다. `Note editor`라는 이름의 폼이 나타나고 초점이 `Title` 입력 상자에 있다.
- **내용 입력.** 제목과 본문을 입력한다. `control-notes browser fill --role textbox --name "Title" --value "Release checklist"`와 `control-notes browser fill --role textbox --name "Body" --value "Tag and publish"`를 실행한다. `Save note` 버튼이 활성화된다.
- **노트 저장.** `Save note`를 고른다. `control-notes browser click --role button --name "Save note"`를 실행한다. `Note saved`라는 이름의 상태가 나타나고 제목 줄이 `Release checklist`다.
- **저장 유지 확인.** 노트 목록으로 돌아가 노트를 다시 연다. `control-notes browser click --role link --name "All notes"`와 `control-notes browser click --role link --name "Release checklist"`를 실행한다. 편집기에 저장한 두 값이 모두 보인다.
- **초안 취소.** 새 노트를 열고 `Discard me`를 입력한 뒤 `Cancel`을 고른다. `control-notes browser click --role button --name "New note"`, `control-notes browser fill --role textbox --name "Title" --value "Discard me"`, `control-notes browser click --role button --name "Cancel"`을 실행한다. 노트 목록이 돌아오고 `Discard me` 링크가 없다.
- **CLI 진입.** 두 번째 노트를 만든다. `control-notes cli -- notes create --title "CLI note" --body "Created from terminal" --format json`을 실행한다. 종료 코드가 `0`이고 stdout에 새 노트 ID와 제목이 들어 있다.
- **증명.** `All notes`에서 저장한 두 노트를 다시 연다. `control-notes browser snapshot --aria --path artifacts/create-note/list.aria.txt`와 `control-notes browser screenshot --path artifacts/create-note/list.png`를 실행한다. 산출물에 `Release checklist`와 `CLI note`가 보인다.

## 주의할 점

- 입력 상자에 초점이 있을 때 `n`을 누르면 새 편집기를 열지 않고 글자를 입력한다.
- 제목은 저장할 때 앞뒤 공백이 잘린다. 초안 입력값이 아니라 그려진 제목을 단언한다.
- 저장 상태 하나만으로는 증명이 부족하다. 목록에서 노트를 다시 연다.
- 픽스처 정리 때 `Release checklist`와 `CLI note`를 지우되, 그 증명 산출물은 남긴다.
