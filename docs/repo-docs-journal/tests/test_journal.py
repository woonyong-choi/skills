"""repo-docs-journal: 기록 기준 세 칸, 저장 경로·이름 규칙, 위치 거부, 기록 형식, 원칙, 모드.

실제 Vault는 쓰지 않는다. 임시 폴더의 합성 Vault·합성 프로젝트·합성 설정 폴더만 사용
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SKILL = Path(__file__).resolve().parents[1]
REPO = SKILL.parents[1]
SCRIPT = SKILL / "scripts" / "journal.py"
sys.path.insert(0, str(SKILL / "scripts"))
sys.path.insert(0, str(REPO / "git" / "git-issue" / "scripts"))

import document_guard  # noqa: E402
import journal  # noqa: E402
import project_context  # noqa: E402

# 오늘 실제로 있었던 세 판단을 합성 근거로 재현
VAULT_SOURCE = """html-report 저장 위치를 Vault로 통일
- 저장소 .local/reports에 두는 안은 쓰기 훅이 report.md만 막고 index.html은 통과해 원문 없는 반쪽 상태가 생겨 버림
- 프로젝트 무관 보고서는 legacy 아래면 충분하다고 보고 별도 폴더는 만들지 않음
- 위치: 등록 프로젝트는 worktree/<프로젝트>/docs/보고서, 프로젝트 무관은 legacy/보고서
"""
COLOR_SOURCE = """변경 표시 색
- 노랑 배경은 인쇄하면 흐려서 버리고 초록·파랑·빨강으로 결정
"""
LUNA_SOURCE = """Codex 읽기 검토 모델
- codex exec --model gpt-6-luna "1+1은?" 실행 결과 종료 0, 답 2
- 실행으로 확인했으므로 상수 gpt-6-luna 유지, 다른 이름 후보는 버림
"""


class ScreenTest(unittest.TestCase):
    def test_vault_location_decision_is_recorded(self) -> None:
        result = journal.screen(
            [VAULT_SOURCE],
            "저장소 .local/reports에 두는 안은 쓰기 훅이 report.md만 막고 index.html은 통과해 원문 없는 반쪽 상태가 생겨 버림",
            "프로젝트 무관 보고서는 legacy 아래면 충분하다고 보고 별도 폴더는 만들지 않음",
            "저장 위치",
        )
        self.assertTrue(result["pass"], result)
        self.assertEqual(result["criteria"]["구조"], "저장 위치")

    def test_change_mark_color_is_rejected(self) -> None:
        result = journal.screen([COLOR_SOURCE], "노랑 배경은 인쇄하면 흐려서 버리고 초록·파랑·빨강으로 결정", "", "화면 값")
        self.assertFalse(result["pass"])
        self.assertIn("가정 문장 없음", result["reason"])
        self.assertIn("구조 목록 밖: 화면 값", result["reason"])

    def test_luna_model_constant_is_rejected(self) -> None:
        result = journal.screen(
            [LUNA_SOURCE],
            "다른 이름 후보는 버림",
            "실행으로 확인했으므로 상수 gpt-6-luna 유지",
            "실행으로 확인 끝난 설정 값",
        )
        self.assertFalse(result["pass"])
        self.assertTrue(result["reason"].startswith("기록 기준 미충족: "))
        self.assertIn("가정 문장 없음", result["reason"])
        self.assertIn("구조 목록 밖", result["reason"])

    def test_quotes_must_exist_in_sources(self) -> None:
        result = journal.screen([VAULT_SOURCE], "지어낸 대안 문장", "아마 괜찮을 것", "저장 위치")
        self.assertIn("대안 인용이 근거 원문에 없음", result["reason"])
        self.assertIn("가정 인용이 근거 원문에 없음", result["reason"])

    def test_cli_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "근거.txt"
            source.write_text(COLOR_SOURCE, encoding="utf-8")
            run = subprocess.run([sys.executable, str(SCRIPT), "screen", "--source", str(source), "--structure", "화면 값"], capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 1)
            self.assertIn("기록 기준 미충족", json.loads(run.stdout)["reason"])


class SyntheticVault(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.vault = self.root / "vault"
        self.vault.mkdir()
        self.config = self.root / "config"
        patcher = mock.patch.dict(os.environ, {"WOON_KNOWLEDGE_ROOT": str(self.vault), "WORK_CONTINUITY_CONFIG_DIR": str(self.config)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.outside = self.root / "outside"
        self.outside.mkdir()

    def files(self) -> list[Path]:
        return sorted(path for path in self.root.rglob("*") if path.is_file() and self.config not in path.parents)

    def project(self) -> tuple[Path, Path]:
        origin, project = self.root / "origin.git", self.root / "catalog"
        for args, cwd in ((["init", "-q", "--bare", str(origin)], self.root), (["init", "-q", str(project)], self.root), (["remote", "add", "origin", "../origin.git"], project)):
            subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, timeout=15)
        import project_registration

        with mock.patch.dict(os.environ, {"WOON_KNOWLEDGE_ROOT": ""}):
            project_context.register_vault(self.vault)
            project_registration.register_project(project, None, False)
        return project, Path(project_context.check_project(project)["area"])


class PathTest(SyntheticVault):
    def test_unrelated_record_goes_to_legacy(self) -> None:
        result = journal.target("판단", "보고서 위치 Vault 통일", "2026-10-16", self.outside)
        self.assertEqual(Path(result["path"]), (self.vault / "legacy" / "판단" / "2026-10-16-보고서-위치-Vault-통일.md").resolve())
        self.assertEqual(Path(result["principles"]), self.vault.resolve() / "principles.md")
        log = journal.target("작업 일지", "판단 기록 개편", "2026-10-16", self.outside)
        self.assertEqual(Path(log["path"]).parent.name, "작업일지")
        self.assertEqual(Path(journal.target("판단 변경", "보고서 위치 다시 정함", "2026-10-17", None)["path"]).parent.name, "판단")

    def test_registered_project_goes_to_area_docs(self) -> None:
        project, area = self.project()
        result = journal.target("판단", "보고서 위치 Vault 통일", "2026-10-16", project)
        self.assertEqual(Path(result["path"]), (area / "docs" / "판단" / "2026-10-16-보고서-위치-Vault-통일.md").resolve())
        self.assertEqual(result["scope"], "project")

    def test_name_rule(self) -> None:
        for topic in ("report location", "보고서", "보고서 위치 저장 방식 Vault 통일 결정", "보고서/위치 통일"):
            with self.assertRaises(journal.JournalError, msg=topic):
                journal.target("판단", topic, "2026-10-16", None)
        with self.assertRaises(journal.JournalError):
            journal.target("서사", "판단 기록 개편", "2026-10-16", None)

    def test_unregistered_vault_writes_zero_files(self) -> None:
        before = self.files()
        env = {**os.environ, "WOON_KNOWLEDGE_ROOT": ""}
        run = subprocess.run([sys.executable, str(SCRIPT), "path", "--kind", "판단", "--topic", "보고서 위치 통일"], env=env, capture_output=True, text=True, timeout=30, cwd=self.outside)
        self.assertEqual(run.returncode, 1)
        self.assertIn("Vault 미등록", json.loads(run.stdout)["error"])
        self.assertEqual(self.files(), before)

    def test_document_guard_allows_only_vault_principles_outside_areas(self) -> None:
        allowed = document_guard.check_tool({"tool_name": "Write", "cwd": str(self.outside), "tool_input": {"file_path": str(self.vault / "principles.md")}})
        self.assertEqual(allowed, {})
        denied = document_guard.check_tool({"tool_name": "Write", "cwd": str(self.outside), "tool_input": {"file_path": str(self.vault / "다른-문서.md")}})
        self.assertEqual(denied["hookSpecificOutput"]["permissionDecision"], "deny")


DECISION = """---
날짜: 2026-10-16
종류: 판단
관련:
  - https://github.com/owner/repo/pull/105
