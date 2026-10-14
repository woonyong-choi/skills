"""제공된 조건과 후보의 계산·비교·근거 누락을 검사한다.

인자: UTF-8 JSON 파일 하나, 생략 또는 - 는 stdin. --help는 계약과 예시.
requirements: 이름별 {source, limit, operator, unit, scope}.
candidates: 후보 이름별 {조건 이름: {value, unit, scope, evidence, certainty, claim?}}.
limit/value: 십진수 사칙연산 문자열 또는 bool, 미확인 value는 null.
operator: <=, >=, ==. bool은 ==만. certainty: known, estimated, unknown.
claim: 선택 필드, pass/fail/unknown 중 주장한 판정.
출력: stdout JSON. 계산 완료 0, 주장 불일치 1, 잘못된 입력 2.
종료 0은 후보 채택·원문 해석·근거 진위 통과를 뜻하지 않는다.
입력 1MiB, 이름 128자, 조건×후보 1,000개, 식 512자·64개 노드는
검사기 자원 한도다. 초과하면 입력을 나눠 검사하며 조건을 생략하지 않는다.

적용·판정:
- 실행자가 원문에서 requirements·candidates 작성, 사용자에게 양식 작성 요구 금지.
  원문·단위·시점/환경을 입력과 대조; 없는 값을 만들거나 조건 생략 금지.
- 출력의 후보별 status와 개별 comparison 구분. estimated는 수치 비교가 맞아도
  status=unknown, 단위·범위 불일치와 근거 누락도 unknown.
  알려진 필수 조건 하나의 fail은 후보 전체 fail.
- 종료 0은 입력 처리 성공, 1은 claim과 계산 판정 불일치, 2는 입력 오류.
  0을 후보 전체 통과로 해석 금지. 오류 위치만 수정 후 재실행,
  미확인은 확인 방법·조건부 추천으로 유지.
- 식은 십진수 사칙연산·괄호만, 같은 단위·범위끼리 비교.
  환율·단위 변환·반올림·백분위 분해의 의미는 검사기 밖에서 원계약 확인.
- 검사 범위는 제공된 입력뿐. 근거 문자열 존재는 근거의 진위·적합성 증명 아님.
  전체 후보 pass도 누락된 요구·실제 동작·운영 보장 증명 아님.

예시:
{"requirements":{"memory":{"source":"peak memory <= 100 MiB","limit":"100",
"operator":"<=","unit":"MiB","scope":"process peak"}},
"candidates":{"buffered":{"memory":{"value":"20*6","unit":"MiB",
"scope":"process peak","evidence":"measured buffers","certainty":"known"}}}}
"""

from __future__ import annotations

__all__ = ["main"]

import argparse
import ast
import json
import logging
import operator
import re
import sys
from fractions import Fraction
from pathlib import Path
from typing import Callable, Final, cast

MAX_INPUT_BYTES: Final = 1024 * 1024
MAX_NAME_CHARS: Final = 128
MAX_COMPARISONS: Final = 1000
MAX_EXPRESSION_CHARS: Final = 512
MAX_EXPRESSION_NODES: Final = 64
ARITHMETIC: Final[
    dict[type[ast.operator], Callable[[Fraction, Fraction], Fraction]]
] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
COMPARISONS: Final[dict[str, Callable[[Fraction, Fraction], bool]]] = {
    "<=": operator.le,
    ">=": operator.ge,
    "==": operator.eq,
}
logger = logging.getLogger(__name__)


# cost: time O(b+c), heap O(b+c), stack O(d), io one input read and stdout
# vars: b = 입력 바이트 수, c = 비교 수, d = JSON 깊이; 식 크기·이름 길이 제한
# basis: estimate
def main() -> int:
    logging.basicConfig(level=logging.ERROR, format="%(message)s")
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("input", nargs="?", default="-")
    args = parser.parse_args()
    try:
        raw = _read_input(args.input)
        document = json.loads(
            raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant
        )
        report = _check_document(document)
    except (OSError, UnicodeError, ValueError, RecursionError) as error:
        logger.error("invalid decision input: %s", error)
        return 2
    print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    return 1 if report["claim_errors"] else 0


# cost: time O(b), heap O(b), stack O(1), io one input read
# vars: b = 최대 입력 한도까지 읽은 바이트 수
# basis: estimate
def _read_input(path: str) -> str:
    if path == "-":
        data = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    else:
        with Path(path).open("rb") as stream:
            data = stream.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("input exceeds 1 MiB")
    return data.decode("utf-8")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("duplicate object key")
        result[name] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ValueError("nonfinite JSON number")


def _object(value: object, location: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(k, str) for k in value):
        raise ValueError(f"{location}: expected object")
    return cast(dict[str, object], value)


