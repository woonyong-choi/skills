// 포트폴리오 내용 틀. career.typ는 그대로 두고 자리 글만 바꾼다. 사례 블록은 PLAN의 사례 수만큼 반복.
#import "career.typ": *

#let profile = (
  name: "{이름}",
  title: "{지원 직무}",
  stack: "{기술} / {기술}",
  email: "{이메일}",
  phone: "{전화}",
  github-label: "{GitHub 표시}",
  github-url: "{GitHub 주소}",
  website-label: "{웹사이트 표시}",
  website-url: "{웹사이트 주소}",
)

#show: portfolio-page.with(profile: profile, thesis: [{지원 직무에 맞는 한 문장}])

#section-title("핵심 사례")
#index-row("01", "{사례}", [{보여 주는 것}], [{결과 또는 검증}], first: true)

#pagebreak()
#case-heading("01", "{사례}", "{회사 또는 팀}", "{역할}", "{YYYY.MM} - {YYYY.MM}", "{기술} / {기술}", [{한 문장 결론}])
#case-section("개요 및 역할", [#bullet[{맥락, 목표, 본인 범위}]])
#case-section("문제 정의 및 기술적 제약", [#bullet[{문제와 완료 조건, 제약}]])
#case-section("기술적 의사결정 및 아키텍처", [
  #bullet[{대안, 트레이드오프, 선택 이유}]
  #diagram("figures/{사례}-architecture.png", [{그림이 보여 주는 결론}])
])
#case-section("구현 및 해결 과정", [
  #step("1", [{단계}], [{구현 순서 설명, ~요 문체}])
])
#impact("성과 및 배운 점", [#bullet[{조건과 범위가 있는 결과, 남은 위험과 후속}]])
