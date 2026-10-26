"""figure_audit의 항목 대조, 배치 위험 경고, SVG 크기 보고, 종료 코드 검증."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "figure_audit.py"
_SPEC = importlib.util.spec_from_file_location("figure_audit", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
AUDIT = importlib.util.module_from_spec(_SPEC)
sys.modules["figure_audit"] = AUDIT
_SPEC.loader.exec_module(AUDIT)

CHAIN = """diagramplay
box a "가" badge="S"
box b "나" badge="S"
box c "다" badge="S"
box d "라" badge="S"
box e "마" badge="S"
a -> b
b -> c
c -> d
d -> e
"""


def codes(source: str) -> list[str]:
    return [line.split(":", 1)[0] for line in AUDIT.warnings(AUDIT.parse(source))]


class WarningTest(unittest.TestCase):
    def test_chain_is_clean(self) -> None:
        self.assertEqual(codes(CHAIN), [])

    def test_aspect_and_width_wide_warn(self) -> None:
        self.assertEqual(codes(CHAIN.replace("diagramplay\n", "diagramplay\naspect 3\n")), [])
        self.assertEqual(codes(CHAIN.replace("diagramplay\n", "diagramplay\naspect 3\n") + "a -> e\n"), ["aspect"])
        self.assertEqual(codes(CHAIN.replace("diagramplay\n", "diagramplay\nwidth wide\n")), ["wide"])

    def test_branching_graph_is_not_a_chain(self) -> None:
        self.assertEqual(codes(CHAIN + "a -> e\n"), [])

    def test_long_card_name_warns_and_short_name_does_not(self) -> None:
        self.assertEqual(codes('diagramplay\nbox a "주문 서비스가 재고를 확인함"\n'), ["name"])
        self.assertEqual(codes('diagramplay\nbox a "푸시 서비스" "부제는 길어도 된다"\n'), [])

    def test_long_edge_label_warns(self) -> None:
        source = 'diagramplay\nbox a "가"\nbox b "나"\na -> b "HTTPS POST 요청으로 주문 내용을 전달"\n'
        self.assertEqual(codes(source), ["label"])

    def test_sequence_with_two_scenes_warns(self) -> None:
        source = 'diagramplay\nbox a "가"\nbox b "나"\nview sequence {\n  a b\n}\nscene "하나"\n  a -> b "요청"\nscene "둘"\n  b -> a "응답"\n'
        self.assertEqual(codes(source), ["scenes"])

    def test_loose_cards_warn(self) -> None:
        source = 'diagramplay\nperson a "가"\nperson b "나"\nperson m1 "지표1"\nperson m2 "지표2"\na -> b\n'
        self.assertEqual(codes(source), ["loose"])

    def test_chained_groups_warn_as_staircase(self) -> None:
        source = "diagramplay\n" + "".join(f'group g{i} "묶음{i}" direction=down {{\n  box n{i} "카{i}" badge="S"\n  box m{i} "드{i}" badge="S"\n}}\n' for i in range(3))
        source += "n0 -> m0\nm0 -> n1\nn1 -> m1\nm1 -> n2\nn2 -> m2\n"
        self.assertEqual(codes(source), ["staircase"])

    def test_flat_cards_warn_until_tagged_or_focal(self) -> None:
        flat = 'diagramplay\nbox a "가"\nbox b "나"\nbox c "다"\nstore d "라"\na -> b\na -> c\na -> d\n'
        self.assertEqual(codes(flat), ["flat"])
        self.assertEqual(codes(flat.replace('box a "가"', 'box a "가" tone=blue appearance=filled')), [])

    def test_flowchart_with_decision_is_not_flat(self) -> None:
        source = 'diagramplay\nbox a "가"\nbox b "나"\nbox c "다"\nbox d "라"\ndecision g "갈래"\na -> b\nb -> g\ng -> c "예"\ng -> d "아니오"\n'
        self.assertEqual(codes(source), [])

    def test_condition_and_metric_cards_are_exempt(self) -> None:
        source = 'diagramplay\nbox a "가" badge="APP"\ndecision g "오류율 > 1% 인가?"\nbox k "성과" {\n  value p "지연" from=-85%\n}\na -> g\n'
        self.assertEqual(codes(source), [])

    def test_partial_badges_warn(self) -> None:
        source = 'diagramplay\nbox a "가" badge="API"\nbox b "나"\na -> b\n'
        self.assertEqual(codes(source), ["badge"])

    def test_more_than_two_focal_cards_warn(self) -> None:
        cards = "".join(f'box n{i} "카{i}" badge="S" tone=blue appearance=filled\n' for i in range(3))
        self.assertEqual(codes(f"diagramplay\n{cards}n0 -> n1\nn0 -> n2\n"), ["focal"])

    def test_too_many_edges_warn(self) -> None:
        cards = "".join(f'box n{i} "카{i}" badge="APP"\n' for i in range(5))
        lines = "".join([f"n{a} -> n{b}\n" for a in range(5) for b in range(5) if a != b][:13])
        source = f"diagramplay\n{cards}{lines}"
        self.assertIn("edges", codes(source))

    def test_sequence_with_too_many_messages_warns(self) -> None:
        moves = "".join(f'  a -> b "요청{i}"\n' for i in range(5))
        source = f'diagramplay\nbox a "가"\nbox b "나"\nbox c "다"\nview sequence {{\n  a b c\n}}\nscene "하나"\n{moves}'
        self.assertEqual(codes(source), ["messages"])
        self.assertEqual(codes(source.replace('  a -> b "요청4"\n', '')), [])

    def test_too_many_series_warns(self) -> None:
        series = "".join(f'  series s{i} "계열{i}"\n' for i in range(8))
        self.assertEqual(codes(f'diagramplay\nchart c "차트" bar {{\n{series}  row "가" s0=1\n}}\n'), ["series"])


class ItemTest(unittest.TestCase):
    def test_missing_item_and_alternatives(self) -> None:
        fig = AUDIT.parse('diagramplay\ntitle "토큰 갱신"\nbox a "인증 서버"\nbox b "DB"\na -> b "POST /refresh"\n')
        lost = AUDIT.missing(fig, [["인증 서버"], ["토큰 갱신", "/refresh"], ["캐시"]])
        self.assertEqual(lost, ["캐시"])

    def test_title_alone_does_not_count(self) -> None:
        fig = AUDIT.parse('diagramplay\ntitle "환불 흐름"\nstate a "생성"\n')
        self.assertEqual(AUDIT.missing(fig, [["환불"]]), ["환불"])

    def test_hash_inside_quotes_is_text(self) -> None:
        fig = AUDIT.parse('diagramplay\nbox a "C# 서버" # 주석\n')
        self.assertEqual(fig.cards, {"a": "C# 서버"})

    def test_value_text_counts(self) -> None:
        fig = AUDIT.parse('diagramplay\nbox k "성과" {\n  value p "p95 지연" from=-85%\n}\n')
        self.assertEqual(AUDIT.missing(fig, [["p95 지연"], ["-85%"]]), [])


class CliTest(unittest.TestCase):
    def run_cli(self, *args: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = AUDIT.main(list(args))
        return code, out.getvalue()

    def test_exit_codes_and_svg_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.diagramplay").write_text(CHAIN, encoding="utf-8")
            (root / "items.txt").write_text("# 요구 항목\n가\n마\n", encoding="utf-8")
            (root / "a.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 800 300"></svg>', encoding="utf-8")
            code, out = self.run_cli(str(root / "a.diagramplay"), "--items", str(root / "items.txt"))
            self.assertEqual((code, out), (0, ""))
            code, out = self.run_cli(str(root / "a.diagramplay"), "--svg", str(root / "a.svg"))
            self.assertEqual(code, 0)
            self.assertIn("크기: 800x300", out)
            (root / "tall.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 300 900"></svg>', encoding="utf-8")
            (root / "b.diagramplay").write_text(CHAIN, encoding="utf-8")
            code, out = self.run_cli(str(root / "b.diagramplay"), "--svg", str(root / "tall.svg"))
            self.assertEqual(code, 1)
            self.assertIn("경고 portrait", out)
            (root / "items.txt").write_text("바\n", encoding="utf-8")
            code, out = self.run_cli(str(root / "a.diagramplay"), "--items", str(root / "items.txt"))
            self.assertEqual((code, out), (1, "누락: 바\n"))
            (root / "wide.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1020 300"></svg>', encoding="utf-8")
            code, out = self.run_cli(str(root / "a.diagramplay"), "--svg", str(root / "wide.svg"))
            self.assertEqual(code, 1)
            self.assertIn("경고 small", out)
            code, _ = self.run_cli(str(root / "none.diagramplay"))
            self.assertEqual(code, 2)

    def test_zigzag_wrap_warns_but_three_per_row_passes(self) -> None:
        six = CHAIN.replace("d -> e\n", "d -> e\nbox f \"바\" badge=\"S\"\ne -> f\n")
        across = 'M 620 80 L 650 80 Q 670 80, 670 100 L 670 140 Q 670 160, 650 160 L 40 160 Q 20 160, 20 180 L 20 220 Q 20 240, 40 240 L 150 240'
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 480"><path class="fl-path" d="{0}"/><path class="fl-path" d="{1}"/><path class="fl-path" d="M 300 80 L 440 80"/></svg>'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "six.diagramplay").write_text(six, encoding="utf-8")
            (root / "zigzag.svg").write_text(svg.format(across, across.replace("80", "320").replace("160", "400")), encoding="utf-8")
            code, out = self.run_cli(str(root / "six.diagramplay"), "--svg", str(root / "zigzag.svg"))
            self.assertEqual(code, 1)
            self.assertIn("경고 wrap", out)
            self.assertIn("카드 2개씩", out)
            (root / "rows.svg").write_text(svg.format(across, "M 100 400 L 200 400"), encoding="utf-8")
            code, out = self.run_cli(str(root / "six.diagramplay"), "--svg", str(root / "rows.svg"))
            self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