def _text(value: object, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{location}: expected nonempty text")
    return value


def _fields(row: dict[str, object], allowed: set[str], location: str) -> None:
    if row.keys() - allowed:
        raise ValueError(f"{location}: unsupported fields")


def _name(value: str) -> None:
    _text(value, "name")
    if len(value) > MAX_NAME_CHARS:
        raise ValueError("name exceeds 128 characters")


def _check_document(value: object) -> dict[str, object]:
    document = _object(value, "input")
    _fields(document, {"requirements", "candidates"}, "input")
    requirements = _object(document.get("requirements"), "requirements")
    candidates = _object(document.get("candidates"), "candidates")
    if not requirements or not candidates:
        raise ValueError("requirements and candidates must not be empty")
    if len(requirements) * len(candidates) > MAX_COMPARISONS:
        raise ValueError("more than 1000 comparisons; split the input")
    rules = {name: _read_rule(raw, name) for name, raw in requirements.items()}
    reports: dict[str, object] = {}
    claim_errors: list[str] = []
    for name, raw in candidates.items():
        _name(name)
        rows = _object(raw, f"candidates.{name}")
        _fields(rows, set(rules), f"candidates.{name}")
        checks = {}
        for key, rule in rules.items():
            location = f"candidates.{name}.{key}"
            check = _check_value(rule, rows.get(key), location)
            checks[key] = check
            if check.get("claim_error"):
                claim_errors.append(location)
        statuses = {check["status"] for check in checks.values()}
        status = "fail" if "fail" in statuses else "unknown"
        if statuses == {"pass"}:
            status = "pass"
        reports[name] = {"status": status, "checks": checks}
    return {
        "scope": "provided_input_only",
        "candidates": reports,
        "claim_errors": claim_errors,
    }


def _read_rule(raw: object, name: str) -> dict[str, object]:
    _name(name)
    rule = _object(raw, f"requirements.{name}")
    _fields(rule, {"source", "limit", "operator", "unit", "scope"}, name)
    for key in ["source", "unit", "scope"]:
        _text(rule.get(key), f"requirements.{name}.{key}")
    operation = _text(rule.get("operator"), f"requirements.{name}.operator")
    if operation not in COMPARISONS:
        raise ValueError(f"requirements.{name}: unsupported comparison")
    limit = _calculate(rule.get("limit"))
    if isinstance(limit, bool) and operation != "==":
        raise ValueError(f"requirements.{name}: boolean requires ==")
    return {**rule, "limit": limit}


def _check_value(
    rule: dict[str, object], raw: object, location: str
) -> dict[str, object]:
    if raw is None:
        return {"status": "unknown", "reason": "missing check"}
    row = _object(raw, location)
    _fields(row, {"value", "unit", "scope", "evidence", "certainty", "claim"}, location)
    certainty = row.get("certainty")
    if certainty not in ("known", "estimated", "unknown"):
        raise ValueError(f"{location}: invalid certainty")
    claim = row.get("claim")
    if claim is not None and claim not in ("pass", "fail", "unknown"):
        raise ValueError(f"{location}: invalid claim")
    actual = None if row.get("value") is None else _calculate(row["value"])
    result = _compare(rule, row, actual)
    if claim is not None and claim != result["status"]:
        result["claim_error"] = {"claimed": claim, "computed": result["status"]}
    return result


def _compare(
    rule: dict[str, object], row: dict[str, object], actual: Fraction | bool | None
) -> dict[str, object]:
    for key in ["unit", "scope"]:
        if row.get(key) != rule[key]:
            return {"status": "unknown", "reason": f"{key} mismatch"}
    if row.get("certainty") == "unknown" or actual is None:
        return {"status": "unknown", "reason": "unknown value"}
    evidence = row.get("evidence")
    if not isinstance(evidence, str) or not evidence.strip():
        return {"status": "unknown", "reason": "missing evidence"}
    limit = rule["limit"]
    if type(actual) is not type(limit):
        raise ValueError("value and limit types must match")
    if isinstance(actual, bool):
        is_met = actual == limit
    else:
        operation = COMPARISONS[cast(str, rule["operator"])]
        is_met = operation(actual, cast(Fraction, limit))
    comparison = "pass" if is_met else "fail"
    status = comparison if row["certainty"] == "known" else "unknown"
    return {
        "status": status,
        "comparison": comparison,
        "certainty": row["certainty"],
        "value": str(actual),
        "limit": str(limit),
    }


# cost: time O(n²), heap O(n), stack O(n)
# vars: n = 식 길이; 문자·노드 한도로 유리수 피연산자 크기도 제한
# basis: estimate
def _calculate(value: object) -> Fraction | bool:
    if isinstance(value, bool):
        return value
    expression = _text(value, "expression")
    if len(expression) > MAX_EXPRESSION_CHARS:
        raise ValueError("expression exceeds 512 characters")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as error:
        raise ValueError("invalid arithmetic expression") from error
    if len(list(ast.walk(tree))) > MAX_EXPRESSION_NODES:
        raise ValueError("expression exceeds 64 nodes")
    try:
        return _evaluate(tree.body, expression)
    except ZeroDivisionError as error:
        raise ValueError("division by zero") from error


def _evaluate(node: ast.AST, source: str) -> Fraction:
    if isinstance(node, ast.Constant):
        literal = ast.get_source_segment(source, node)
        if literal is not None and re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", literal):
            return Fraction(literal)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        number = _evaluate(node.operand, source)
        return -number if isinstance(node.op, ast.USub) else number
    if isinstance(node, ast.BinOp) and type(node.op) in ARITHMETIC:
        operation = ARITHMETIC[type(node.op)]
        return operation(_evaluate(node.left, source), _evaluate(node.right, source))
    raise ValueError("only decimal arithmetic and parentheses are supported")


if __name__ == "__main__":
    raise SystemExit(main())
