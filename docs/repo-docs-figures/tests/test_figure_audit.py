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

CHAIN = """thinkflow
box a "가"
box b "나"
box c "다"
box d "라"
box e "마"
a -> b
b -> c
c -> d
d -> e
"""


def codes(source: str) -> list[str]:
    return [line.split(":", 1)[0] for line in AUDIT.warnings(AUDIT.parse(source))]


class WarningTest(unittest.TestCase):
    def test_chain_without_aspect_warns(self) -> None:
        self.assertEqual(codes(CHAIN), ["chain"])

    def test_chain_with_aspect_is_clean(self) -> None:
        self.assertEqual(codes(CHAIN.replace("thinkflow\n", "thinkflow\naspect 1.6\n")), [])

    def test_branching_graph_is_not_a_chain(self) -> None:
        self.assertEqual(codes(CHAIN + "a -> e\n"), [])

    def test_long_card_name_warns_and_short_name_does_not(self) -> None:
        self.assertEqual(codes('thinkflow\nbox a "주문 서비스가 재고를 확인함"\n'), ["name"])
        self.assertEqual(codes('thinkflow\nbox a "푸시 서비스" "부제는 길어도 된다"\n'), [])

    def test_long_edge_label_warns(self) -> None:
        source = 'thinkflow\nbox a "가"\nbox b "나"\na -> b "HTTPS POST 요청으로 주문 내용을 전달"\n'
        self.assertEqual(codes(source), ["label"])

    def test_sequence_with_two_scenes_warns(self) -> None:
        source = 'thinkflow\nbox a "가"\nbox b "나"\nview sequence {\n  a b\n}\nscene "하나"\n  a -> b "요청"\nscene "둘"\n  b -> a "응답"\n'
        self.assertEqual(codes(source), ["scenes"])

    def test_loose_cards_warn(self) -> None:
        source = 'thinkflow\nbox a "가"\nbox b "나"\nbox m1 "지표1"\nbox m2 "지표2"\na -> b\n'
        self.assertEqual(codes(source), ["loose"])

    def test_chained_groups_warn_as_staircase(self) -> None:
        source = "thinkflow\n" + "".join(f'group g{i} "묶음{i}" direction=down {{\n  box n{i} "카{i}"\n  box m{i} "드{i}"\n}}\n' for i in range(3))
        source += "n0 -> m0\nm0 -> n1\nn1 -> m1\nm1 -> n2\nn2 -> m2\n"
        self.assertEqual(codes(source), ["staircase"])

    def test_too_many_series_warns(self) -> None:
        series = "".join(f'  series s{i} "계열{i}"\n' for i in range(8))
        self.assertEqual(codes(f'thinkflow\nchart c "차트" bar {{\n{series}  row "가" s0=1\n}}\n'), ["series"])


class ItemTest(unittest.TestCase):
    def test_missing_item_and_alternatives(self) -> None:
        fig = AUDIT.parse('thinkflow\ntitle "토큰 갱신"\nbox a "인증 서버"\nbox b "DB"\na -> b "POST /refresh"\n')
        lost = AUDIT.missing(fig, [["인증 서버"], ["토큰 갱신", "/refresh"], ["캐시"]])
        self.assertEqual(lost, ["캐시"])

    def test_title_alone_does_not_count(self) -> None:
        fig = AUDIT.parse('thinkflow\ntitle "환불 흐름"\nstate a "생성"\n')
        self.assertEqual(AUDIT.missing(fig, [["환불"]]), ["환불"])

    def test_hash_inside_quotes_is_text(self) -> None:
        fig = AUDIT.parse('thinkflow\nbox a "C# 서버" # 주석\n')
        self.assertEqual(fig.cards, {"a": "C# 서버"})

    def test_value_text_counts(self) -> None:
        fig = AUDIT.parse('thinkflow\nbox k "성과" {\n  value p "p95 지연" from=-85%\n}\n')
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
            (root / "a.thinkflow").write_text(CHAIN.replace("thinkflow\n", "thinkflow\naspect 1.6\n"), encoding="utf-8")
            (root / "items.txt").write_text("# 요구 항목\n가\n마\n", encoding="utf-8")
            (root / "a.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1020" height="300"></svg>', encoding="utf-8")
            code, out = self.run_cli(str(root / "a.thinkflow"), "--items", str(root / "items.txt"))
            self.assertEqual((code, out), (0, ""))
            code, out = self.run_cli(str(root / "a.thinkflow"), "--svg", str(root / "a.svg"))
            self.assertEqual(code, 1)
            self.assertIn("크기: 1020x300", out)
            self.assertIn("경고 width", out)
            (root / "items.txt").write_text("바\n", encoding="utf-8")
            code, out = self.run_cli(str(root / "a.thinkflow"), "--items", str(root / "items.txt"))
            self.assertEqual((code, out), (1, "누락: 바\n"))
            code, _ = self.run_cli(str(root / "none.thinkflow"))
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
