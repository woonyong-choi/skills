"""repo-docs 규칙으로 저장소 Markdown 파일 검사.

사용: python3 check_doc.py 파일 [파일 ...] (저장소 루트에서 실행)
"""
import os
import html
import urllib.parse
import re
import sys

FORMAL_FILES = {"README.ko.md"}
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
FENCE_CLOSE = re.compile(r"^ {0,3}(?:`+|~+)[ \t]*$")
NOT_PARAGRAPH = re.compile(r"^(\||- |[0-9]+\. |#|!\[|\[!|---|<)|^[a-z_]+: ")
PARAGRAPH_ENDING = re.compile(r"(해요|십시오| 것이다|게 된다|함|음|임)\.$")
QUOTE_ALERT = re.compile(r"^> \[!(NOTE|WARNING)\]$")
KO_BANNED = re.compile(r"(TBD|TODO|미측정|더미 데이터|목업|강력한|혁신적|쉽게|간단히|간단하게|다양한|효율적|원활|최적의|완벽한|매끄러운|차세대|것 같다|로 보인다|유저|리포지토리|레포지토리|커맨드|컨피그|구동)")
KO_CONNECTIVES = re.compile(r"(^|[.] |^- |^[0-9]+[.] )(또한|이를 통해|이에 따라|결론적으로|요약하면|참고로|기본적으로)")
EN_BANNED = re.compile(r"\b(TBD|TODO|blazing|powerful|seamless(ly)?|simply|easy|easily|revolutionary|next-generation|cutting-edge|world-class|best-in-class)\b", re.IGNORECASE)
EN_CONNECTIVES = re.compile(r"(^|[.] |^- |^[0-9]+[.] )(Additionally|Furthermore|In conclusion|Basically)\b")
EN_CONTRACTION = re.compile(r"\b\w+n't\b|\b(it|that|there|what|here|who)'s\b|\b\w+'(re|ll|ve|d)\b", re.IGNORECASE)
PUNCTUATION = re.compile(r"[?!]$|\.\.\.|…")
HEADING = re.compile(r"^#{1,6} ")
HTML_TAG = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)[^>]*>|<!")
ALLOWED_TAGS = {"picture", "source", "img", "details", "summary"}
README_TAGS = ALLOWED_TAGS | {"p", "h1", "a", "br"}
HANGUL = re.compile(r"[가-힣]")
LETTER = re.compile(r"[A-Za-z가-힣]")
INLINE_CODE = re.compile(r"(`+)(?!`)(.+?)(?<!`)\1(?!`)")
BOLD = re.compile(r"(?<!\\)(?P<mark>\*\*|(?<!\w)__)(?=\S)(?P<body>.+?)(?<=\S)(?P=mark)")
GUIDE_PHRASES = re.compile(
    r"다음과\s+같습니다|살펴보겠습니다|\blet['’]s\b"
    r"|(?:^|[.!?]\s+|^\s*(?:[-*]|\d+\.)\s+|\|\s*)in\s+summary\b(?![./_-]\w)"
    r"|\bit['’]s\s+worth\s+noting\b",
    re.IGNORECASE,
)
EMOJI = re.compile(
    r"[\U0001F1E6-\U0001F1FF\U0001F300-\U0001FAFF]"
    r"|[\u2300-\u27FF\u00A9\u00AE\u3030\u303D\u3297\u3299]\uFE0F"
    r"|[\u231A\u231B\u23E9-\u23EC\u23F0\u23F3\u25FD\u25FE\u2614\u2615"
    r"\u2648-\u2653\u267F\u2693\u26A1\u26AA\u26AB\u26BD\u26BE\u26C4\u26C5"
    r"\u26CE\u26D4\u26EA\u26F2\u26F3\u26F5\u26FA\u26FD\u2705\u270A\u270B"
    r"\u2728\u274C\u274E\u2753-\u2755\u2757\u2795-\u2797\u27B0\u27BF\u2B1B\u2B1C\u2B50\u2B55]"
    r"|[#*0-9]\uFE0F?\u20E3"
)

