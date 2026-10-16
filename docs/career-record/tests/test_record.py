"""career-record: 경력 원본 구조 검사, 추가·병합·10줄 초과, 모드 규칙, 위치 찾기, 위치 거부, career 문서 생성 흐름.

실제 Vault는 쓰지 않는다. 모든 시험은 임시 폴더의 합성 Vault와 합성 설정 폴더만 사용
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
REPO = SKILL.parents[1]
SCRIPT = SKILL / "scripts" / "record.py"
CAREER = REPO / "docs" / "career"
sys.path.insert(0, str(SKILL / "scripts"))
sys.path.insert(0, str(CAREER / "scripts"))

import record  # noqa: E402
import versions  # noqa: E402

try:
    import typst  # noqa: F401

    HAS_TYPST = True
except ImportError:
    HAS_TYPST = shutil.which("typst") is not None

BASE_LINE = {
    "주체": "본인(워커 구현), 팀 4명",
    "상황": "하루 한 번 도는 배치라 정산 완료까지 6시간",
    "행동": "Kafka로 주문 이벤트를 받아 정산하는 워커 구현",
    "확인": "운영 2주 관찰",
    "결과": "6시간 → 30분(1차)",
    "상태": "진행 중",
}
FIRST = "정산 배치를 주문 이벤트 처리로 전환"
BUNDLE = f"""## {FIRST}

### 맡은 일
주문 이벤트를 받아 정산 행을 만드는 워커를 맡았다.

### 해결한 문제
배치가 끝나기 전에는 가게가 정산 금액을 볼 수 없었다.

### 설계 결정
배치 주기를 1시간으로 줄이는 안은 DB 부하가 24배라 버렸다. 이벤트를 받는 워커를 골랐다.

### 구현
주문 완료 이벤트마다 정산 행을 만들고, 같은 이벤트가 두 번 와도 한 번만 반영한다.

### 결과
정산 대기 시간이 줄었다.

