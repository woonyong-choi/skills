import hashlib
import importlib
import json
import shutil
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


@pytest.fixture
def deploy(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(SCRIPTS))
    return importlib.import_module("deploy")


@pytest.fixture
def skill(tmp_path: Path) -> Path:
    path = tmp_path / "example"
    path.mkdir()
    (path / "extra.txt").write_text("해시 보존", encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("encoded", "expected"),
    [
        ("한글 설명을 쓴다.", "한글 설명을 쓴다."),
        (r'한글 \"인용\"을 쓴다.', '한글 "인용"을 쓴다.'),
        (r"경로 \\ 및 \/를 쓴다.", "경로 \\ 및 /를 쓴다."),
        (r"문자 \\n과 개행 \n을 가른다.", "문자 \\n과 개행 \n을 가른다."),
        ("글자 \\" + "\t 보존", "글자 \t 보존"),
        (r"\0\a\b\t\n\v\f\r\e\ \"\/\\\N\_\L\P", '\0\a\b\t\n\v\f\r\x1b "/\\\x85\xa0\u2028\u2029'),
        (r"한글 \x41\uD55c\U0001F642\x00\uFFFF\U0010FFFF", "한글 A한🙂\0\uffff\U0010ffff"),
        (r"이모지 \uD83D\uDE42를 쓴다.", "이모지 🙂를 쓴다."),
        (r"경계 \uD800\uDC00\uDBFF\uDFFF", "경계 \U00010000\U0010ffff"),
        (r"소문자 \ud83d\ude42", "소문자 🙂"),
        (r"\\uD800과 \\q는 문자다.", r"\uD800과 \q는 문자다."),
    ],
)
def test_source_record_yaml_description_preserves_metadata(
    deploy: ModuleType, skill: Path, encoded: str, expected: str
) -> None:
    content = f'---\nname: example\ndescription: "{encoded}"\n---\n본문\n'.encode()
    (skill / "SKILL.md").write_bytes(content)
    source_hash = deploy.install.tree_hash(skill)
    dist = skill.parent / "dist"

    record = deploy.source_record(skill, dist)

    assert record == {
        "name": "example",
        "description": expected,
        "sourceHash": source_hash,
        "skillHash": hashlib.sha256(content).hexdigest(),
        "path": str(dist / "example.zip"),
    }


@pytest.mark.parametrize(
    "encoded",
    [r"\q", "끝\\", r"\x", r"\x0", r"\xGG", r"\u123", r"\u12+3",
     r"\U0000000", r"\U00110000", r"\uD800", r"\uDFFF", r"\U0000D800",
     r"\uD83D\u0041", r"\uD83D\uDE4G", r"\uD83D\U0000DE42"],
)
def test_source_record_invalid_yaml_escape_raises_value_error(
    deploy: ModuleType, skill: Path, encoded: str
) -> None:
    (skill / "SKILL.md").write_text(
        f'---\nname: example\ndescription: "{encoded}"\n---\n', encoding="utf-8"
    )

    with pytest.raises(ValueError, match="invalid description.*example"):
        deploy.source_record(skill, skill.parent / "dist")


@pytest.mark.skipif(shutil.which("node") is None, reason="node is unavailable")
@pytest.mark.parametrize("mismatch", [False, True])
def test_source_record_account_verification_uses_decoded_description(
    deploy: ModuleType, skill: Path, mismatch: bool
) -> None:
    (skill / "SKILL.md").write_text(
        '---\nname: example\ndescription: "한글 \\"인용\\"을 쓴다."\n---\n',
        encoding="utf-8",
    )
    record = deploy.source_record(skill, skill.parent / "dist")
    script = r'''
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const { syncAccount, planAccount } = await import(process.argv[1]);
const { record, mismatch } = JSON.parse(readFileSync(0, "utf8"));
const description = mismatch ? "다른 설명" : '한글 "인용"을 쓴다.';
let present = [{ name: record.name, description, updatedAt: "before" }];
const receipt = { version: 1, skills: {} };
let saves = 0;
const account = {
  list: async () => present,
  upload: async () => { present = [{ name: record.name, description, updatedAt: "after" }]; },
};
const sync = () => syncAccount([record], account, receipt, () => { saves++; }, false);
if (mismatch) {
  await assert.rejects(sync, /account verification failed: example/);
  assert.equal(receipt.skills.example, undefined);
} else {
  await sync();
  assert.deepEqual(planAccount([record], present, receipt), []);
  assert.equal(receipt.skills.example.description, description);
  assert.equal(saves, 2);
}
'''

    result = subprocess.run(
        ["node", "--input-type=module", "-e", script, (SCRIPTS / "claude_upload.mjs").as_uri()],
        input=json.dumps({"record": record, "mismatch": mismatch}),
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0, result.stdout + result.stderr