README_KO = ["작동 방식", "설치", "사용법", "기능", "측정 결과", "상태", "비교", "로드맵", "문서", "개발", "라이선스"]
README_EN = ["How it works", "Installation", "Usage", "Features", "Benchmarks", "Status", "Comparison", "Roadmap", "Documentation", "Development", "License"]
ARCHITECTURE_KO = ["맥락", "코드 지도", "실행 흐름", "불변 조건", "배치", "기술 선택"]
ARCHITECTURE_EN = ["Context", "Code map", "Flows", "Invariants", "Deployment", "Technology choices"]
DESIGN_KO = ["요약", "동기", "예시", "상세 설계", "단점", "대안", "미해결 질문"]
DESIGN_EN = ["Summary", "Motivation", "Examples", "Design", "Drawbacks", "Alternatives", "Unresolved questions"]
DECISION_KO = ["배경", "선택지", "결정", "결과", "다시 볼 조건"]
DECISION_EN = ["Context", "Options", "Decision", "Consequences", "Revisit when"]



# cost: time O(n * d), heap O(n), stack O(1), io 0
# vars: n = 경로 길이, d = 중첩 URL 이스케이프 깊이
# basis: estimate; URL 파싱과 디코딩은 메모리에서만 수행
def _private_path(value: str) -> bool:
    decoded = html.unescape(value)
    while True:
        unquoted = urllib.parse.unquote(decoded)
        if unquoted == decoded:
            break
        decoded = unquoted
    path = urllib.parse.urlsplit(decoded.replace("\\", "/")).path
    parts = [part.casefold() for part in path.split("/") if part not in ("", ".")]
    return ".local" in parts or "archive" in parts

def _private_links(raw: str) -> bool:
    links = re.findall(r"!?\[[^\]]*\]\(<?([^\s)>]+)", raw)
    links += re.findall(r"^\s*\[[^\]]+\]:\s*<?([^\s>]+)", raw)
    links += re.findall(r"https?://[^\s<>\"']+", raw)
    for match in re.finditer(r"\b(?:href|src|srcset)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))", raw, re.IGNORECASE):
        value = next(group for group in match.groups() if group is not None)
        links.extend(part.strip().split()[0] for part in value.split(',') if part.strip())
    return any(_private_path(value) for value in links)


# cost: time O(1), heap O(1), stack O(1), alloc 0
# basis: estimate
def section_lists(name: str) -> list[list[str]]:
    if name in ("README.md", "README.ko.md"):
        return [README_KO, README_EN]
    if name == "docs/architecture.md":
        return [ARCHITECTURE_KO, ARCHITECTURE_EN]
    if name.startswith("docs/design/"):
        return [DESIGN_KO, DESIGN_EN]
    if re.match(r"docs/decisions/\d{4}-\d{2}-\d{2}-", name):
        return [DECISION_KO, DECISION_EN]
    return []


# cost: time O(s), heap O(s), stack O(1), alloc ≈ s
# vars: s = 절 수
# basis: estimate
def section_indexes(headings: list[str], lists: list[list[str]]) -> list[int]:
    indexes = []
    for heading in headings:
        index = next((names.index(heading) for names in lists if heading in names), -1)
        indexes.append(index)
    return indexes


# cost: time O(c), heap O(s), stack O(1), io 1
# vars: c = 파일 글자 수, s = 절 수
# basis: estimate
def level_two_headings(path: str) -> list[str]:
    headings = []
    in_fence = False
    with open(path, encoding="utf-8") as file:
        for raw in file:
            if FENCE.match(raw):
                in_fence = not in_fence
            elif not in_fence and raw.startswith("## "):
                headings.append(raw[3:].strip())
    return headings


# cost: time O(s), heap O(s), stack O(1), io 2
# vars: s = 절 수
# basis: estimate
def structure_errors(name: str, path: str) -> list[str]:
    lists = section_lists(name)
    if not lists:
        return []
    errors = []
    indexes = [index for index in section_indexes(level_two_headings(path), lists) if index >= 0]
    if indexes != sorted(indexes) or len(indexes) != len(set(indexes)):
        errors.append("절 순서")
    pair = {"README.md": "README.ko.md", "README.ko.md": "README.md"}.get(name)
    if name == "README.ko.md" and os.path.exists(pair):
        mine = section_indexes(level_two_headings(path), lists)
        theirs = section_indexes(level_two_headings(pair), lists)
        if mine != theirs:
            errors.append("README.md와 절 대응 불일치")
    return errors


# cost: time O(c), heap O(1), stack O(1), io 1
# vars: c = 파일 글자 수
# basis: estimate
def is_english(path: str) -> bool:
    text = open(path, encoding="utf-8").read()
    letters = len(LETTER.findall(text))
    return letters > 0 and len(HANGUL.findall(text)) / letters < 0.2


