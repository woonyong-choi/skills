// 이력서 내용 틀. career.typ는 그대로 두고 이 파일의 자리 글만 바꾼다. 절·항목 수는 PLAN에 따름.
#import "career.typ": *

#let profile = (
  name: "{이름}",
  title: "{지원 직무}",
  email: "{이메일}",
  phone: "{전화}",
  github-label: "{GitHub 표시}",
  github-url: "{GitHub 주소}",
  website-label: "{웹사이트 표시}",
  website-url: "{웹사이트 주소}",
)

#show: resume-page.with(profile: profile, summary: [{JD에 맞는 소개 한 문장}])

#section([01 PROFILE], [소개])
{직무, 경력 범위, 중심 포지셔닝 두세 개를 2문장으로}

#section([02 HIGHLIGHTS], [주요 성과와 강점])
#outcome([{검증 수치 또는 정성 결과}], [{성격}], [{문제, 본인 행동, 확인 방법, 남은 위험을 한 문장으로}])

#section([03 EXPERIENCE], [경력])
#employer("{회사}", "{직무} | {고용 형태}", "{YYYY.MM} - {YYYY.MM 또는 현재}", tags: ("{기술}",), divider: false)
#project([{프로젝트}], ([{문제와 책임 범위}], [{판단과 구현}], [{확인한 결과와 후속}]))

#section([04 PROJECTS], [주요 프로젝트])
#project([{프로젝트} | {역할} | {기간}], ([{문제, 구조, 구현, 검증}],))

#section([05 DETAILS], [기술과 공개 기여])
#compact([기술], [{사용 근거가 있는 기술}])
#compact([공개 기여], [{프로젝트·릴리스, 기여 종류, 결과}])

#section([06 EDUCATION], [학력과 교육])
#compact([학력], [{학교} / {전공} / {기간}])
#compact([집중 교육], [{과정} / {기수} / {수료 상태}])
