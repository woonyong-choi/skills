"""보고서 스크립트의 ThinkFlow 그림 키·확장자 계약 검증."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[3]


# cost: time O(n), heap O(n), stack O(1), io 1
# vars: n = 읽는 스크립트 크기
# basis: estimate
def load_script(name: str, relative: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


REPORT = load_script("build_report", "docs/html-report/scripts/build_report.py")


class ReportFigureKeyTest(unittest.TestCase):
    # 모르는 그림 키와 확장자는 출력 전에 실패한다.
    def test_old_report_key_fails_before_output_write(self) -> None:
        spec = {
            "title": "test",
            "intro": "test",
            "questions": [
                {
                    "title": "test",
                    "what": "test",
                    "options": [{"label": "test", "images": [{"figure": "old.svg"}]}],
                    "effect": [["test", "test", "test"]],
                    "rec": ["test", "test"],
                }
            ],
        }
        renderer = REPORT.FigureRenderer(base=ROOT, thinkflow=None, static=False)
        with self.assertRaisesRegex(REPORT.ReportError, "src, thinkflow, inline"):
            REPORT.build(spec, renderer, "")
        spec["questions"][0]["options"][0]["images"] = [{"thinkflow": "old.svg"}]
        with self.assertRaisesRegex(REPORT.ReportError, "must end with .thinkflow"):
            REPORT.build(spec, renderer, "")


class ThinkflowThemeTest(unittest.TestCase):
    # ThinkFlow는 공통 테마를 design-tokens 패키지에서 읽는다(ThinkFlow #327).
    def _tokens(self, node_modules: Path) -> Path:
        dist = node_modules / "@woonyong-choi" / "design-tokens" / "dist"
        dist.mkdir(parents=True)
        (dist / "tokens.css").write_text(":root{}", encoding="utf-8")
        return dist

    def test_checkout_reads_theme_from_design_tokens_package(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "src").mkdir()
            (root / "src" / "cli.js").write_text("", encoding="utf-8")
            dist = self._tokens(root / "node_modules")
            thinkflow = REPORT._thinkflow(str(root))
            self.assertEqual(thinkflow.cli, root.resolve() / "src" / "cli.js")
            self.assertEqual(thinkflow.theme, dist.resolve())

    def test_installed_package_reads_sibling_design_tokens(self) -> None:
        # npm 설치본은 peer 의존성을 thinkflow 옆 node_modules에 둔다.
        with tempfile.TemporaryDirectory() as folder:
            modules = Path(folder) / "node_modules"
            cli = modules / "thinkflow" / "src" / "cli.js"
            cli.parent.mkdir(parents=True)
            cli.write_text("", encoding="utf-8")
            dist = self._tokens(modules)
            thinkflow = REPORT._thinkflow(str(cli))
            self.assertEqual(thinkflow.theme, dist.resolve())

    def test_missing_design_tokens_names_package(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "src").mkdir()
            (root / "src" / "cli.js").write_text("", encoding="utf-8")
            with self.assertRaisesRegex(REPORT.ReportError, "@woonyong-choi/design-tokens"):
                REPORT._thinkflow(str(root))


if __name__ == "__main__":
    unittest.main()
