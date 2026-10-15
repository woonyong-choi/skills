// 이력서 내용 틀. career.typ는 그대로 두고 {} 자리와 항목 수만 바꾼다. 절 순서는 PLAN에 따름.
#import "career.typ": *

#let profile = (
  name: "{이름}",
  contacts: (link("tel:{전화}")[{전화}], link("mailto:{이메일}")[{이메일}], link("{GitHub 주소}")[{GitHub 표시}]),
)

#show: resume-page.with(profile: profile, photo: none, intro: [{직무 맞춤 소개 두세 문장}])

#section[Projects]
#entry([{프로젝트} ({인원}) [{역할}]],
  meta: ([{분류}], [{소속}], link("{저장소}")[GitHub]),
  what: [{무엇을 왜 만들었는지 한 문장}],
  items: ([{행동과 확인한 결과}], [{수치는 전 → 후와 조건}]),
  stack: [{기술}, {기술}],
)

#section[Career]
#entry([{회사}], meta: ([{직무 변화}], link("{근거}")[{근거 표시}]), period: [{YYYY.MM} - {YYYY.MM}],
  what: [{조직과 맡은 범위 한 문장}],
  items: ([{성과와 근거}],),
)

#section[Education]
#compact([{구분}], ([{기관}], [{과정}], [{기간}]))
