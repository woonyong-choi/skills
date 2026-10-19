from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "render_figures.py"
_SPEC = importlib.util.spec_from_file_location("render_figures", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
FIGURES = importlib.util.module_from_spec(_SPEC)
sys.modules["render_figures"] = FIGURES
_SPEC.loader.exec_module(FIGURES)


class TapeWorkingDirectoryTest(unittest.TestCase):
    # 가짜 vhs가 실행 위치와 받은 경로를 기록하는 임시 저장소
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name).resolve()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / "docs" / "assets").mkdir(parents=True)
        (self.root / "docs" / "assets" / "demo.tape").write_text("Output docs/assets/demo.gif\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", "docs/assets/demo.tape"], check=True)
        (self.root / "sub").mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.log = self.root / "vhs.log"
        vhs = self.bin / "vhs"
        vhs.write_text(f'#!/bin/sh\necho "$PWD $1" >> "{self.log}"\n', encoding="utf-8")
        vhs.chmod(0o755)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def run_script(self, *arguments: str, cwd: Path) -> None:
        environment = {**os.environ, "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}"}
        completed = subprocess.run([sys.executable, str(SCRIPT), *arguments], cwd=cwd, env=environment, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    # #64: 하위 폴더에서 찾은 녹화의 루트 기준 Output이 하위 폴더로 빠지는 회귀
    def test_discovered_tape_runs_from_repository_root(self) -> None:
        self.run_script(cwd=self.root / "sub")
        self.assertEqual(self.log.read_text(encoding="utf-8").split(), [str(self.root), "docs/assets/demo.tape"])

    def test_explicit_tape_keeps_current_directory(self) -> None:
        self.run_script("../docs/assets/demo.tape", cwd=self.root / "sub")
        self.assertEqual(self.log.read_text(encoding="utf-8").split(), [str(self.root / "sub"), "../docs/assets/demo.tape"])



class DiagramPlayCliTest(unittest.TestCase):
    # 명시 옵션이 환경 변수보다 우선한다.
    def test_option_precedes_environment(self) -> None:
        for options, environment, selected in (
            (["--diagramplay", "new.js"], {"DIAGRAMPLAY_PATH": "env.js"}, "new.js"),
            ([], {"DIAGRAMPLAY_PATH": "env.js"}, "env.js"),
        ):
            with (
                self.subTest(options=options),
                patch.dict(os.environ, environment, clear=True),
                patch.object(FIGURES.subprocess, "run") as run,
                patch.object(Path, "is_dir", return_value=False),
            ):
                self.assertEqual(FIGURES.main([*options, "sample.diagramplay"]), 0)
                self.assertEqual(Path(run.call_args_list[-1].args[0][1]).name, selected)

    def test_tracked_sources_use_diagramplay_on_path(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(FIGURES.subprocess, "run") as run,
        ):
            run.return_value.stdout = b"diagram with spaces.diagramplay\0"
            with patch.object(FIGURES, "_git", side_effect=[os.getcwd().encode() + b"\n", run.return_value.stdout]) as git:
                self.assertEqual(FIGURES.main([]), 0)
        self.assertEqual(
            git.call_args_list[1].args[4:],
            ("--", "docs/assets/*.diagramplay", "docs/assets/*.tape"),
        )
        self.assertEqual(
            run.call_args_list[0].args[0],
            ["diagramplay", "check", "diagram with spaces.diagramplay", "--strict"],
        )
        self.assertEqual(
            run.call_args_list[1].args[0],
            ["diagramplay", "render", "diagram with spaces.diagramplay", "--strict"],
        )
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(FIGURES.main(["old.torso"]), 1)
        self.assertIn("old.torso: unsupported source", stderr.getvalue())

    # 인자 생략: docs/assets/ 밖 원본과 다른 확장자는 찾지 않는다.
    def test_no_argument_run_reads_docs_assets_only(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            for path in ("docs/assets/a.diagramplay", "docs/assets/old.svg", "tests/b.diagramplay", "docs/notes/demo.tape"):
                (repo / path).parent.mkdir(parents=True, exist_ok=True)
                (repo / path).write_text("diagramplay\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            with contextlib.chdir(repo):
                self.assertEqual(FIGURES._tracked_sources(), ["docs/assets/a.diagramplay"])

    # 하위 폴더 실행은 루트 기준 탐색, 원본 없음·git 밖은 메시지와 종료 1.
    def test_no_argument_run_from_subfolder_empty_and_outside_git(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder) / "repo"
            (repo / "docs" / "assets").mkdir(parents=True)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            with contextlib.chdir(repo / "docs"), contextlib.redirect_stderr(io.StringIO()) as stderr:
                self.assertEqual(FIGURES.main([]), 1)
            self.assertIn("no tracked sources under docs/assets/", stderr.getvalue())
            (repo / "docs" / "assets" / "a.diagramplay").write_text("x\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            with contextlib.chdir(repo / "docs"):
                self.assertEqual(FIGURES._tracked_sources(), ["assets/a.diagramplay"])
            outside = Path(folder) / "outside"
            outside.mkdir()
            with (
                patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": folder}),
                contextlib.chdir(outside),
                contextlib.redirect_stderr(io.StringIO()) as stderr,
            ):
                self.assertEqual(FIGURES.main([]), 1)
            self.assertIn("not a git repository", stderr.getvalue())

    # VHS가 없으면 그림 렌더 전에 실패한다.
    def test_missing_vhs_fails_before_rendering(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(FIGURES.shutil, "which", return_value=None),
            patch.object(FIGURES.subprocess, "run") as run,
            contextlib.redirect_stderr(io.StringIO()) as stderr,
        ):
            self.assertEqual(FIGURES.main(["a.diagramplay", "demo.tape"]), 1)
        self.assertIn("vhs not found", stderr.getvalue())
        run.assert_not_called()

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
            self.assertEqual(FIGURES.main(["invalid.diagramplay"]), 1)
        self.assertEqual(run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
