"""Torso 원본(.torso)의 항목 누락과 품질 위험 배치를 찾는다.

인자: 원본 경로 하나, --items 요구 항목 파일(한 줄에 항목 하나, `#` 주석, `|`로 같은 뜻의 다른 이름), --svg 렌더한 SVG(크기와 세로형 판정), --print 인쇄용 그림(width wide를 요구하지 않음)
출력: stdout `누락:`, `경고 <코드>:`, `크기:` 줄, 종료 0 문제 없음·1 누락이나 경고 있음·2 인자 오류나 읽기 실패
실행 조건: Python 3.9 이상, 표준 라이브러리만. Torso 문법 검사는 대신하지 않으므로 `torso check --strict`를 따로 돌린다
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

CARD_WORDS = {"person", "box", "external", "store", "decision", "queue", "state", "table", "api", "class", "interface"}
NAME_UNITS = 11  # 카드 최소 폭(100px 안팎)에 드는 이름 폭. 한글 5자와 띄어쓰기 하나, 영문 10자
EDGE_UNITS = 20  # 선과 메시지 글 폭. 한글 10자
CARDS_MAX = 12
EDGES_MAX = 12
FOCAL_MAX = 2
TAGGED = {"box", "external", "store"}  # 꼬리표를 다는 카드. person은 받지만 사람 아이콘이 종류를 대신해 달지 않는다
FLAT_MIN = 4
CHAIN_MIN = 5
SERIES_MAX = 7
BODY = 680
TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"|\S+')
EDGE = re.compile(r"^([\w.-]+)\s*->\s*([\w.-]+)(.*)$")


@dataclass
class Figure:
    cards: dict[str, str] = field(default_factory=dict)
    groups: dict[str, list[str]] = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    edge_labels: list[str] = field(default_factory=list)
    series: dict[str, int] = field(default_factory=dict)
    badges: dict[str, bool] = field(default_factory=dict)
    conditions: set[str] = field(default_factory=set)
    focal: list[str] = field(default_factory=list)
    scenes: int = 0
    sequence: bool = False
    aspect: bool = False
    flowchart: bool = False
    participants: int = 0
    scene_messages: list[int] = field(default_factory=list)
    wide: bool = False


def strip_comment(line: str) -> str:
    quoted = False
    for i, ch in enumerate(line):
        if ch == '"':
            quoted = not quoted
        elif ch == "#" and not quoted:
            return line[:i]
    return line


def units(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def unquote(token: str) -> str:
    return token[1:-1] if token.startswith('"') and token.endswith('"') else token


def parse(source: str) -> Figure:
    fig = Figure()
    stack: list[str] = []
    in_scene = False
    in_sequence_view = False
    for raw in source.splitlines():
        line = strip_comment(raw).strip()
        if not line:
            continue
        tokens = TOKEN.findall(line)
        word = tokens[0]
        quoted = [unquote(t) for t in tokens if t.startswith('"')]
        if word == "}":
            if stack:
                stack.pop()
            in_sequence_view = False
            continue
        if in_sequence_view:
            fig.participants += len(tokens)
            continue
        if word == "scene":
            in_scene = True
            fig.scenes += 1
            fig.scene_messages.append(0)
            continue
        if word in ("title", "subtitle"):
            continue  # 그래프 SVG에 그리지 않는 글이라 항목 대조에서 뺀다
        if word == "aspect":
            fig.aspect = True
        elif word == "width" and "wide" in tokens:
            fig.wide = True
        elif word == "view" and len(tokens) > 1 and tokens[1] == "sequence":
            fig.sequence = True
            in_sequence_view = line.endswith("{")
        fig.texts.extend(quoted)
        fig.texts.extend(t[5:] for t in tokens if t.startswith("from="))
        match = EDGE.match(line)
        if match:
            if not in_scene:
                fig.edges.append((match.group(1).split(".")[0], match.group(2).split(".")[0]))
            elif fig.scene_messages:
                fig.scene_messages[-1] += 1
            fig.edge_labels.extend(quoted)
        elif word in CARD_WORDS and len(tokens) > 1 and not in_scene:
            if word in ("decision", "state"):
                fig.flowchart = True
            if word == "decision":
                fig.conditions.add(tokens[1])
            fig.cards[tokens[1]] = quoted[0] if quoted else tokens[1]
            if word in TAGGED:
                fig.badges[tokens[1]] = any(t.startswith("badge=") for t in tokens)
            if "appearance=filled" in tokens or "appearance=outline" in tokens:
                fig.focal.append(tokens[1])
            for group in stack:
                if group in fig.groups:
                    fig.groups[group].append(tokens[1])
        elif word == "group" and len(tokens) > 1:
            fig.groups[tokens[1]] = []
        elif word == "value" and stack and stack[-1] in fig.badges:
            del fig.badges[stack[-1]]  # 값 줄 카드는 구성 요소가 아니라 수치 묶음이라 꼬리표를 요구하지 않는다
        elif word == "series" and stack:
            fig.series[stack[-1]] = fig.series.get(stack[-1], 0) + 1
        if line.endswith("{"):
            stack.append(tokens[1] if len(tokens) > 1 else word)
    return fig


def read_items(path: Path) -> list[list[str]]:
    items = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            items.append([part.strip() for part in line.split("|") if part.strip()])
    return items


def missing(fig: Figure, items: list[list[str]]) -> list[str]:
    haystack = [" ".join(t.split()) for t in fig.texts]
    return [" | ".join(names) for names in items if not any(n in t for n in names for t in haystack)]


def chain_length(fig: Figure) -> int:
    """선이 갈래 없이 한 줄로 이어지면 그 카드 수, 아니면 0."""
    if not fig.edges:
        return 0
    outs: dict[str, int] = {}
    ins: dict[str, int] = {}
    for a, b in fig.edges:
        outs[a] = outs.get(a, 0) + 1
        ins[b] = ins.get(b, 0) + 1
    nodes = set(outs) | set(ins)
    if any(v > 1 for v in outs.values()) or any(v > 1 for v in ins.values()):
        return 0
    return len(nodes) if len(fig.edges) == len(nodes) - 1 else 0


def group_chain(fig: Figure) -> int:
    """그룹 사이 선이 그룹을 차례로 잇는 개수(계단 배치 위험)."""
    owner = {card: g for g, cards in fig.groups.items() for card in cards}
    links = {(owner.get(a), owner.get(b)) for a, b in fig.edges if owner.get(a) and owner.get(b) and owner.get(a) != owner.get(b)}
    outs = {a for a, _ in links}
    ins = {b for _, b in links}
    return len(outs | ins) if links and len(links) == len(outs | ins) - 1 else 0


def warnings(fig: Figure) -> list[str]:
    found = []
    for card, name in fig.cards.items():
        if card not in fig.conditions and units(name) > NAME_UNITS:
            found.append(f"name: 카드 {card}의 이름 \"{name}\"이 한글 5자(영문 10자)를 넘어 카드 폭이 달라진다. 설명은 부제나 text로 옮긴다")
    for label in fig.edge_labels:
        if units(label) > EDGE_UNITS:
            found.append(f"label: 선 글 \"{label}\"이 한글 10자를 넘는다. 짧게 줄이고 설명은 본문에 쓴다")
    if len(fig.cards) > CARDS_MAX:
        found.append(f"cards: 카드가 {len(fig.cards)}개다. {CARDS_MAX}개 이하로 묶거나 그림을 나눈다")
    if len(fig.edges) > EDGES_MAX:
        found.append(f"edges: 선이 {len(fig.edges)}개다. {EDGES_MAX}개 이하로 줄이거나 그림을 나눈다")
    chain = chain_length(fig)
    if chain >= CHAIN_MIN and not fig.aspect and not fig.groups:
        found.append(f"chain: 카드 {chain}개가 한 줄로 이어져 세로 한 줄로 그려진다. aspect 1.6을 머리에 적는다")
    if group_chain(fig) >= 3 and not fig.aspect:
        found.append("staircase: 그룹 세 개 이상을 차례로 이어 계단처럼 대각선으로 늘어진다. 그룹을 한 출발점에서 갈라지게 묶거나, 단계 그룹이면 단계 카드 안 text 줄로 바꾸거나, aspect 1.6을 쓴다")
    if fig.aspect and fig.edges and (fig.groups or not chain_length(fig)):
        found.append("aspect: 갈래나 그룹이 있는 그림을 aspect로 접으면 되돌아오는 선이 그림을 가로지른다. aspect를 지우고 기본 배치에 맡긴다")
    tagged = [c for c, has in fig.badges.items() if has]
    if tagged and len(tagged) < len(fig.badges):
        bare = [c for c, has in fig.badges.items() if not has]
        found.append(f"badge: 꼬리표가 일부 카드에만 있다. {', '.join(bare)}에도 종류 꼬리표를 단다")
    if len(fig.badges) >= FLAT_MIN and not tagged and not fig.focal and not fig.sequence and not fig.flowchart and not chain_length(fig):
        found.append("flat: 카드가 모두 같은 모양이라 종류와 초점이 보이지 않는다. 종류 꼬리표(badge=)와 초점 색 1~2개를 단다")
    if len(fig.focal) > FOCAL_MAX:
        found.append(f"focal: 색을 칠한 카드가 {len(fig.focal)}개다. 초점은 {FOCAL_MAX}개 이하로 둔다")
    if fig.cards and not fig.series and not fig.wide:
        found.append("wide: 머리에 width wide가 없어 680px을 넘는 배치가 세로로 돌아간다. 머리에 width wide를 적는다(인쇄용 포트폴리오는 --print)")
    limit = 2 * fig.participants - 1
    if fig.sequence and fig.participants and any(n > limit for n in fig.scene_messages):
        found.append(f"messages: 참여자 {fig.participants}명 순서 그림의 한 장면 메시지가 {max(fig.scene_messages)}개라 세로형이 된다. 장면마다 {limit}개 이하로 그림을 나눈다")
    if fig.sequence and fig.scenes > 1:
        found.append(f"scenes: 순서 그림에 장면이 {fig.scenes}개다. 정지 SVG는 첫 장면 메시지만 보이므로 한 장에 다 보이려면 fragment로 한 장면에 담는다")
    linked = {n for edge in fig.edges for n in edge}
    loose = [c for c in fig.cards if c not in linked]
    if len(loose) >= 2 and fig.edges:
        found.append(f"loose: 선 없는 카드 {', '.join(loose)}는 선언 순서와 다르게 세로로 쌓인다. 값 줄을 가진 카드 하나로 합친다")
    for chart, count in fig.series.items():
        if count > SERIES_MAX:
            found.append(f"series: 차트 {chart}의 계열이 {count}개라 색이 되풀이된다. 계열을 줄이거나 차트를 나눈다")
    return found


def svg_size(path: Path) -> tuple[float, float]:
    head = path.read_text(encoding="utf-8")[:2000]
    match = re.search(r'<svg[^>]*?\swidth="([\d.]+)"[^>]*?\sheight="([\d.]+)"', head)
    if not match:
        raise ValueError(f"{path}: SVG 크기를 찾지 못했다")
    return float(match.group(1)), float(match.group(2))


def size_lines(width: float, height: float) -> tuple[list[str], list[str]]:
    body = min(1.0, BODY / width)
    info = [f"크기: {width:g}x{height:g}, 본문 단 {BODY}px 칸에서 {body:.2f}배"]
    found = []
    if height > width:
        found.append(f"portrait: 높이 {height:g}가 폭 {width:g}보다 커 세로형이다. 가로형 원칙의 한도대로 줄이거나 그림을 나눈다")
    return info, found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path)
    parser.add_argument("--items", type=Path)
    parser.add_argument("--svg", type=Path)
    parser.add_argument("--print", action="store_true", dest="for_print", help="인쇄용 그림이라 width wide를 요구하지 않는다")
    args = parser.parse_args(argv)
    try:
        fig = parse(args.source.read_text(encoding="utf-8"))
        items = read_items(args.items) if args.items else []
        info, size_found = size_lines(*svg_size(args.svg)) if args.svg else ([], [])
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 2
    lost = missing(fig, items)
    found = [w for w in warnings(fig) if not (args.for_print and w.startswith("wide:"))] + size_found
    for line in info:
        print(line)
    for item in lost:
        print(f"누락: {item}")
    for line in found:
        code, text = line.split(": ", 1)
        print(f"경고 {code}: {text}")
    return 1 if lost or found else 0


if __name__ == "__main__":
    sys.exit(main())
