"""render_figures의 녹화 실행 위치 검증."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "render_figures.py"


class TapeWorkingDirectoryTest(unittest.TestCase):
    # cost: time O(1), heap O(1), stack O(1), io O(1)
    # vars: 없음
    # basis: estimate
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

    # cost: time O(1), heap O(1), stack O(1), io O(1)
    # vars: 없음
    # basis: estimate
    def tearDown(self) -> None:
        self.directory.cleanup()

    # cost: time O(1) + 자식 프로세스 시간, heap O(1), stack O(1), io O(1)
    # vars: 없음
    # basis: estimate
    def run_script(self, *arguments: str, cwd: Path) -> None:
        environment = {**os.environ, "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}"}
        completed = subprocess.run([sys.executable, str(SCRIPT), *arguments], cwd=cwd, env=environment, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    # cost: time O(1) + 자식 프로세스 시간, heap O(1), stack O(1), io O(1)
    # vars: 없음
    # basis: estimate
    # #64: 하위 폴더에서 찾은 녹화의 루트 기준 Output이 하위 폴더로 빠지는 회귀
    def test_discovered_tape_runs_from_repository_root(self) -> None:
        self.run_script(cwd=self.root / "sub")
        self.assertEqual(self.log.read_text(encoding="utf-8").split(), [str(self.root), "docs/assets/demo.tape"])

    # cost: time O(1) + 자식 프로세스 시간, heap O(1), stack O(1), io O(1)
    # vars: 없음
    # basis: estimate
    def test_explicit_tape_keeps_current_directory(self) -> None:
        self.run_script("../docs/assets/demo.tape", cwd=self.root / "sub")
        self.assertEqual(self.log.read_text(encoding="utf-8").split(), [str(self.root / "sub"), "../docs/assets/demo.tape"])


if __name__ == "__main__":
    unittest.main()
