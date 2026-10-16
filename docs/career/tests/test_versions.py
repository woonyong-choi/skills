"""career 공고 폴더: 첫 작성 → 수정 → 확정 → 수정 흐름, 변경 표시 정리, 폴더 구조 검사, 하위 폴더 참조 컴파일."""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
import unittest.mock
import zlib
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("career_versions", SKILL / "scripts" / "versions.py")
assert _SPEC is not None and _SPEC.loader is not None
VERSIONS = importlib.util.module_from_spec(_SPEC)
sys.modules["career_versions"] = VERSIONS
_SPEC.loader.exec_module(VERSIONS)

try:
    import typst  # noqa: F401

    HAS_TYPST = True
except ImportError:
    HAS_TYPST = shutil.which("typst") is not None

STRATEGY = "# 공고 분석\n\n- 필수 5개\n\n# 구성 계획\n\n- 방향 A\n\n# 작성\n\n- 이력서\n\n# 확인\n\n- 화면 1쪽\n"
FIRST = """#import "/career.typ": *

#let profile = (name: "김합성", contacts: (link("mailto:a@example.com")[a\\@example.com],))

#show: resume-page.with(profile: profile, photo: none, intro: [주문 시스템 백엔드 개발자])

#section[Projects]
#entry([주문 서버], period: [2025], what: [결제 이벤트 처리],
  items: ([결제 이벤트 중복 처리 제거], [주문 조회 응답 개선]),
)

#diagram("/figures/order-flow.png", [주문 이벤트가 한 번만 처리됨])
"""


# cost: time O(w * h), heap O(w * h), stack O(1)
# vars: w = 폭, h = 높이
# basis: estimate
def png(width: int, height: int) -> bytes:
    import struct

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    body = zlib.compress((b"\x00" + b"\xc8\xc8\xc8" * width) * height)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", body) + chunk(b"IEND", b"")