# cost: time O(k), heap O(1), stack O(1), alloc 0
# vars: k = 칸 글자 수
# basis: estimate
def has_bad_cell_ending(cell: str) -> bool:
    return (
        (cell.endswith("니다") and not cell.endswith("아니다"))
        or cell.endswith(("해요", "세요", "십시오"))
        or (cell.endswith("함") and not cell.endswith(("포함", "결함")))
        or (cell.endswith("음") and not cell.endswith(("없음", "다음", "처음", "마음")))
        or cell.endswith((" 것이다", "게 된다"))
    )


# cost: time O(w), heap O(w), stack O(1), alloc ≈ 6 + 2k
# vars: w = 줄 글자 수, k = 표 칸 수
# basis: estimate
def korean_errors(text: str, is_formal: bool) -> list[str]:
    errors = []
    if not NOT_PARAGRAPH.match(text):
        if is_formal and text.endswith("다.") and not text.endswith("니다."):
            errors.append("문체(합쇼)")
        if not is_formal and ((text.endswith("니다.") and not text.endswith("아니다.")) or text.endswith("세요.")):
            errors.append("문체(평서)")
        if PARAGRAPH_ENDING.search(text):
            errors.append("문체")
    elif text.startswith("|"):
        errors += ["문체" for cell in text.split("|") if has_bad_cell_ending(re.sub(r"[ .]+$", "", cell))]
    errors += ["쓰지 않는 말"] if KO_BANNED.search(text) else []
    errors += ["연결어"] if KO_CONNECTIVES.search(text) else []
    return errors


# cost: time O(w), heap O(w), stack O(1), alloc ≈ 3
# vars: w = 줄 글자 수
# basis: estimate
def english_errors(text: str) -> list[str]:
    errors = []
    errors += ["쓰지 않는 말"] if EN_BANNED.search(text) else []
    errors += ["연결어"] if EN_CONNECTIVES.search(text) else []
    errors += ["축약형"] if EN_CONTRACTION.search(text) else []
    return errors


# cost: time O(w), heap O(w), stack O(1), alloc ≈ 8
# vars: w = 줄 글자 수
# basis: estimate
def prose_errors(raw: str, is_formal: bool, english: bool, previous_quote: str, tags_allowed: set[str]) -> list[str]:
    errors = []
    line = re.sub(r"`[^`]*`", "", raw)
    text = re.sub(r"^> ", "", line, count=1)
    text = re.sub(r" +$", "", text, count=1)
    text = re.sub(r"\(\[[^\]]*\]\([^)]*\)\)\.$", ".", text, count=1)
    if re.search(r"[ \t]$", raw):
        errors.append("줄 끝 공백")
    errors += english_errors(text) if english else korean_errors(text, is_formal)
    tags = [match for match in HTML_TAG.finditer(line)]
    checks = [
        (re.search(r"[{}]", line), "자리표시자"),
        (any(match.group(0) == "<!" or match.group(2).lower() not in tags_allowed for match in tags), "HTML"),
        ("![](" in line, "대체 글 없음"),
        (raw.startswith("> ") and not QUOTE_ALERT.match(raw) and not QUOTE_ALERT.match(previous_quote), "인용 블록"),
        (PUNCTUATION.search(text), "문장부호"),
    ]
    return errors + [message for matched, message in checks if matched]


# cost: time O(w²), heap O(w), stack O(1), alloc O(w)
# vars: w = 줄 글자 수
# basis: estimate, 닫히지 않은 코드·링크 정규식의 재탐색 상한
def _style_text(raw: str, previous_quote: str) -> str:
    if raw.lstrip().startswith(">") and not QUOTE_ALERT.match(previous_quote):
        return ""
    text = INLINE_CODE.sub("", raw)
    if re.match(r"^ {0,3}\[[^\]]+\]:", text):
        return ""
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"!?\[([^\]]*)\]\[[^\]]*\]", r"\1", text)
    text = re.sub(r"<[^>]*>|https?://\S+", "", text)
    return text


