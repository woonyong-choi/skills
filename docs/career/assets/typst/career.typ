// 이력서·포트폴리오 공통 양식. 복사만 하고 수정 금지. 내용은 resume.typ·portfolio.typ에서만 바꾼다.

#let ink = luma(7%)
#let body-ink = luma(20%)
#let secondary = luma(38%)
#let muted = luma(53%)
#let hairline = luma(84%)
#let subtle = luma(96.5%)
#let accent = luma(45%)
#let number-ink = luma(75%)
#let fonts = ("Pretendard", "Apple SD Gothic Neo", "NanumGothic", "Noto Sans CJK KR")

#let setup(body, size: 9.15pt, leading: 0.78em, margin: (x: 17mm, top: 12.5mm, bottom: 13mm)) = {
  set page(paper: "a4", margin: margin, footer: context align(right)[
    #text(size: 7.3pt, fill: muted)[#counter(page).display("1")]
  ])
  set text(lang: "ko", size: size, fill: body-ink, font: fonts, fallback: true, ligatures: false)
  set par(justify: false, leading: leading)
  set list(marker: [•], indent: 0.1em, body-indent: 0.48em, spacing: 0.56em)
  show link: set text(fill: body-ink)
  show link: underline.with(stroke: 0.45pt + luma(68%), offset: 1.5pt)
  body
}

#let contact(profile) = [
  #link("mailto:" + profile.email)[#profile.email] | #profile.phone | #link(profile.github-url)[#profile.github-label] | #link(profile.website-url)[#profile.website-label]
]

#let micro(label) = text(size: 7.15pt, weight: "medium", fill: muted, font: ("Menlo",) + fonts, tracking: 0.045em, label)

// 공통 그림: ThinkFlow 정지 SVG를 PNG로 찍은 파일만. 본문 폭, 캡션 한 줄.
#let diagram(path, caption) = [
  #v(0.4em)
  #block(width: 100%, breakable: false)[
    #image(path, width: 100%)
    #v(0.2em)
    #align(center)[#text(size: 7.8pt, fill: muted)[#caption]]
  ]
  #v(0.6em)
]

// 이력서
#let resume-page(profile: (:), summary: [], body) = setup({
  line(length: 100%, stroke: 1.25pt + ink)
  v(0.48em)
  text(size: 22pt, weight: "semibold", fill: ink, tracking: -0.024em)[#profile.name]
  h(0.72em)
  text(size: 10.2pt, weight: "medium", fill: secondary)[#profile.title]
  v(0.24em)
  text(size: 7.95pt, fill: secondary)[#contact(profile)]
  v(0.70em)
  micro([TARGET ROLE / CAREER SUMMARY])
  v(0.22em)
  text(size: 11.35pt, weight: "semibold", fill: ink, tracking: -0.012em)[#summary]
  body
})

#let section(code, title) = [
  #v(1.12em)
  #line(length: 100%, stroke: 0.45pt + hairline)
  #v(0.30em)
  #micro(code)
  #h(0.78em)
  #text(size: 11.45pt, weight: "semibold", fill: ink, tracking: -0.012em)[#title]
  #v(0.48em)
]

#let outcome(value, label, body) = [
  #block(width: 100%, breakable: false)[
    #text(size: 12.4pt, weight: "semibold", fill: ink, tracking: -0.018em)[#value]
    #h(0.70em)
    #text(size: 7.8pt, weight: "semibold", fill: secondary)[#label]
    #parbreak()
    #v(0.10em)
    #text(size: 8.75pt, fill: secondary)[#body]
  ]
  #v(0.52em)
]

#let employer(title, role, period, tags: (), divider: true) = [
  #if divider [
    #line(length: 11mm, stroke: 1.05pt + ink)
    #v(0.30em)
  ]
  #text(weight: "semibold", size: 10.25pt, fill: ink)[#title]
  #h(0.44em)
  #text(size: 8.45pt, weight: "medium", fill: secondary)[| #role]
  #h(1fr)
  #text(size: 7.9pt, weight: "medium", fill: muted)[#period]
  #parbreak()
  #if tags.len() > 0 [
    #v(0.14em)
    #text(size: 7.8pt, weight: "medium", fill: secondary)[#tags.join(" / ")]
    #parbreak()
  ]
  #v(0.34em)
]

#let project(title, items) = [
  #block(width: 100%, breakable: false)[
    #text(size: 8.8pt, weight: "semibold", fill: ink)[#title]
    #v(0.16em)
    #list(..items)
  ]
  #parbreak()
  #v(0.76em)
]

#let compact(label, body) = [
  #text(size: 8.25pt, weight: "semibold", fill: ink)[#label]
  #h(0.48em)
  #text(size: 8.55pt, fill: body-ink)[#body]
  #parbreak()
  #v(0.38em)
]

