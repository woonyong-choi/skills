// 이력서 내용 틀. 중괄호 자리와 항목 수만 변경, 근거 없는 칸과 줄은 삭제. 절 순서는 구성 계획에 따름
#import "/career.typ": *

#let profile = (
  name: "{이름}",
  // 전화 없으면 tel 링크 삭제
  contacts: (link("tel:{전화}")[{전화}], link("mailto:{이메일}")[{이메일}], link("{GitHub 주소}")[{GitHub 표시}]),
)

#show: resume-page.with(profile: profile, photo: none, intro: [{직무와 핵심 성과 두세 문장}])

#section[Projects]
#entry([{이름} ({인원}) [{역할}]],
  meta: ([{소속 이름}], link("{저장소}")[GitHub]),
  period: [{기간}],
  what: [{소개}],
  items: ([{고른 사실 줄}], [{고른 사실 줄}]),
  stack: [{기술}, {기술}],
)

#section[Career]
#entry([{소속 이름}], meta: ([{역할 변화}], link("{근거}")[{근거 표시}]), period: [{기간}],
  what: [{요약}],
  items: ([{그 소속 프로젝트의 고른 사실 줄}],),
)

#section[Skills]
#compact([{수준}], ([{기술}], [{기술}]))

#section[Education]
#compact([{교육 또는 학력}], ([{소속 이름}], [{기간}]))
#compact([{기타 종류}], ([{이름}], [{시기}]))