# cost: time O(w²), heap O(w), stack O(1), alloc O(w)
# vars: w = 줄 글자 수
# basis: estimate, 닫히지 않은 강조 정규식의 재탐색 상한
def _style_errors(text: str) -> list[str]:
    errors = []
    for cell in text.split("|"):
        left, separator, right = cell.partition("—")
        if separator and LETTER.search(left) and LETTER.search(right):
            errors.append("줄표 문장 연결")
            break
    if EMOJI.search(text):
        errors.append("이모지")
    if GUIDE_PHRASES.search(BOLD.sub(r"\g<body>", text)):
        errors.append("안내 말")
    if BOLD.search(text):
        errors.append("굵게")
    return errors


# cost: time O(w), heap O(w), stack O(1), alloc O(w)
# vars: w = 줄 글자 수
# basis: estimate
def _visible_length(text: str) -> int:
    text = re.sub(r"^\s*(?:#{1,6}\s+|(?:[-+*]|\d+\.)\s+)", "", text)
    return len(re.sub(r"[\s*_#|>\[\]]", "", text))


# cost: time O(w), heap O(w), stack O(1), alloc O(w)
# vars: w = 줄 글자 수
# basis: estimate
def _without_comments(raw: str, in_comment: bool) -> tuple[str, bool]:
    parts = []
    start = 0
    while start < len(raw):
        marker = "-->" if in_comment else "<!--"
        end = raw.find(marker, start)
        if not in_comment:
            parts.append(raw[start:] if end < 0 else raw[start:end])
        if end < 0:
            break
        parts.append(" ")
        start = end + len(marker)
        in_comment = not in_comment
    return "".join(parts), in_comment


# cost: time O(Σw²), heap O(c), stack O(1), io O(1) + e
# vars: c = 파일 글자 수, w = 줄별 글자 수, e = 오류 수
# basis: estimate, 줄마다 Markdown 표식 정규식 재탐색 가능
def check(path: str) -> int:
    name = re.sub(r"^\./", "", path)
    is_private = name.lower().startswith((".local/", "docs/archive/"))
    is_formal = name in FORMAL_FILES
    english = is_english(path)
    count = number = fence_length = previous_level = 0
    fence_marker = ""
    in_fence = in_comment = is_blank = False
    previous_quote = ""
    with open(path, encoding="utf-8") as file:
        for number, raw in enumerate(file, 1):
            raw = raw.rstrip("\n")
            errors = []
            if not is_private and _private_links(raw):
                errors.append("비공개 경로")
            style_raw = raw
            if not in_fence:
                style_raw, in_comment = _without_comments(raw, in_comment)
            fence = FENCE.match(style_raw)
            if fence:
                previous_quote = ""
                if not in_fence:
                    fence_marker = fence.group(1)[0]
                    fence_length, in_fence = len(fence.group(1)), True
                    errors += ["코드 블록 언어 없음"] if raw.strip() == fence.group(1) else []
                    errors += ["mermaid"] if raw.startswith("```mermaid") else []
                elif fence.group(1)[0] == fence_marker and len(fence.group(1)) >= fence_length and FENCE_CLOSE.match(raw):
                    in_fence = False
                is_blank = False
            elif not in_fence and raw == "":
                errors += ["빈 줄 연속"] if is_blank else []
                is_blank = True
                previous_quote = ""
            elif not in_fence:
                is_blank = False
                errors += prose_errors(raw, is_formal, english, previous_quote, README_TAGS if name in ("README.md", "README.ko.md") else ALLOWED_TAGS)
                text = _style_text(style_raw, previous_quote)
                errors += _style_errors(text)
                previous_quote = raw
                if HEADING.match(raw):
                    level = len(raw.split()[0])
                    errors += ["제목 단계"] if previous_level and level > previous_level + 1 else []
                    previous_level = level
            for message in errors:
                print(f"{name}:{number}: {message}")
            count += len(errors)
    if in_fence:
        print(f"{name}:{number}: 코드 블록 닫힘 없음")
        count += 1
    for message in structure_errors(name, path):
        print(f"{name}: {message}")
        count += 1
    return count


# cost: time O(Σw²), heap O(c), stack O(1), io O(f + e)
# vars: c = 가장 큰 파일 글자 수, w = 줄별 글자 수, f = 파일 수, e = 오류 수
# basis: estimate, 파일마다 줄 검사와 문서 구조 검사
def main(paths: list[str]) -> int:
    if not paths:
        print("usage: check_doc.py FILE [FILE ...]", file=sys.stderr)
        return 2
    return 1 if sum(check(path) for path in paths) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
