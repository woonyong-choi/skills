"""이슈 #9의 CLI 이름과 한 판 호환 계약 검증."""

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


class DaphnisCliTest(unittest.TestCase):
    # 이슈 #9: 명시 옵션 우선, 새 이름 우선, 옛 이름 지정 시 stderr 폐기 안내.
    def test_cli_and_environment_precedence_with_deprecation(self) -> None:
        cases = [
            (["--daphnis", "new.js"], {}, "new.js", []),
            (["--mutoscope", "old.js"], {}, "old.js", ["--mutoscope"]),
            ([], {"DAPHNIS_PATH": "new.js"}, "new.js", []),
            ([], {"MUTOSCOPE_PATH": "old.js"}, "old.js", ["MUTOSCOPE_PATH"]),
            (
                ["--mutoscope", "old.js", "--daphnis", "new.js"],
                {},
                "new.js",
                ["--mutoscope"],
            ),
            (
                [],
                {"DAPHNIS_PATH": "new.js", "MUTOSCOPE_PATH": "old.js"},
                "new.js",
                ["MUTOSCOPE_PATH"],
            ),
            (
                ["--daphnis", "new.js"],
                {"MUTOSCOPE_PATH": "old.js"},
                "new.js",
                ["MUTOSCOPE_PATH"],
            ),
            (
                ["--mutoscope", "old.js"],
                {"DAPHNIS_PATH": "new.js"},
                "old.js",
                ["--mutoscope"],
            ),
        ]
        for options, environment, selected, warnings in cases:
            for script in (FIGURES, REPORT):
                with self.subTest(
                    script=script.__name__, options=options, env=environment
                ):
                    stderr = io.StringIO()
                    with contextlib.ExitStack() as stack:
                        stack.enter_context(
                            patch.dict(os.environ, environment, clear=True)
                        )
                        stack.enter_context(contextlib.redirect_stderr(stderr))
                        run = stack.enter_context(
                            patch.object(script.subprocess, "run")
                        )
                        stack.enter_context(
                            patch.object(Path, "is_dir", return_value=False)
                        )
                        stack.enter_context(
                            patch.object(Path, "is_file", return_value=True)
                        )
                        if script is FIGURES:
                            self.assertEqual(script.main([*options, "sample.dap"]), 0)
                        else:
                            stack.enter_context(
                                patch.object(
                                    sys,
                                    "argv",
                                    ["build_report.py", "input.json", *options],
                                )
                            )
                            stack.enter_context(
                                patch.object(
                                    Path,
                                    "read_text",
                                    return_value='{"kind":"result","title":"test","intro":"test","questions":[{"title":"test","what":"test","options":[{"label":"test","images":[{"dap":"sample.dap","alt":"test"}]}],"effect":[["test","test","test"]],"rec":["test","test"]}]}',
                                )
                            )
                            stack.enter_context(patch.object(Path, "write_text"))
                            stack.enter_context(
                                contextlib.redirect_stdout(io.StringIO())
                            )
                            run.return_value = subprocess.CompletedProcess(
                                [], 0, "", ""
                            )
                            script.main()
                        command = run.call_args_list[-1].args[0]
                        self.assertEqual(Path(command[1]).name, selected)
                    diagnostics = stderr.getvalue()
                    self.assertEqual(diagnostics.count("deprecated:"), len(warnings))
                    for warning in warnings:
                        self.assertIn(warning, diagnostics)
                        self.assertIn("after this release", diagnostics)

    # 이슈 #9: PATH의 새 명령과 git 추적 .dap 탐색 유지.
    def test_tracked_dap_sources_use_daphnis_on_path(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(FIGURES.subprocess, "run") as run,
        ):
            run.return_value.stdout = b"diagram with spaces.dap\0"
            self.assertEqual(FIGURES.main([]), 0)
        self.assertIn("*.dap", run.call_args_list[0].args[0])
        self.assertEqual(
            run.call_args_list[1].args[0],
            ["daphnis", "check", "diagram with spaces.dap", "--strict"],
        )
        self.assertEqual(
            run.call_args_list[2].args[0],
            ["daphnis", "render", "diagram with spaces.dap", "--strict"],
        )

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
            self.assertEqual(FIGURES.main(["invalid.dap"]), 1)
        self.assertEqual(run.call_count, 1)

    # 이슈 #9: 이전 보고서 키를 조용히 누락하지 않고 새 키 안내.
    def test_old_report_key_fails_before_output_write(self) -> None:
        spec = {
            "title": "test",
            "intro": "test",
            "questions": [
                {
                    "title": "test",
                    "what": "test",
                    "options": [{"label": "test", "images": [{"muto": "old.muto"}]}],
                    "effect": [["test", "test", "test"]],
                    "rec": ["test", "test"],
                }
            ],
        }
        renderer = REPORT.FigureRenderer(base=ROOT, daphnis=None, static=False)
        with self.assertRaisesRegex(REPORT.ReportError, "src, dap, inline"):
            REPORT.build(spec, renderer, "")


if __name__ == "__main__":
    unittest.main()
