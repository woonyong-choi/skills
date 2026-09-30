"""repo-docs 규칙으로 저장소 Markdown 파일 검사.

사용: python3 check_doc.py 파일 [파일 ...] (저장소 루트에서 실행)
"""
import re
import sys

FORMAL_FILES = {"README.md", "CHANGELOG.md", ".github/CONTRIBUTING.md", ".github/SECURITY.md"}
PRIVATE_PATH = re.compile(r"docs/+(\./)*archive|\]\((\.\.?/)*archive/|^\[[^\]]*\]: *(\.\.?/)*archive/")
FENCE = re.compile(r"^`{3,}")
FENCE_CLOSE = re.compile(r"^`+[ \t]*$")
NOT_PARAGRAPH = re.compile(r"^(\||- |[0-9]+\. |#|!\[|\[!|---)|^[a-z_]+: ")
PARAGRAPH_ENDING = re.compile(r"(해요|십시오| 것이다|게 된다|함|음|임)\.$")
QUOTE_ALERT = re.compile(r"^> \[!(NOTE|WARNING)\]$")
BANNED_WORDS = re.compile(r"(계획|예정|향후|TBD|TODO|미측정|더미 데이터|목업|강력한|혁신적|쉽게|간단히|간단하게|다양한|효율적|원활|최적의|완벽한|매끄러운|차세대|것 같다|로 보인다|유저|리포지토리|레포지토리|커맨드|컨피그|구동)")
CONNECTIVES = re.compile(r"(^|[.] |^- |^[0-9]+[.] )(또한|이를 통해|이에 따라|결론적으로|요약하면|참고로|기본적으로)")
PUNCTUATION = re.compile(r"[?!]$|\.\.\.|…")
HEADING = re.compile(r"^#{1,6} ")


def has_bad_cell_ending(cell: str) -> bool:
    return (
        (cell.endswith("니다") and not cell.endswith("아니다"))
        or cell.endswith(("해요", "세요", "십시오"))
        or (cell.endswith("함") and not cell.endswith(("포함", "결함")))
        or (cell.endswith("음") and not cell.endswith(("없음", "다음")))
        or cell.endswith((" 것이다", "게 된다"))
    )


# cost: time O(w), heap O(w), stack O(1), alloc ≈ 6 + 2k
# vars: w = 줄 글자 수, k = 표 칸 수
# basis: estimate
def prose_errors(raw: str, is_formal: bool, previous_quote: str) -> list[str]:
    errors = []
    line = re.sub(r"`[^`]*`", "", raw)
    text = re.sub(r"^> ", "", line, count=1)
    text = re.sub(r" +$", "", text, count=1)
    text = re.sub(r"\(\[[^\]]*\]\([^)]*\)\)\.$", ".", text, count=1)
    if re.search(r"[ \t]$", raw):
        errors.append("줄 끝 공백")
    if not NOT_PARAGRAPH.match(text):
        if is_formal and text.endswith("다.") and not text.endswith("니다."):
            errors.append("문체(합쇼)")
        if not is_formal and ((text.endswith("니다.") and not text.endswith("아니다.")) or text.endswith("세요.")):
            errors.append("문체(평서)")
        if PARAGRAPH_ENDING.search(text):
            errors.append("문체")
    else:
        errors += ["문체" for cell in text.split("|") if has_bad_cell_ending(re.sub(r"[ .]+$", "", cell))]
    checks = [
        (re.search(r"[{}]", line), "자리표시자"),
        (re.search(r"<[a-zA-Z/!][^>]*>", line), "HTML"),
        ("**" in line or "__" in line, "굵게"),
        ("![](" in line, "대체 글 없음"),
        (raw.startswith("> ") and not QUOTE_ALERT.match(raw) and not QUOTE_ALERT.match(previous_quote), "인용 블록"),
        (BANNED_WORDS.search(line), "쓰지 않는 말"),
        (CONNECTIVES.search(line), "연결어"),
        (PUNCTUATION.search(line), "문장부호"),
    ]
    return errors + [message for matched, message in checks if matched]


# cost: time O(c), heap O(w), stack O(1), io 1 + e
# vars: c = 파일 글자 수, w = 가장 긴 줄 글자 수, e = 오류 수
# basis: estimate
def check(path: str) -> int:
    name = re.sub(r"^\./", "", path)
    is_private = name.lower().startswith("docs/archive/")
    is_formal = name in FORMAL_FILES
    count = number = fence_length = previous_level = 0
    in_fence = is_blank = False
    previous_quote = ""
    with open(path, encoding="utf-8") as file:
        for number, raw in enumerate(file, 1):
            raw = raw.rstrip("\n")
            errors = []
            if not is_private and PRIVATE_PATH.search(raw.lower()):
                errors.append("비공개 경로")
            fence = FENCE.match(raw)
            if fence:
                if not in_fence:
                    fence_length, in_fence = len(fence.group()), True
                    errors += ["코드 블록 언어 없음"] if raw == "```" else []
                    errors += ["mermaid"] if raw.startswith("```mermaid") else []
                elif len(fence.group()) >= fence_length and FENCE_CLOSE.match(raw):
                    in_fence = False
                is_blank = False
            elif not in_fence and raw == "":
                errors += ["빈 줄 연속"] if is_blank else []
                is_blank = True
            elif not in_fence:
                is_blank = False
                errors += prose_errors(raw, is_formal, previous_quote)
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
    return count


# cost: time O(Σc), heap O(w), stack O(1), io f + e
# vars: c = 파일별 글자 수, w = 가장 긴 줄 글자 수, f = 파일 수, e = 오류 수
# basis: estimate
def main(paths: list[str]) -> int:
    if not paths:
        print("usage: check_doc.py FILE [FILE ...]", file=sys.stderr)
        return 2
    return 1 if sum(check(path) for path in paths) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