class FlowTest(unittest.TestCase):
    # cost: time O(1), heap O(1), stack O(1), io O(1)
    # vars: 없음
    # basis: estimate
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        base = Path(self.directory.name)
        (base / "config").mkdir()
        self.env = unittest.mock.patch.dict("os.environ", {"CAREER_ROOT": str(base / "career"), "SKILLS_CONFIG_DIR": str(base / "config")})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.posting = base / "career" / "2026-11-30-합성-백엔드-개발자"
        (self.posting / "이력서").mkdir(parents=True)
        (self.posting / "figures").mkdir()
        shutil.copy(SKILL / "assets" / "typst" / "career.typ", self.posting / "career.typ")
        (self.posting / "jd.md").write_text("# JD\n", encoding="utf-8")
        (self.posting / "전략.md").write_text(STRATEGY, encoding="utf-8")
        (self.posting / "figures" / "order-flow.png").write_bytes(png(200, 80))
        self.work = self.posting / "이력서" / "이력서.typ"

    # cost: time O(1), heap O(1), stack O(1), io O(1)
    # vars: 없음
    # basis: estimate
    def tearDown(self) -> None:
        self.directory.cleanup()

    def files(self) -> list[str]:
        return sorted(path.name for path in (self.posting / "이력서").iterdir())

    def test_first_edit_confirm_edit(self) -> None:
        # 첫 작성: 작업 파일만, 표시 없음
        self.work.write_text(FIRST, encoding="utf-8")
        self.assertEqual(VERSIONS.count_marks(FIRST), {"추가": 0, "바뀜": 0, "삭제": 0})
        self.assertEqual(VERSIONS.check(self.posting), [])
        # 수정: 작업 파일 갱신, 표시와 범례
        edited = FIRST.replace(
            "#show: resume-page", '#show: resume-page'
        ).replace(
            "items: ([결제 이벤트 중복 처리 제거], [주문 조회 응답 개선]),",
            "items: (changed[결제 이벤트 중복 처리 제거][결제 이벤트 중복 0건(하루 12만 건 기준)], removed[주문 조회 응답 개선], added[장애 알림 연결]),",
        ) + "\n#changes-legend([이력서 작업본], [첫 작성])\n#added[추가 문단]\n#removed[지운 문단]\n"
        self.work.write_text(edited, encoding="utf-8")
        self.assertEqual(VERSIONS.count_marks(edited), {"추가": 2, "바뀜": 1, "삭제": 2})
        self.assertEqual(self.files(), ["이력서.typ"])
        # 확정: 깨끗한 0001, 작업 파일도 깨끗
        written = VERSIONS.confirm(self.posting / "이력서", build=False)
        self.assertEqual([path.name for path in written], ["이력서-0001.typ"])
        self.assertEqual(self.files(), ["이력서-0001.typ", "이력서.typ"])
        clean = (self.posting / "이력서" / "이력서-0001.typ").read_text(encoding="utf-8")
        self.assertEqual(clean, self.work.read_text(encoding="utf-8"))
        self.assertNotRegex(clean, r"added\[|changed\[|removed\[|changes-legend")
        self.assertIn("items: ([결제 이벤트 중복 0건(하루 12만 건 기준)], none, [장애 알림 연결]),", clean)
        self.assertIn("추가 문단", clean)
        self.assertNotIn("지운 문단", clean)
        self.assertEqual(VERSIONS.check(self.posting), [])
        # 다시 수정: 0001 대비 표시, 다음 확정은 0002
        self.work.write_text(clean + "\n#added[두 번째 수정]\n", encoding="utf-8")
        VERSIONS.confirm(self.posting / "이력서", build=False)
        self.assertEqual(self.files(), ["이력서-0001.typ", "이력서-0002.typ", "이력서.typ"])

    def test_check_finds_structure_problems(self) -> None:
        self.work.write_text(FIRST.replace('#import "/career.typ"', '#import "../career.typ"'), encoding="utf-8")
        (self.posting / "이력서" / "이력서-1.typ").write_text("x", encoding="utf-8")
        (self.posting / "이력서" / "이력서-0001.typ").write_text("#added[남은 표시]", encoding="utf-8")
        (self.posting / "포트폴리오.typ").write_text("x", encoding="utf-8")
        (self.posting / "career.typ").write_text("// 고친 양식", encoding="utf-8")
        (self.posting / "전략.md").write_text("# SPEC\n\n# PLAN\n\n# IMPLEMENT\n\n# VERIFY\n", encoding="utf-8")
        problems = "\n".join(VERSIONS.check(self.posting))
        for expected in ["career.typ가 스킬 양식과 다름", "전략.md 절", "옛 절 이름", "문서 폴더 안에: 포트폴리오.typ", "이력서-1.typ", "/career.typ", "확정 버전에 변경 표시"]:
            self.assertIn(expected, problems)

    def test_confirm_requires_document_folder(self) -> None:
        with self.assertRaises(VERSIONS.CareerError):
            VERSIONS.confirm(self.posting, build=False)

    def test_confirm_outside_root_writes_nothing(self) -> None:
        outside = Path(self.directory.name) / "elsewhere" / "이력서"
        outside.mkdir(parents=True)
        (outside / "이력서.typ").write_text(FIRST, encoding="utf-8")
        with self.assertRaises(VERSIONS.CareerError):
            VERSIONS.confirm(outside, build=False)
        self.assertEqual(sorted(p.name for p in outside.iterdir()), ["이력서.typ"])

    def test_place_checks_posting_folder_before_any_write(self) -> None:
        outside = Path(self.directory.name) / "elsewhere" / "2026-11-01-회사-백엔드"
        self.assertEqual(VERSIONS.main(["place", str(outside)]), 1)
        self.assertFalse(outside.exists())
        self.assertEqual(VERSIONS.main(["place", str(self.posting)]), 0)

    @unittest.skipUnless(HAS_TYPST, "typst 없음")
    def test_subfolder_template_and_figure_compile_with_marks_on_and_off(self) -> None:
        self.work.write_text(FIRST + "\n#changes-legend([이력서 작업본], [이력서-0001])\n#changed[이전 문장][새 문장]\n", encoding="utf-8")
        written = VERSIONS.confirm(self.posting / "이력서")
        self.assertEqual([path.name for path in written], ["이력서-0001.typ", "이력서-0001.pdf"])
        self.assertTrue((self.posting / "이력서" / "이력서.pdf").is_file())
        self.assertTrue((self.posting / "이력서" / "이력서-0001.pdf").read_bytes().startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
