// 이력서·포트폴리오 공통 양식. 지원 폴더에 그대로 복사하고 수정 금지. 내용은 이력서.typ·포트폴리오.typ에서만 바꾼다.

#let ink = rgb("#1f2328")
#let body-ink = rgb("#2a323d")
#let muted = rgb("#4b5563")
#let faint = rgb("#8a929d")
#let divider = rgb("#e3e6ea")
#let surface = rgb("#f4f6f8")
#let accent = rgb("#2b96ed")
#let fonts = ("Pretendard", "Apple SD Gothic Neo", "NanumGothic", "Noto Sans CJK KR")
#let mono = ("JetBrains Mono", "Menlo") + fonts

#let setup(body) = {
  set page(paper: "a4", margin: (x: 18mm, top: 16mm, bottom: 15mm), footer: context align(right)[
    #text(size: 7.5pt, fill: faint)[#counter(page).display("1")]
  ])
  set text(lang: "ko", size: 9.6pt, fill: body-ink, font: fonts, fallback: true, ligatures: false)
  set par(justify: false, leading: 0.82em, spacing: 0.9em)
  set list(marker: text(fill: accent)[•], indent: 0pt, body-indent: 0.5em, spacing: 0.62em)
  show link: set text(fill: accent)
  show raw.where(block: false): it => box(fill: surface, inset: (x: 2.5pt), outset: (y: 2pt), radius: 2pt)[#text(font: mono, size: 8.6pt)[#it]]
  body
}

#let dot(body) = [#body#text(fill: accent)[.]]

// 구분자는 이 helper만 넣는다. 본문에 가운뎃점을 쓰지 않기 위함
#let joined(parts) = parts.join(text(fill: faint)[#h(0.5em)|#h(0.5em)])

// 공통 그림: ThinkFlow 정지 그림을 figures.py로 찍은 PNG만. 본문 폭, 캡션 한 줄.
#let diagram(path, caption) = block(width: 100%, breakable: false, above: 1em, below: 1.1em)[
  #image(path, width: 100%)
  #v(0.25em)
  #text(size: 7.8pt, fill: faint)[#caption]
]

#let callout(body) = block(width: 100%, fill: surface, stroke: (left: 2.5pt + accent), inset: (x: 10pt, y: 8pt), above: 1em, below: 1em)[
  #text(size: 9pt, fill: muted)[#body]
]

#let code(path, body) = block(width: 100%, fill: surface, radius: 4pt, inset: 9pt, above: 1em, below: 1em)[
  #if path != none [#text(font: mono, size: 7.6pt, fill: accent)[#path] #v(0.3em)]
  #set text(font: mono, size: 8pt)
  #body
]

// 이력서
#let resume-page(profile: (:), photo: none, intro: [], body) = setup({
  grid(columns: if photo == none { (1fr,) } else { (34mm, 1fr) }, column-gutter: 9mm,
    ..if photo == none { () } else { (image(photo, width: 34mm),) },
    [
      #text(size: 20pt, weight: "bold", fill: ink)[#dot[반갑습니다, 저는 #profile.name\입니다]]
      #v(0.5em)
      #text(size: 10.4pt, fill: body-ink)[#intro]
      #v(0.7em)
      #text(size: 8.4pt)[#joined(profile.contacts)]
    ],
  )
  body
})

#let section(title) = block(above: 2.2em, below: 1.2em)[
  #text(size: 17pt, weight: "bold", fill: ink)[#dot(title)]
  #v(-0.3em)
  #line(length: 100%, stroke: 0.6pt + divider)
]

#let labeled(label, body) = grid(columns: (14mm, 1fr), column-gutter: 3mm, row-gutter: 0.9em,
  text(weight: "bold", fill: ink)[#label], body)

// 경력·프로젝트 항목 하나. meta는 (분류, 소속, 링크) 같은 배열, what은 한 문장 소개
#let entry(title, meta: (), period: none, what: [], items: (), stack: none) = block(width: 100%, breakable: false, below: 2em)[
  #grid(columns: (1fr, auto), align: bottom,
    text(size: 11.6pt, weight: "bold", fill: ink)[#title],
    if period != none { text(size: 8.4pt, fill: faint, tracking: 0.04em)[#period] },
  )
  #v(0.25em)
  #text(size: 8.2pt, fill: muted)[#joined(meta)]
  #v(0.5em)
  #what
  #v(0.5em)
  #if items.len() > 0 { labeled([담당], list(..items)) }
  #if stack != none { v(0.4em); labeled([기술], text(fill: muted)[#stack]) }
]

#let compact(label, parts) = block(below: 0.7em)[#labeled(label, joined(parts))]

// 포트폴리오
#let portfolio-page(body) = setup({
  text(size: 20pt, weight: "bold", fill: ink)[#dot[포트폴리오]]
  v(-0.3em)
  line(length: 100%, stroke: 0.6pt + divider)
  body
})

#let case(title, lead) = block(width: 100%, above: 1.6em, below: 1.1em)[
  #text(size: 13.5pt, weight: "bold", fill: ink)[#dot(title)]
  #v(0.5em)
  #text(weight: "bold", fill: ink)[#lead]
]

// 사례 요약 표: (("기간", [..]), ("역할", [..]), ..)
#let facts(rows) = table(columns: (24mm, 1fr), stroke: (x, y) => (bottom: 0.5pt + divider, top: if y == 0 { 0.8pt + divider } else { none }),
  inset: (x: 6pt, y: 5.5pt), fill: (x, y) => if y == 0 { surface },
  text(weight: "bold", fill: ink)[항목], text(weight: "bold", fill: ink)[내용],
  ..rows.map(((k, v)) => (text(weight: "bold", fill: ink)[#k], v)).flatten(),
)

#let part(title) = block(above: 1.6em, below: 0.7em)[#text(size: 11pt, weight: "bold", fill: ink)[#title]]
