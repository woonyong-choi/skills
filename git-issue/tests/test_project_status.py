"""git-issue 프로젝트 판 상태 절의 CLI 계약을 고정 응답으로 검증한다."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import project_status  # noqa: E402

STATES = ["대기", "작업 중", "검증 중", "선택 필요", "보류", "완료"]


def connection(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    return {"nodes": nodes, "pageInfo": {"hasNextPage": False, "endCursor": None}}


class FakeGh:
    def __init__(self) -> None:
        self.projects = [{"id": "P", "number": 15, "title": "Example"}]
        self.options = [
            {"id": str(index), "name": name, "color": "GRAY", "description": ""}
            for index, name in enumerate(STATES)
        ]
        self.issues = [
            {"id": "I1", "number": 1, "state": "OPEN"},
            {"id": "I2", "number": 2, "state": "CLOSED"},
        ]
        self.items: list[dict[str, Any]] = []
        self.views = [
            {
                "id": "V",
                "name": "Board",
                "layout": "BOARD_LAYOUT",
                "filter": "assignee:@me",
            },
            {"id": "T", "name": "Table", "layout": "TABLE_LAYOUT", "filter": ""},
        ]
        self.writes: list[tuple[str, dict[str, Any]]] = []
        self.calls: list[dict[str, Any]] = []

    def add_item(self, number: int, status: str | None) -> None:
        issue = next(issue for issue in self.issues if issue["number"] == number)
        self.items.append(
            {
                "id": f"ITEM{number}",
                "content": {**issue, "repository": {"nameWithOwner": "owner/repo"}},
                "fieldValueByName": {"name": status} if status else None,
            }
        )

    def __call__(self, args: list[str], payload: str | None = None) -> dict[str, Any]:
        if args[:2] == ["repo", "view"]:
            return {"nameWithOwner": "owner/repo"}
        assert args == ["api", "graphql", "--input", "-"]
        request = json.loads(payload or "{}")
        query, variables = request["query"], request["variables"]
        self.calls.append(request)
        if query.startswith("mutation"):
            name = query.split("{", 1)[1].strip().split("(", 1)[0]
            value = variables["input"]
            self.writes.append((name, copy.deepcopy(value)))
            if name == "addProjectV2ItemById":
                number = int(value["contentId"][1:])
                self.add_item(number, None)
                return {"data": {name: {"item": {"id": f"ITEM{number}"}}}}
            if name == "updateProjectV2ItemFieldValue":
                item = next(
                    item for item in self.items if item["id"] == value["itemId"]
                )
                option = next(
                    option
                    for option in self.options
                    if option["id"] == value["value"]["singleSelectOptionId"]
                )
                item["fieldValueByName"] = {"name": option["name"]}
            elif name == "updateProjectV2Field":
                self.options = [
                    {"id": f"new{index}", **option}
                    for index, option in enumerate(value["singleSelectOptions"])
                ]
            elif name == "updateProjectV2View":
                next(view for view in self.views if view["id"] == value["viewId"])[
                    "filter"
                ] = value["filter"]
            return {"data": {name: {}}}
        if "projectsV2(" in query:
            result = {"repository": {"projectsV2": connection(self.projects)}}
        elif "fields(" in query:
            result = {
                "node": {
                    "fields": connection(
                        [{"id": "F", "name": "Status", "options": self.options}]
                    )
                }
            }
        elif "items(" in query:
            result = {"node": {"items": connection(self.items)}}
        elif "views(" in query:
            result = {"node": {"views": connection(self.views)}}
        elif "issues(" in query:
            result = {"repository": {"issues": connection(self.issues)}}
        elif "issue(" in query:
            result = {
                "repository": {
                    "issue": next(
                        (
                            issue
                            for issue in self.issues
                            if issue["number"] == variables["number"]
                        ),
                        None,
                    )
                }
            }
        else:
            raise AssertionError(query)
        return copy.deepcopy({"data": result})


@pytest.fixture
def gh() -> FakeGh:
    return FakeGh()


@pytest.mark.parametrize("status", STATES)
def test_set_missing_item_adds_and_moves_status(gh: FakeGh, status: str) -> None:
    assert project_status.main(["set", "1", status], gh) == 0
    assert [name for name, _ in gh.writes] == [
        "addProjectV2ItemById",
        "updateProjectV2ItemFieldValue",
    ]
    assert gh.items[0]["fieldValueByName"]["name"] == status


def test_set_same_status_has_no_writes(gh: FakeGh) -> None:
    gh.add_item(1, "작업 중")

    assert project_status.main(["set", "1", "작업 중", "--repo", "owner/repo"], gh) == 0
    assert gh.writes == []


@pytest.mark.parametrize(
    "args", [["set", "1", "대기"], ["setup"], ["check"], ["check", "--fix"]]
)
def test_commands_no_linked_project_report_without_writes(
    gh: FakeGh, capsys: Any, args: list[str]
) -> None:
    gh.projects = []

    assert project_status.main(args, gh) == 2
    assert "연결된 프로젝트 없음" in capsys.readouterr().out
    assert gh.writes == []


def test_set_missing_option_reports_before_addition(gh: FakeGh, capsys: Any) -> None:
    gh.options = gh.options[:1]

    assert project_status.main(["set", "1", "작업 중"], gh) == 2
    assert "작업 중" in capsys.readouterr().out
    assert gh.writes == []


def test_check_reports_three_mismatches_without_writes(gh: FakeGh, capsys: Any) -> None:
    gh.issues.append({"id": "I3", "number": 3, "state": "OPEN"})
    gh.add_item(2, "작업 중")
    gh.add_item(3, "완료")

    assert project_status.main(["check"], gh) == 1
    output = capsys.readouterr().out
    for phrase in ("#1", "#2", "#3", "판에 없음", "닫힌 이슈", "열린 이슈"):
        assert phrase in output
    assert gh.writes == []


def test_check_fix_changes_only_mismatches_and_is_idempotent(gh: FakeGh) -> None:
    gh.issues.extend(
        [
            {"id": "I3", "number": 3, "state": "OPEN"},
            {"id": "I4", "number": 4, "state": "OPEN"},
        ]
    )
    gh.add_item(2, None)
    gh.add_item(3, "완료")
    gh.add_item(4, "검증 중")

    assert project_status.main(["check", "--fix"], gh) == 0
    assert len(gh.writes) == 4
    assert {
        item["content"]["number"]: item["fieldValueByName"]["name"] for item in gh.items
    } == {1: "대기", 2: "완료", 3: "대기", 4: "검증 중"}
    gh.writes.clear()
    assert project_status.main(["check", "--fix"], gh) == 0
    assert gh.writes == []


def test_check_clean_board_ignores_other_repository_and_drafts(gh: FakeGh) -> None:
    gh.add_item(1, "보류")
    gh.items.extend(
        [
            {"id": "D", "content": None},
            {
                "id": "X",
                "content": {
                    "id": "other",
                    "repository": {"nameWithOwner": "other/repo"},
                },
            },
        ]
    )

    assert project_status.main(["check"], gh) == 0
    assert gh.writes == []


def test_setup_preserves_option_ids_and_filters_only_boards(
    gh: FakeGh, capsys: Any
) -> None:
    gh.options = [
        {"id": "legacy", "name": "기존", "color": "BLUE", "description": "유지"},
        gh.options[0],
    ]
    original = copy.deepcopy(gh.options)
    gh.add_item(1, "기존")

    assert project_status.main(["setup"], gh) == 0
    assert gh.options[:2] == original
    assert {option["name"] for option in gh.options} == {"기존", *STATES}
    assert gh.items[0]["fieldValueByName"]["name"] == "기존"
    assert gh.views[0]["filter"] == "assignee:@me -status:완료"
    assert gh.views[1]["filter"] == ""
    assert "Hide from view" in capsys.readouterr().out
    gh.writes.clear()
    assert project_status.main(["setup"], gh) == 0
    assert gh.writes == []


def test_check_fix_missing_option_has_no_partial_writes(gh: FakeGh) -> None:
    gh.options = gh.options[:1]
    gh.add_item(2, "작업 중")

    assert project_status.main(["check", "--fix"], gh) == 2
    assert gh.writes == []


@pytest.mark.parametrize(
    "field,parent",
    [
        ("projectsV2", "repository"),
        ("issues", "repository"),
        ("fields", "node"),
        ("items", "node"),
        ("views", "node"),
    ],
)
def test_commands_read_all_connection_pages(
    gh: FakeGh, field: str, parent: str
) -> None:
    gh.add_item(1, "대기")
    visited = []

    def paginated(args: list[str], payload: str | None = None) -> dict[str, Any]:
        response = gh(args, payload)
        request = json.loads(payload or "{}")
        if f"{field}(" not in request.get("query", ""):
            return response
        cursor = request["variables"]["cursor"]
        visited.append(cursor)
        if cursor is None:
            response["data"][parent][field] = {
                "nodes": [],
                "pageInfo": {"hasNextPage": True, "endCursor": "next"},
            }
        return response

    command = "setup" if field == "views" else "check"
    assert project_status.main([command], paginated) == 0
    assert visited == [None, "next"]


def test_set_all_linked_projects_receive_status(gh: FakeGh) -> None:
    gh.projects.append({"id": "Q", "number": 20, "title": "Second"})

    assert project_status.main(["--repo", "owner/repo", "set", "1", "작업 중"], gh) == 0
    changes = [
        value for name, value in gh.writes if name == "updateProjectV2ItemFieldValue"
    ]
    assert [value["projectId"] for value in changes] == ["P", "Q"]


@pytest.mark.parametrize(
    "current", ["-status:완료", '-status:"완료"', "assignee:@me -status:완료,보류"]
)
def test_setup_existing_exclusion_has_no_writes(gh: FakeGh, current: str) -> None:
    gh.views[0]["filter"] = current

    assert project_status.main(["setup"], gh) == 0
    assert gh.writes == []


def test_check_api_error_reports_to_stdout_without_writes(
    gh: FakeGh, capsys: Any
) -> None:
    def denied(args: list[str], payload: str | None = None) -> dict[str, Any]:
        if args[:2] == ["api", "graphql"]:
            return {"errors": [{"message": "permission denied"}]}
        return gh(args, payload)

    assert project_status.main(["check"], denied) == 2
    output = capsys.readouterr()
    assert "permission denied" in output.out
    assert output.err == ""
    assert gh.writes == []


def test_set_invalid_status_reports_to_stdout_without_writes(
    gh: FakeGh, capsys: Any
) -> None:
    assert project_status.main(["set", "1", "unknown"], gh) == 2
    output = capsys.readouterr()
    assert "unknown" in output.out
    assert output.err == ""
    assert gh.calls == []
    assert gh.writes == []