// 포트폴리오
#let portfolio-page(profile: (:), thesis: [], body) = setup(size: 9.7pt, leading: 0.92em, margin: (x: 18mm, top: 13.5mm, bottom: 13mm), {
  text(size: 7.8pt, weight: "semibold", tracking: 0.08em, fill: accent)[SOFTWARE ENGINEERING PORTFOLIO]
  v(0.46em)
  line(length: 30mm, stroke: 1.05pt + ink)
  v(0.5em)
  text(size: 23pt, weight: "semibold", fill: ink)[#profile.name]
  v(0.12em)
  text(size: 11.1pt, weight: "medium", fill: secondary)[#profile.title]
  v(0.16em)
  text(size: 8.55pt, fill: muted)[#profile.stack]
  v(0.28em)
  text(size: 8.5pt, fill: secondary)[#contact(profile)]
  v(0.76em)
  block(width: 100%, stroke: (left: 2.2pt + accent), inset: (left: 9pt, right: 4pt, y: 3.5pt))[
    #text(size: 10.7pt, weight: "semibold", fill: ink)[#thesis]
  ]
  body
})

#let bullet(body) = [
  #grid(columns: (8pt, 1fr), column-gutter: 2.5pt, align: top, [#text(size: 7.4pt, weight: "semibold", fill: accent)[•]], [#body])
  #v(0.42em)
]

#let section-title(title) = [
  #v(0.84em)
  #text(size: 11.5pt, weight: "semibold", fill: ink)[#title]
  #v(0.2em)
  #line(length: 100%, stroke: 0.45pt + hairline)
  #v(0.48em)
]

#let index-row(num, project, focus, proof, first: false) = [
  #block(width: 100%, stroke: if first { none } else { (top: 0.45pt + hairline) }, inset: (x: 0pt, top: if first { 4pt } else { 7.5pt }, bottom: 7.5pt), breakable: false)[
    #grid(columns: (28pt, 1fr, 108pt), column-gutter: 8pt, align: top,
      [#text(size: 14pt, weight: "medium", fill: number-ink)[#num]],
      [#text(size: 10.4pt, weight: "semibold", fill: ink)[#project] #v(0.18em) #text(size: 8.9pt, fill: secondary)[#focus]],
      [#align(right)[#text(size: 8.25pt, weight: "semibold", fill: secondary)[#proof]]],
    )
  ]
]

#let case-heading(num, project, organization, role, period, tags, headline) = [
  #grid(columns: (auto, 1fr), column-gutter: 10pt, align: bottom,
    [#text(size: 19pt, weight: "medium", fill: number-ink)[#num]],
    [#text(size: 16.5pt, weight: "semibold", fill: ink)[#project]],
  )
  #v(0.28em)
  #line(length: 100%, stroke: 0.5pt + hairline)
  #v(0.48em)
  #text(size: 8.5pt, weight: "medium", fill: secondary)[#organization / #role / #period]
  #v(0.3em)
  #block(width: 100%, fill: subtle, inset: (x: 6pt, y: 3.6pt))[#text(size: 8.2pt, weight: "medium", fill: secondary)[#tags]]
  #v(0.54em)
  #block(width: 100%, stroke: (left: 2.2pt + accent), inset: (left: 9pt, right: 4pt, y: 3.5pt))[
    #text(size: 10.7pt, weight: "semibold", fill: ink)[#headline]
  ]
  #v(0.82em)
]

#let case-section(title, body) = [
  #block(width: 100%)[
    #text(size: 10.35pt, weight: "semibold", fill: ink)[#title]
    #v(0.28em)
    #set text(size: 9.65pt)
    #body
  ]
  #v(0.84em)
]

// 같은 grid 행의 카드는 행 높이를 함께 쓴다.
#let card(title, body) = grid.cell(fill: subtle, stroke: 0.45pt + hairline, inset: (x: 8pt, y: 6.5pt))[
  #text(size: 8.15pt, weight: "semibold", fill: ink)[#title]
  #v(0.15em)
  #text(size: 8.15pt, fill: secondary)[#body]
]

#let step(num, title, body) = [
  #grid(columns: (22pt, 76pt, 1fr), gutter: 7pt, align: left + top,
    [#box(width: 18pt, height: 18pt, fill: subtle, radius: 50%)[#align(center + horizon)[#text(size: 7.4pt, weight: "semibold", fill: accent)[#num]]]],
    [#text(size: 8.15pt, weight: "semibold", fill: ink)[#title]],
    [#text(size: 8.2pt, fill: secondary)[#body]],
  )
  #v(0.38em)
]

#let impact(title, body) = [
  #block(width: 100%, fill: subtle, inset: (x: 9pt, top: 7.5pt, bottom: 8pt))[
    #text(size: 10.15pt, weight: "semibold", fill: ink)[#title]
    #v(0.28em)
    #set text(size: 9.55pt)
    #body
  ]
]