---

# 보고서는 Vault에만 저장

## 기록 기준

- 대안: "저장소 .local/reports에 두는 안은 버림" (PR)
- 가정: "legacy 아래면 충분하다고 보고" (PR)
- 구조: 저장 위치
"""
REVISION = """---
날짜: 2026-10-20
종류: 판단 변경
이전 판단: "[[2026-10-16-보고서-위치-Vault-통일]]"
관련:
  - https://github.com/owner/repo/pull/120
---

# 보고서를 프로젝트별로 나눔

## 놓친 것

| 분류 | 원인 | 당시 신호 |
|---|---|---|
| 범위 착오 | 프로젝트 무관 보고서 수를 세지 않음 | 없음 |

## 교훈

보고서 수를 먼저 센다
"""


class CheckTest(SyntheticVault):
    def write(self, relative: str, text: str) -> Path:
        path = self.vault / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_valid_records_and_misses(self) -> None:
        self.write("legacy/판단/2026-10-16-보고서-위치-Vault-통일.md", DECISION)
        self.write("legacy/판단/2026-10-20-보고서-프로젝트별-분리.md", REVISION)
        code, result = journal.run(["check"])
        self.assertEqual((code, result["problems"]), (0, []))
        self.assertEqual(journal.run(["misses"])[1]["rows"], [{"분류": "범위 착오", "원인": "프로젝트 무관 보고서 수를 세지 않음", "기록": "2026-10-20-보고서-프로젝트별-분리"}])

    def test_old_format_and_names_are_reported(self) -> None:
        old = "# 옛 판단\n\n| 항목 | 값 |\n|---|---|\n| 날짜 | 2026-10-16 |\n\n## 판단\n\n| 확인한 근거 | 남은 가정 |\n|---|---|\n\n서사 링크\n"
        path = self.write("legacy/판단/2026-10-16-report-location.md", old)
        problems = "\n".join(journal.check_record(path))
        for expected in ("한국어", "속성 날짜 없음", "| 항목 | 값 |", "확인한 근거 | 남은 가정", "서사 → 작업 일지"):
            self.assertIn(expected, problems)
        broken = self.write("legacy/판단/2026-10-21-이전-판단-없는-변경.md", REVISION.replace("2026-10-20", "2026-10-21"))
        self.assertIn("파일 없음", "\n".join(journal.check_record(broken)))
        misplaced = self.write("legacy/작업일지/2026-10-16-보고서-위치-Vault-통일.md", DECISION)
        self.assertIn("판단/ 폴더", "\n".join(journal.check_record(misplaced)))

    def test_principles_need_second_occurrence_and_order(self) -> None:
        path = self.write("principles.md", "# 원칙\n\n## 한 번 나온 교훈\n\n- [[a]]\n\n## 두 번 나온 교훈\n\n- [[b]]\n- [[c]]\n")
        problems = "\n".join(journal.check_principles(path))
        self.assertIn("링크 1개", problems)
        self.assertIn("내림차순", problems)
        path.write_text("# 원칙\n\n## 세 번\n\n- [[a]]\n- [[b]]\n- [[c]]\n\n## 두 번\n\n- [[d]]\n- [[e]]\n", encoding="utf-8")
        self.assertEqual(journal.check_principles(path), [])

    def test_mode(self) -> None:
        self.assertEqual(journal.config()["mode"], "normal")
        self.assertEqual(journal.run(["mode", "bypass"])[1], {"mode": "bypass"})
        self.assertEqual(json.loads((self.config / "journal.json").read_text(encoding="utf-8"))["mode"], "bypass")


if __name__ == "__main__":
    unittest.main()
