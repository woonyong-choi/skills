"""그림 변환·보고서 스크립트의 ThinkFlow 경로·원본 확장자 계약 검증."""

import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

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


FIGURES = load_script(
    "render_figures", "docs/repo-docs-figures/scripts/render_figures.py"
)
REPORT = load_script("build_report", "docs/html-report/scripts/build_report.py")


class ThinkflowCliTest(unittest.TestCase):
    # 명시 옵션이 환경 변수보다 우선한다.
    def test_option_precedes_environment(self) -> None:
        for options, environment, selected in (
            (["--thinkflow", "new.js"], {"THINKFLOW_PATH": "env.js"}, "new.js"),
            ([], {"THINKFLOW_PATH": "env.js"}, "env.js"),
        ):
            with (
                self.subTest(options=options),
                patch.dict(os.environ, environment, clear=True),
                patch.object(FIGURES.subprocess, "run") as run,
                patch.object(Path, "is_dir", return_value=False),
            ):
                self.assertEqual(FIGURES.main([*options, "sample.thinkflow"]), 0)
                self.assertEqual(Path(run.call_args_list[-1].args[0][1]).name, selected)

    # PATH의 thinkflow와 git 추적 원본 탐색. 다른 확장자는 이전 안내로 실패한다.
    def test_tracked_sources_use_thinkflow_on_path(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(FIGURES.subprocess, "run") as run,
        ):
            run.return_value.stdout = b"diagram with spaces.thinkflow\0"
            self.assertEqual(FIGURES.main([]), 0)
        self.assertIn("*.thinkflow", run.call_args_list[0].args[0])
        self.assertEqual(
            run.call_args_list[1].args[0],
            ["thinkflow", "check", "diagram with spaces.thinkflow", "--strict"],
        )
        self.assertEqual(
            run.call_args_list[2].args[0],
            ["thinkflow", "render", "diagram with spaces.thinkflow", "--strict"],
        )
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(FIGURES.main(["old.svg"]), 1)
        self.assertIn("migrate to .thinkflow", stderr.getvalue())

    # strict 실패 원본은 렌더를 시작하지 않는 공개 계약.
    def test_failed_check_does_not_render(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(
                FIGURES.subprocess,
                "run",
                side_effect=subprocess.CalledProcessError(1, "check"),
            ) as run,
        ):
            self.assertEqual(FIGURES.main(["invalid.thinkflow"]), 1)
        self.assertEqual(run.call_count, 1)

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


if __name__ == "__main__":
    unittest.main()
