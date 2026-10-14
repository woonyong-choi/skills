"""전체 완료 조건과 현재 단계의 연결을 검사한다."""

from __future__ import annotations

import re


def completion_criteria(body: str) -> list[str]:
    section = re.search(r"^## 완료 조건\s*\n(.*?)(?=^## |\Z)", body, re.M | re.S)
    if not section:
        raise ValueError("issue has no completion criteria section")
    criteria = re.findall(r"^- \[[ xX]\] (.+)$", section.group(1), re.M)
    if not criteria:
        raise ValueError("issue completion criteria are empty")
    return criteria


def validate_scope(scope: dict, criteria: list[str]) -> None:
    required = {
        "criteria",
        "stage",
        "relation",
        "covers",
        "reason",
        "boundary",
        "outcomes",
    }
    if not isinstance(scope, dict) or set(scope) != required:
        raise ValueError(
            "scope requires criteria, stage, relation, covers, reason, boundary, outcomes; assess each requested result before saving"
        )
    if scope["criteria"] != criteria:
        raise ValueError(
            "scope criteria differ from issue; read the issue and reassess"
        )
    if scope["relation"] not in {"continue", "amend"}:
        raise ValueError(
            "independent or changed scope requires issue selection or explicit issue amendment before checkpoint"
        )
    for name in ("stage", "reason", "boundary"):
        if not isinstance(scope[name], str) or not scope[name].strip():
            raise ValueError("missing scope justification: " + name)
    covers = scope["covers"]
    if not isinstance(covers, list) or not covers:
        raise ValueError("current stage must cover an issue completion criterion")
    if any(
        type(index) is not int or not 1 <= index <= len(criteria) for index in covers
    ):
        raise ValueError("scope covers must contain one-based criterion numbers")

    outcomes = scope["outcomes"]
    if not isinstance(outcomes, list) or not outcomes:
        raise ValueError(
            "scope requires a separate assessment for each requested outcome"
        )
    linked = set()
    for outcome in outcomes:
        _validate_outcome(outcome, criteria)
        linked.add(outcome["criterion"])
    if linked != set(covers):
        raise ValueError("scope covers must match assessed outcome criteria")


def _validate_outcome(outcome: dict, criteria: list[str]) -> None:
    fields = {
        "result",
        "criterion",
        "criterion_result",
        "verification",
        "independent",
        "counterfactual",
    }
    if not isinstance(outcome, dict) or set(outcome) != fields:
        raise ValueError(
            "outcome requires result, criterion, criterion_result, verification, independent, counterfactual"
        )
    if type(outcome["independent"]) is not bool:
        raise ValueError("outcome independence must be an explicit boolean")
    if outcome["independent"]:
        raise ValueError(
            "independent outcome: search existing issues, reuse or create one, connect its board and bind before recording; do not widen current criteria"
        )
    index = outcome["criterion"]
    if type(index) is not int or not 1 <= index <= len(criteria):
        raise ValueError("outcome must identify one existing completion criterion")
    for name in ("result", "criterion_result", "verification", "counterfactual"):
        if not isinstance(outcome[name], str) or not outcome[name].strip():
            raise ValueError("missing outcome evidence: " + name)


def merge_record(data: dict) -> dict:
    result = {}
    for key, value in data.items():
        if "```" in value or "~~~" in value:
            result[key] = value.strip()
            continue
        seen = set()
        lines = []
        for line in value.splitlines():
            is_prose = bool(line.strip()) and not line.lstrip().startswith(
                ("|", "#", "-", "*", ">")
            )
            if is_prose and line in seen:
                continue
            seen.add(line)
            lines.append(line)
        result[key] = "\n".join(lines).strip()
    return result