### 남은 과제
환불 이벤트는 아직 배치로 처리한다.
"""


class SyntheticVault(unittest.TestCase):
    """임시 Vault: 회사(+팀), 교육, 개인. 설정 폴더도 임시"""

    def setUp(self) -> None:
        self.temp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.temp)
        self.vault = self.temp / "vault"
        self.root = self.vault / "career"
        self.config = self.temp / "config"
        self.config.mkdir()
        self.env = {**os.environ, "WOON_KNOWLEDGE_ROOT": str(self.vault), "WORK_CONTINUITY_CONFIG_DIR": str(self.config)}
        self.old_env = {key: os.environ.get(key) for key in ("WOON_KNOWLEDGE_ROOT", "WORK_CONTINUITY_CONFIG_DIR")}
        os.environ.update({key: self.env[key] for key in self.old_env})
        self.addCleanup(self.restore_env)
        self.root.mkdir(parents=True)
        (self.root / "master.md").write_text("# 기본\n이름: 홍길동\n\n# 기술\n- Kafka: 실무\n\n# 기타\n- 정보처리기사, 2022\n", encoding="utf-8")
        self.org("예시페이", "재직")
        self.org("부트캠프", "교육")
        self.org("개인", "개인")
        (self.root / "예시페이" / "정산팀").mkdir()
        (self.root / "예시페이" / "정산팀" / "팀.md").write_text("---\n기간: 2024.01 - 현재\n역할: 백엔드\n---\n", encoding="utf-8")
        self.cli("new-project", "예시페이/정산팀/정산-이벤트-전환", "--set", "기간=2025.03 - 2025.09", "--set", "인원=4",
                 "--set", "역할=백엔드", "--set", "공개=비공개", "--set", "저장소=https://github.com/examplepay/settlement",
                 "--set", "기술=Kafka, Java")
        self.cli("new-project", "부트캠프/미니-db", "--set", "저장소=git@github.com:me/mini-db.git")
        self.cli("new-project", "개인/블로그", "--set", "저장소=https://github.com/me/blog")

    def restore_env(self) -> None:
        for key, value in self.old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def org(self, name: str, kind: str) -> None:
        (self.root / name).mkdir()
        (self.root / name / "소속.md").write_text(f"---\n구분: {kind}\n기간: 2023.01 - 현재\n역할 변화: 미확인\n근거: 미확인\n---\n", encoding="utf-8")

    def cli(self, *args: str, code: int = 0) -> dict:
        run = subprocess.run([sys.executable, str(SCRIPT), *args], env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, code, run.stdout + run.stderr)
        return json.loads(run.stdout)

    def sets(self, values: dict) -> list[str]:
        return [part for key, value in values.items() for part in ("--set", f"{key}={value}")]

    def resume(self, project: str) -> str:
        return (self.root / project / "이력서.md").read_text(encoding="utf-8")

    def lines(self, project: str) -> list[dict]:
        return record.Project(self.root / project, self.root).lines

    def snapshot(self) -> dict:
        return {str(path): path.read_bytes() for path in self.vault.rglob("*") if path.is_file()}


class StructureTest(SyntheticVault):
    def test_synthetic_vault_passes_check(self) -> None:
        self.cli("mode", "bypass")
        self.cli("add", "예시페이/정산팀/정산-이벤트-전환", "--first", FIRST, *self.sets(BASE_LINE), "--pr", "https://github.com/examplepay/settlement/pull/12")
        (self.root / "예시페이/정산팀/정산-이벤트-전환/포트폴리오.md").write_text(BUNDLE, encoding="utf-8")
        self.assertEqual(self.cli("check")["problems"], [])

    def test_line_has_eight_fields_in_order_and_first_line_alone_is_saved(self) -> None:
        self.cli("mode", "bypass")
        self.cli("add", "개인/블로그", "--first", "글 목록 첫 화면 속도 개선")
        text = self.resume("개인/블로그")
        keys = re.findall(r"^  - ([^:]+):", text.split("\n---\n", 1)[1], re.M)
        self.assertEqual(keys, list(record.FIELDS))
        self.assertIn("  - 결과: 미확인", text)
        self.assertIn("  - 등급: 하", text)

    def test_orphan_bundle_and_wrong_sections_are_reported(self) -> None:
        self.cli("mode", "bypass")
        self.cli("add", "개인/블로그", "--first", "글 목록 첫 화면 속도 개선")
        folder = self.root / "개인/블로그"
        (folder / "포트폴리오.md").write_text("## 다른 제목\n\n### 맡은 일\n본인\n", encoding="utf-8")
        problems = "\n".join(self.cli("check", code=1)["problems"])
        self.assertIn("짝 없는 묶음", problems)
        self.assertIn("절:", problems)

    def test_field_order_grade_and_count_violations(self) -> None:
        folder = self.root / "개인/블로그"
        fields = "\n".join(f"  - {key}: 미확인" for key in reversed(record.FIELDS))
        many = "\n".join(f"- 줄 {i}\n" + "\n".join(f"  - {key}: {'하' if key == '등급' else '미확인'}" for key in record.FIELDS) for i in range(11))
        head = (folder / "이력서.md").read_text(encoding="utf-8")
        (folder / "이력서.md").write_text(head + "\n" + many + f"\n- 순서 틀림\n{fields}\n", encoding="utf-8")
        problems = "\n".join(self.cli("check", code=1)["problems"])
        self.assertIn("줄 12개", problems)
        self.assertIn("칸 순서", problems)
        wrong = head + "\n- 등급 틀림\n" + "\n".join(f"  - {key}: {value}" for key, value in [("등급", "상"), *[(k, "미확인") for k in record.FIELDS[1:]]]) + "\n"
        (folder / "이력서.md").write_text(wrong, encoding="utf-8")
        self.assertIn("등급 상 → 계산값 하", "\n".join(self.cli("check", code=1)["problems"]))

    def test_parent_names_inside_files_are_reported(self) -> None:
        self.cli("mode", "bypass")
        self.cli("add", "예시페이/정산팀/정산-이벤트-전환", "--first", "예시페이 정산팀 배치 개선")
        problems = "\n".join(self.cli("check", code=1)["problems"])
        self.assertIn('상위 폴더 이름 "예시페이"', problems)
        self.assertIn('상위 폴더 이름 "정산팀"', problems)

    def test_old_layout_is_reported(self) -> None:
        (self.root / "cases").mkdir()
        (self.root / "master.md").write_text("# 기본\n\n# 프로젝트\n\n# 기술\n", encoding="utf-8")
        problems = "\n".join(self.cli("check", code=1)["problems"])
        self.assertIn("cases/ 폐지", problems)
        self.assertIn("master.md 절", problems)


class GradeTest(unittest.TestCase):
    def test_grade_rules(self) -> None:
        full = {**BASE_LINE, "근거": "https://github.com/a/b/pull/1"}
        self.assertEqual(record.grade(full), "상")
        self.assertEqual(record.grade({**full, "근거": "미확인"}), "중")
        self.assertEqual(record.grade({**full, "확인": "로컬 측정 3회"}), "중")
        self.assertEqual(record.grade({**full, "주체": "팀 4명"}), "중")
        self.assertEqual(record.grade({**full, "주체": "팀 4명", "근거": "미확인"}), "하")
        self.assertEqual(record.grade({**full, "결과": "미확인"}), "하")
        self.assertEqual(record.grade({**full, "주체": "참여(리뷰만)"}), "하")


class FlowTest(SyntheticVault):
    project = "예시페이/정산팀/정산-이벤트-전환"

    def test_normal_asks_before_add_and_writes_nothing(self) -> None:
        before = self.snapshot()
        result = self.cli("add", self.project, "--first", FIRST, *self.sets(BASE_LINE), "--similar", "주문 집계 배치", code=3)
        self.assertTrue(result["ask"].startswith(f"경력에 추가할까요? → {self.project}\n\"{FIRST} (6시간 → 30분(1차))\" (등급"))
        self.assertIn('비슷한 줄: "주문 집계 배치" → 병합 / 새 줄 / 건너뛰기', result["ask"])
        self.assertEqual(self.snapshot(), before)
        self.cli("add", self.project, "--first", FIRST, *self.sets(BASE_LINE), "--yes")
        self.assertEqual(self.lines(self.project)[0]["first"], FIRST)

    def test_add_merge_regrade_and_over_limit(self) -> None:
        self.cli("mode", "bypass")
        added = self.cli("add", self.project, "--first", FIRST, *self.sets(BASE_LINE))
        self.assertEqual(added["report"], [f'경력 추가: {self.project} "{FIRST}" (중)'])
        merged = self.cli("merge", self.project, "--line", FIRST, "--set", "결과=5분(2차)", "--set", "상태=완료",
                          "--set", "확인=부하 시험", "--pr", "https://github.com/examplepay/settlement/pull/15")
        self.assertEqual(merged["report"], [f'경력 병합: {self.project} "{FIRST}" (상)'])
        fields = dict(self.lines(self.project)[0]["fields"])
        self.assertEqual(fields["결과"], "6시간 → 30분(1차) → 5분(2차)")
        self.assertEqual(fields["확인"], "운영 2주 관찰, 부하 시험")
        self.assertEqual(fields["상태"], "완료")
        self.assertEqual(fields["근거"], "https://github.com/examplepay/settlement/pull/15")
        (self.root / self.project / "포트폴리오.md").write_text(BUNDLE, encoding="utf-8")
        for i in range(8):
            self.cli("add", self.project, "--first", f"하 줄 {i}")
        self.cli("add", self.project, "--first", "중 줄", "--set", "주체=본인", "--set", "결과=오류 3건 → 0건", "--set", "확인=운영 로그")
        self.assertEqual(len(self.lines(self.project)), 10)
        order = [dict(line["fields"])["등급"] for line in self.lines(self.project)]
        self.assertEqual(order, sorted(order, key=record.RANK.get))
        # 10줄: 새 줄이 가장 낮은 줄(하, 묶음 없음)보다 높으면 bypass는 바로 교체
        replaced = self.cli("add", self.project, "--first", "새 중 줄", "--set", "주체=본인", "--set", "결과=2분", "--set", "확인=운영")
        self.assertEqual(replaced["report"][0], f'경력 삭제: {self.project} "하 줄 0" (하)')
        self.assertEqual(len(self.lines(self.project)), 10)
        # 새 줄이 가장 낮은 줄보다 높지 않으면 질문, 파일 0개
        before = self.snapshot()
        self.assertIn("가장 낮은 줄", self.cli("add", self.project, "--first", "또 하 줄", code=3)["ask"])
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.cli("check")["problems"], [])

    def test_bypass_asks_before_deleting_high_or_bundled_lines(self) -> None:
        self.cli("mode", "bypass")
        self.cli("add", self.project, "--first", FIRST, *self.sets(BASE_LINE), "--pr", "https://github.com/x/y/pull/1")
        self.cli("add", self.project, "--first", "하 줄")
        (self.root / self.project / "포트폴리오.md").write_text(BUNDLE.replace(FIRST, "하 줄"), encoding="utf-8")
        self.cli("add", self.project, "--first", "묶음 없는 하 줄")
        before = self.snapshot()
        self.assertIn("등급 상", self.cli("remove", self.project, "--line", FIRST, code=3)["ask"])
        self.assertIn("포트폴리오 묶음도 함께 지움", self.cli("remove", self.project, "--line", "하 줄", code=3)["ask"])
        self.assertEqual(self.snapshot(), before)
        self.cli("remove", self.project, "--line", "묶음 없는 하 줄")
        self.cli("remove", self.project, "--line", "하 줄", "--yes")
        self.assertNotIn("## 하 줄", (self.root / self.project / "포트폴리오.md").read_text(encoding="utf-8"))
        self.assertEqual([line["first"] for line in self.lines(self.project)], [FIRST])

    def test_bypass_asks_when_several_locations(self) -> None:
        self.cli("mode", "bypass")
        self.assertIn("ask", self.cli("add", self.project, "--first", FIRST, "--locations", "2", code=3))

    def test_mode_decisions(self) -> None:
        for action in ("add", "merge", "remove"):
            self.assertEqual(record.decide("normal", action), "ask")
        self.assertEqual(record.decide("bypass", "add"), "run")
        self.assertEqual(record.decide("bypass", "merge"), "run")
        self.assertEqual(record.decide("bypass", "add", locations=3), "ask")
        self.assertEqual(record.decide("bypass", "remove", grade_value="상"), "ask")
        self.assertEqual(record.decide("bypass", "remove", grade_value="중"), "ask")
        self.assertEqual(record.decide("bypass", "remove", grade_value="하", bundle=True), "ask")
        self.assertEqual(record.decide("bypass", "remove", grade_value="하"), "run")

    def test_fill_only_answered_blanks_then_regrade(self) -> None:
        self.cli("mode", "bypass")
        self.cli("add", "개인/블로그", "--first", "글 목록 첫 화면 속도 개선")
        blanks = self.cli("blanks")["blanks"]
        self.assertTrue(blanks.startswith("채워 주세요 ("))
        self.assertIn("1. 부트캠프/미니-db - 기간: 언제부터 언제까지 했나요?", blanks)
        self.assertIn("개인/블로그 글 목록 첫 화면 속도 개선 - 결과: 전과 후가 어떻게 달라졌나요?", blanks)
        self.cli("fill", "개인/블로그", "--line", "글 목록 첫 화면 속도 개선", "--set", "결과=2.1초 → 0.4초", "--set", "주체=본인")
        fields = dict(self.lines("개인/블로그")[0]["fields"])
        self.assertEqual((fields["결과"], fields["확인"], fields["등급"]), ("2.1초 → 0.4초", "미확인", "하"))
        self.cli("fill", "개인/블로그", "--line", "글 목록 첫 화면 속도 개선", "--set", "결과=1초", code=1)

    def test_edit_state_and_first_line_moves_bundle_title(self) -> None:
        self.cli("mode", "bypass")
        self.cli("add", self.project, "--first", FIRST, *self.sets(BASE_LINE))
        (self.root / self.project / "포트폴리오.md").write_text(BUNDLE, encoding="utf-8")
        self.cli("edit", self.project, "--line", FIRST, "--set", "상태=완료", "--new-first", "정산을 주문 이벤트 처리로 전환")
        self.assertIn("## 정산을 주문 이벤트 처리로 전환", (self.root / self.project / "포트폴리오.md").read_text(encoding="utf-8"))
        self.assertEqual(self.cli("check")["problems"], [])


class LocateTest(SyntheticVault):
    def test_one_match(self) -> None:
        result = self.cli("locate", "--remote", "git@github.com:ExamplePay/settlement.git", "--author", "me")
        self.assertEqual(result, {"location": "예시페이/정산팀/정산-이벤트-전환", "personal": False})

    def test_several_matches_ask(self) -> None:
        self.cli("new-project", "예시페이/정산팀/정산-대사", "--set", "저장소=https://github.com/examplepay/settlement")
        result = self.cli("locate", "--remote", "https://github.com/examplepay/settlement")
        self.assertEqual(sorted(result["candidates"]), ["예시페이/정산팀/정산-대사", "예시페이/정산팀/정산-이벤트-전환"])
        self.assertTrue(result["ask"].startswith("어느 프로젝트에 넣을까요?"))

    def test_no_match_offers_recent_three_and_new_project(self) -> None:
        self.cli("new-project", "예시페이/정산-도구")
        result = self.cli("locate", "--remote", "https://github.com/examplepay/unknown")
        self.assertEqual(len(result["candidates"]), 4)
        self.assertEqual(result["candidates"][-1], "새 프로젝트(소속 선택)")

    def test_personal_repo_defaults_to_personal_folder(self) -> None:
        result = self.cli("locate", "--remote", "https://github.com/me/new-tool", "--author", "Me")
        self.assertTrue(result["personal"])
        self.assertEqual(result["candidates"][0], "개인/new-tool (새 프로젝트)")


class ScreenTest(unittest.TestCase):
    def test_condition_met_goes_to_judgement(self) -> None:
        pr = {"author": {"login": "me"}, "title": "perf(settle): 재처리 도구", "url": "https://github.com/me/x/pull/3",
              "files": [{"path": "src/retry.py"}, {"path": "tests/test_retry.py"}]}
        result = record.screen(pr, "me")
        self.assertIn("judge", result)
        self.assertTrue(result["tests_changed"])

    def test_excluded_prs(self) -> None:
        cases = [
            ({"author": {"login": "other"}, "title": "feat: x", "files": [{"path": "a.py"}]}, "사용자 계정"),
            ({"author": {"login": "me"}, "title": "docs: 오타", "files": [{"path": "a.py"}]}, "문서·포맷"),
            ({"author": {"login": "me"}, "title": "style: 포맷", "files": [{"path": "a.py"}]}, "문서·포맷"),
            ({"author": {"login": "me"}, "title": "feat: 안내", "files": [{"path": "README.md"}, {"path": "docs/a.png"}]}, "문서만"),
            ({"author": {"login": "me"}, "title": "chore: 올림", "files": [{"path": "package.json"}, {"path": "package-lock.json"}]}, "의존성"),
        ]
        for pr, reason in cases:
            self.assertIn(reason, record.screen(pr, "me").get("skip", ""), pr)


class LocationGuardTest(SyntheticVault):
    def test_unregistered_vault_writes_zero_files(self) -> None:
        env = {key: value for key, value in self.env.items() if key != "WOON_KNOWLEDGE_ROOT"}
        before = self.snapshot()
        run = subprocess.run([sys.executable, str(SCRIPT), "new-project", "개인/x"], env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 1)
        self.assertIn("Vault 미등록", json.loads(run.stdout)["error"])
        self.assertEqual(self.snapshot(), before)

    def test_outside_vault_writes_zero_files(self) -> None:
        outside = self.temp / "outside" / "proj"
        outside.mkdir(parents=True)
        (outside / "이력서.md").write_text("---\n---\n", encoding="utf-8")
        before = self.snapshot()
        for args in (("add", str(outside), "--first", "x", "--yes"), ("new-project", "../outside/new"), ("new-project", "2026-11-30-회사-직군/x")):
            result = self.cli(*args, code=1)
            self.assertEqual(result["files"], [])
        self.assertEqual(self.snapshot(), before)
        self.assertEqual((outside / "이력서.md").read_text(encoding="utf-8"), "---\n---\n")

    def test_backfill_time_is_stored_in_config(self) -> None:
        self.assertIsNone(self.cli("since")["last_recorded"])
        self.cli("stamp", "--at", "2026-10-01T00:00:00+00:00")
        self.assertEqual(self.cli("since")["last_recorded"], "2026-10-01T00:00:00+00:00")
        self.assertEqual(json.loads((self.config / "career-record.json").read_text(encoding="utf-8"))["mode"], "normal")


class CareerBuildTest(SyntheticVault):
    """원본에서 career 공고 폴더(#103 구조)를 만들고 versions.py check·Typst 컴파일까지"""

    def test_resume_and_portfolio_from_source(self) -> None:
        project = "예시페이/정산팀/정산-이벤트-전환"
        self.cli("mode", "bypass")
        self.cli("add", project, "--first", FIRST, *self.sets(BASE_LINE), "--pr", "https://github.com/examplepay/settlement/pull/12")
        self.cli("merge", project, "--line", FIRST, "--set", "결과=5분(2차)", "--set", "상태=완료")
        folder = self.root / project
        (folder / "포트폴리오.md").write_text(BUNDLE, encoding="utf-8")
        (folder / "figures").mkdir()
        shutil.copy(REPO / "docs" / "assets" / "skill-quality-light.svg", folder / "figures" / "흐름.svg")
        self.assertEqual(self.cli("check")["problems"], [])

        posting = self.root / "2026-11-30-합성-백엔드-개발자"
        for name in ("이력서", "포트폴리오", "figures"):
            (posting / name).mkdir(parents=True)
        (posting / "jd.md").write_text("# 합성 JD\n", encoding="utf-8")
        (posting / "전략.md").write_text("# 공고 분석\n\n# 구성 계획\n\n# 작성\n\n# 확인\n", encoding="utf-8")
        shutil.copy(CAREER / "assets" / "typst" / "career.typ", posting / "career.typ")
        shutil.copy(folder / "figures" / "흐름.svg", posting / "figures" / "흐름.svg")

        source = record.Project(folder, self.root)
        line = source.lines[0]
        fields = dict(line["fields"])
        attributes = source.attributes
        # 양식 대응: 이력서 한 줄 = 줄 첫 줄 + 결과, 포트폴리오 사례 = 짝 묶음
        item = f"{line['first']} ({fields['결과']})"
        (posting / "이력서" / "이력서.typ").write_text(
            '#import "/career.typ": *\n'
            '#let profile = (name: "홍길동", contacts: ())\n'
            '#show: resume-page.with(profile: profile, photo: none, intro: [정산 백엔드 개발자])\n'
            "#section[Projects]\n"
            f"#entry([정산 이벤트 전환 ({attributes['인원']}) [{attributes['역할']}]], meta: ([예시페이],), period: [{attributes['기간']}],\n"
            f"  what: [주문 이벤트 정산], items: ([{item}],), stack: [{', '.join(attributes['기술'])}])\n",
            encoding="utf-8",
        )
        bundle = record.parse_bundles(source.portfolio)[0]
        self.assertEqual(bundle["title"], line["first"])
        body = "\n".join(bundle["lines"])
        part = lambda name: body.split(f"### {name}\n", 1)[1].split("\n###", 1)[0].strip()  # noqa: E731
        (posting / "포트폴리오" / "포트폴리오.typ").write_text(
            '#import "/career.typ": *\n#show: portfolio-page\n'
            f"#case([{bundle['title']}], [{part('맡은 일')}])\n"
            f'#facts((("기간", [{attributes["기간"]}]), ("검증", [{fields["확인"]}])))\n'
            f"#part[문제 정의 및 기술적 제약]\n{part('해결한 문제')}\n"
            f"#part[기술적 의사결정 및 아키텍처]\n{part('설계 결정')}\n"
            '#diagram("/figures/흐름.svg", [이벤트 워커 흐름])\n'
            f"#part[구현 및 해결 과정]\n{part('구현')}\n"
            f"#part[성과 및 배운 점]\n{fields['결과']}. {part('남은 과제')}\n",
            encoding="utf-8",
        )
        self.assertEqual(versions.check(posting), [])
        self.assertEqual(self.cli("check")["problems"], [], "공고 폴더는 원본 검사 대상 아님")
        if not HAS_TYPST:
            self.skipTest("typst 없음")
        for document in ("이력서", "포트폴리오"):
            pdf = versions.compile_pdf(posting / document / f"{document}.typ", posting)
            self.assertGreater(pdf.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()


class StdinScreenTest(unittest.TestCase):
    def test_screen_reads_pr_json_from_stdin(self) -> None:
        pr = '{"author":{"login":"me"},"title":"docs: 오타","files":[{"path":"README.md"}],"url":"u"}'
        done = subprocess.run([sys.executable, str(SCRIPT), "screen", "-", "--user", "me"], input=pr, capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("skip", json.loads(done.stdout))
