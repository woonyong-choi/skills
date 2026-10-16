# 노트 검색

검색은 사용자가 제목이나 본문 내용으로 노트를 찾고, 일치하는 노트를 살펴보고, 일치하는 결과가 없는 것과 검색을 쓸 수 없는 것을 구분하게 한다.

## 하위 기능

- `search-open`은 지원하는 브라우저 진입점마다 검색을 연다.
- `search-match`는 노트 데이터를 바꾸지 않고 제목과 본문 일치를 돌려준다.
- `search-open-result`는 결과를 노트 편집기에서 연다.
- `search-empty`는 일치가 없는 검색어에 빈 결과 화면을 온전히 보여 준다.
- `search-clear`는 검색어를 지우고 최근 노트 화면으로 되돌린다.
- `search-cli`는 터미널에서 같은 일치 노트를 돌려준다.

## 들어가는 방법(사용자 관점)

- 브라우저 도구 막대에서 `Search` 버튼을 고른다.
- 브라우저에서 초점이 편집 가능한 필드 밖에 있을 때 `/`를 누른다.
- 터미널에서 `notes search <query>`를 실행한다.

## control-notes로 조작하기

전제 조건:

- Notes가 `http://127.0.0.1:4173`에서 정상이다.
- 일회용 데이터 폴더에 본문이 `Draft budget`인 `Quarterly plan`이 있다.
- `control-notes doctor`가 기대한 URL과 데이터 폴더를 보고한다.

- **도구 막대 진입.** `Search` 버튼을 고른다. `control-notes browser click --role button --name "Search"`를 실행한다. `Search notes`라는 이름의 대화 상자가 나타나고 초점이 검색 상자에 있다.
- **키보드 진입.** 대화 상자를 닫고 페이지에 초점을 둔 뒤 `/`를 누른다. `control-notes browser press --key "/"`를 실행한다. 같은 대화 상자가 나타나고 페이지에 슬래시(`/`)가 입력되지 않는다.
- **제목 일치.** `quarterly`를 입력한다. `control-notes browser fill --role searchbox --name "Search notes" --value "quarterly"`를 실행한다. `Search results` 목록에 `Quarterly plan`이 있고 `Grocery list`는 없다.
- **본문 일치.** 검색어를 `budget`으로 바꾼다. `control-notes browser fill --role searchbox --name "Search notes" --value "budget"`을 실행한다. 결과 `Quarterly plan`이 본문 일치 발췌와 함께 계속 보인다.
- **결과 열기.** `Quarterly plan`을 고른다. `control-notes browser click --role link --name "Quarterly plan"`을 실행한다. 대화 상자가 닫히고 편집기 제목이 `Quarterly plan`이다.
- **빈 상태.** 검색을 다시 열고 `volcano`를 입력한다. `control-notes browser fill --role searchbox --name "Search notes" --value "volcano"`를 실행한다. 검색이 끝나면 `No matching notes`라는 이름의 상태가 나타난다.
- **검색어 지우기.** `Clear search`를 고른다. `control-notes browser click --role button --name "Clear search"`를 실행한다. 검색 상자가 비고 `Recent notes` 영역이 결과 목록을 대신한다.
- **CLI 일치.** 터미널에서 검색한다. `control-notes cli -- notes search "quarterly" --format json`을 실행한다. 종료 코드가 `0`이고 stdout에 제목이 `Quarterly plan`인 객체 하나가 들어 있다.
- **CLI 결과 없음.** 없는 값을 검색한다. `control-notes cli -- notes search "volcano" --format json`을 실행한다. 종료 코드가 `0`이고 stdout이 `[]`다.
- **증명.** 결과가 채워진 상태를 남긴다. `control-notes browser snapshot --aria --path artifacts/search/results.aria.txt`와 `control-notes browser screenshot --path artifacts/search/results.png`를 실행한다. 두 산출물 모두 Notes, 검색어, `Quarterly plan`을 알아볼 수 있게 보여 준다.

## 주의할 점

- 편집기나 검색 상자에 초점이 있을 때 `/`를 누르면 검색을 열지 않고 글자를 입력한다.
- 결과는 짧은 디바운스 뒤에 갱신된다. 고정된 sleep이 아니라 결과 목록이나 빈 상태를 기다린다.
- 사용자가 `Include archived`를 켜지 않으면 보관한 노트는 빠진다.
- CLI 기본 출력은 사람이 읽는 형식이다. 결과를 안정적으로 단언하려면 `--format json`을 쓴다.
- 결과를 열면 브라우저 상태가 바뀐다. 다른 검색어를 증명하기 전에 검색을 다시 연다.
