"""이슈 #6의 수정 전후 제목과 게시 전 CLI 계약을 검증한다."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import issue_title  # noqa: E402


@pytest.mark.parametrize(
    ("kind", "before", "after"),
    [
        ("design", "연결이 끊긴 요청을 다시 보낼지", "끊긴 요청 재전송 정책 결정"),
        ("build", "토큰 재발급 도입", "토큰 재발급 추가"),
        (
            "bug",
            "재연결 뒤 대기 요청이 두 번 전송되는 문제",
            "대기 요청 재연결 뒤 중복 전송 수정",
        ),
        (
            "experiment",
            "한국어 입력의 분류 오류율과 재시도 횟수 및 응답 시간 측정",
            "한국어 입력 분류 오류율 측정",
        ),
        ("docs", "설치 방법 갱신", "설치 방법 문서 갱신"),
    ],
)
def test_old_title_fails_and_revised_title_passes(
    kind: str, before: str, after: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    for title, expected in ((before, 1), (after, 0)):
        monkeypatch.setattr(sys, "stdin", io.StringIO(title))
        assert issue_title.main(["--kind", kind]) == expected


@pytest.mark.parametrize("ending", ["추가", "구현", "변경"])
def test_build_endings_pass(ending: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(f"토큰 재발급 {ending}\n"))
    assert issue_title.main(["--kind", "build", "-"]) == 0


@pytest.mark.parametrize("length,expected", [(20, 0), (21, 1)])
@pytest.mark.parametrize("character", ["가", "𐐀"])
def test_length_counts_unicode_characters_and_spaces(
    character: str,
    length: int,
    expected: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    title = character * (length - 3) + " 결정"
    monkeypatch.setattr(sys, "stdin", io.StringIO(title + "\r\n"))
    assert issue_title.main(["--kind", "design"]) == expected


@pytest.mark.parametrize(
    "title",
    ["", "   ", "결정", " 결정", "대상 변경", "대상 결정\n다른 제목", "대상 결정\n\n"],
)
def test_invalid_title_reports_violation(
    title: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(title))
    assert issue_title.main(["--kind", "design"]) == 1
    result = capsys.readouterr()
    assert result.out.startswith("1: ")
    assert result.err == ""


def test_utf8_file_passes_without_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def read_title(self: Path, *, encoding: str) -> str:
        assert self == Path("title.txt")
        assert encoding == "utf-8"
        return "설치 방법 문서 갱신\n"

    monkeypatch.setattr(Path, "read_text", read_title)
    assert issue_title.main(["--kind", "docs", "title.txt"]) == 0
    result = capsys.readouterr()
    assert result.out == result.err == ""


@pytest.mark.parametrize(
    "error", [OSError("read failed"), UnicodeError("invalid utf-8")]
)
def test_file_error_returns_input_error(
    error: Exception,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_read(self: Path, *, encoding: str) -> str:
        raise error

    monkeypatch.setattr(Path, "read_text", fail_read)
    assert issue_title.main(["--kind", "docs", "title.txt"]) == 2
    result = capsys.readouterr()
    assert result.out == ""
    assert "issue title check failed:" in result.err


@pytest.mark.parametrize("args", [[], ["--kind", "unknown"]])
def test_invalid_arguments_return_input_error(args: list[str]) -> None:
    with pytest.raises(SystemExit) as error:
        issue_title.main(args)
    assert error.value.code == 2
