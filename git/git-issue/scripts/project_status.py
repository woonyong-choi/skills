"""저장소에 연결된 Projects v2의 이슈·PR 등록과 Status를 관리한다.
인자: --repo owner/name, --project 번호 반복(colors 필수), --status-map 역할=이름 반복, set 번호 상태 | setup | colors | check [--fix] | queue
출력: stdout 프로젝트·상태·불일치·대기 이슈(판 순서)·오류, 종료 0 성공·1 불일치·2 실패
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from datetime import datetime
from collections.abc import Callable
from typing import Any, NoReturn, Optional

STATES = ("대기", "진행", "검토", "보류", "완료")
STATE_COLORS = {
    "대기": "GRAY",
    "진행": "BLUE",
    "검토": "GREEN",
    "보류": "RED",
    "작업 중": "BLUE",
    "검증 중": "GREEN",
    "선택 필요": "RED",
}
PAGE = "pageInfo { hasNextPage endCursor }"
HOLD_DAYS = 30
ITEM_FIELDS = (
    'fieldValueByName(name:"Status"){... on ProjectV2ItemFieldSingleSelectValue{name updatedAt}}'
    ' hold: fieldValueByName(name:"보류 사유"){... on ProjectV2ItemFieldTextValue{text}}'
)
Gh = Callable[[list[str], Optional[str]], dict[str, Any]]


class ProjectError(Exception):
    """조회 또는 상태 변경에 필요한 조건이 충족되지 않은 오류."""


class StdoutArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ProjectError(message)


class ProjectStatus:
    def __init__(
        self, repo: str | None, gh: Gh, states: dict[str, str] | None = None
    ) -> None:
        self.states = states or dict(zip(STATES, STATES))
        self._status_field_ids: set[str] = set()
        self.gh = gh
        self.repo = (
            repo
            or gh(["repo", "view", "--json", "nameWithOwner"], None)["nameWithOwner"]
        )
        parts = self.repo.split("/")
        if len(parts) != 2 or not all(parts):
            raise ProjectError(f"invalid repository: {self.repo}; expected owner/name")
        self.repository = {"owner": parts[0], "name": parts[1]}

    def run(self, args: argparse.Namespace) -> int:
        if args.command == "colors" and not args.project:
            raise ProjectError("colors requires an explicit --project")
        projects = self._pages(
            "query($owner:String!,$name:String!,$cursor:String){"
            "repository(owner:$owner,name:$name){projectsV2(first:100,after:$cursor){"
            "nodes{id number title}" + PAGE + "}}}",
            self.repository,
            "repository",
            "projectsV2",
        )
        if len(projects) > 1 and not args.project:
            raise ProjectError("여러 프로젝트 연결: --project 명시 필수")
        if args.project:
            missing = set(args.project) - {project["number"] for project in projects}
            if missing:
                raise ProjectError(f"연결되지 않은 프로젝트: {sorted(missing)}")
            projects = [
                project for project in projects if project["number"] in args.project
            ]
        if not projects:
            raise ProjectError(
                f"{self.repo}: 연결된 프로젝트 없음; project_bootstrap.py로 새 저장소 절차 실행 필요"
            )
        if args.command == "queue":
            for project in projects:
                print(f"프로젝트 {project['number']} {project['title']} ({self.repo})")
                for issue in self._waiting(project):
                    print(f"#{issue['number']} {issue['title']}")
            return 0
        content = self._issue_or_pull_request(args.number) if args.number else None
        if content and args.command == "set":
            if (content["state"] != "OPEN") != (args.status == "완료"):
                raise ProjectError(
                    "issue state and requested status disagree; close only with completion evidence"
                )
        issues = (
            ([content] if content else self._issues())
            if args.command == "check"
            else []
        )
        attention = 0
        plans: list[
            tuple[
                dict[str, Any],
                dict[str, Any],
                list[tuple[dict[str, Any], str, dict[str, Any] | None]],
            ]
        ] = []
        for project in projects:
            field = self._status_field(project)
            if args.command in ("setup", "colors"):
                plans.append((project, field, []))
                continue
            items = self._items(project, content)
            changes = (
                [(content, self.states[args.status])]
                if args.command == "set"
                else self._mismatches(project, issues, items)
            )
            if args.command == "check":
                attention += self._attention(project, issues, items, time.time())
            if args.command == "set" or args.fix:
                for _, status in changes:
                    self._option(field, status, project)
            plans.append(
                (
                    project,
                    field,
                    [
                        (value, status, items.get(value["id"]))
                        for value, status in changes
                    ],
                )
            )
        count = 0
        for project, field, item_changes in plans:
            print(f"프로젝트 {project['number']} {project['title']} ({self.repo})")
            if args.command == "colors":
                self._colors(project, field)
                continue
            if args.command == "setup":
                self._setup(project, field, args.view)
                continue
            count += len(item_changes)
            if args.command == "set" or args.fix:
                for value, status, item in item_changes:
                    self._set(project, field, value, status, item)
        if args.command == "check":
            print(f"불일치 {count}개" + ("; 수정 완료" if args.fix and count else "") + (f", 주의 {attention}개(자동 변경 없음)" if attention else ""))
            return 1 if (count and not args.fix) or attention else 0
        return 0

    def _query(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        response = self.gh(
            ["api", "graphql", "--input", "-"],
            json.dumps({"query": query, "variables": variables}),
        )
        if response.get("errors"):
            raise ProjectError(f"graphql failed: {response['errors']}")
        if not response.get("data"):
            raise ProjectError("graphql returned no data")
        return response["data"]

    def _pages(
        self, query: str, variables: dict[str, Any], parent: str, field: str
    ) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        cursor = None
        while True:
            data = self._query(query, {**variables, "cursor": cursor})
            if not data.get(parent):
                raise ProjectError(f"unavailable graphql object: {parent}")
            page = data[parent][field]
            nodes.extend(node for node in page["nodes"] if node is not None)
            if not page["pageInfo"]["hasNextPage"]:
                return nodes
            next_cursor = page["pageInfo"]["endCursor"]
            if not next_cursor or next_cursor == cursor:
                raise ProjectError(f"invalid pagination cursor: {field}")
            cursor = next_cursor

    def _project_pages(
        self, project: dict[str, Any], field: str, selection: str
    ) -> list[dict[str, Any]]:
        query = (
            "query($id:ID!,$cursor:String){node(id:$id){... on ProjectV2{"
            + field
            + "(first:100,after:$cursor){nodes{"
            + selection
            + "}"
            + PAGE
            + "}}}}"
        )
        return self._pages(query, {"id": project["id"]}, "node", field)

    def _status_field(self, project: dict[str, Any]) -> dict[str, Any]:
        fields = self._project_pages(
            project,
            "fields",
            "... on ProjectV2SingleSelectField{id name options{id name color description}}",
        )
        for field in fields:
            if field.get("name") == "Status":
                self._status_field_ids.add(field["id"])
                return field
        raise ProjectError(f"프로젝트 {project['number']}: Status 단일 선택 필드 없음")

    def _issue_or_pull_request(self, number: int) -> dict[str, Any]:
        data = self._query(
            "query($owner:String!,$name:String!,$number:Int!){"
            "repository(owner:$owner,name:$name){issueOrPullRequest(number:$number){"
            "... on Issue{id number state} ... on PullRequest{id number state}}}}",
            {**self.repository, "number": number},
        )
        content = (data.get("repository") or {}).get("issueOrPullRequest")
        if not content:
            raise ProjectError(f"issue or pull request not found: {self.repo}#{number}")
        return content

    def _issues(self) -> list[dict[str, Any]]:
        return self._pages(
            "query($owner:String!,$name:String!,$cursor:String){repository(owner:$owner,name:$name){issues(first:100,after:$cursor){nodes{id number state}"
            + PAGE
            + "}}}",
            self.repository,
            "repository",
            "issues",
        )

    def _items(
        self, project: dict[str, Any], content: dict[str, Any] | None = None
    ) -> dict[str, dict[str, Any]]:
        if content:
            selection = "projectItems(first:100){nodes{id project{id} " + ITEM_FIELDS + "} pageInfo{hasNextPage}}"
            data = self._query(
                "query($id:ID!){node(id:$id){... on Issue{"
                + selection
                + "} ... on PullRequest{"
                + selection
                + "}}}",
                {"id": content["id"]},
            )["node"]["projectItems"]
            if data["pageInfo"]["hasNextPage"]:
                raise ProjectError("too many item memberships; use full project check")
            return {
                content["id"]: item
                for item in data["nodes"]
                if item["project"]["id"] == project["id"]
            }
        items = self._project_pages(
            project,
            "items",
            "id content{... on Issue{id number state repository{nameWithOwner}}"
            "... on PullRequest{id number repository{nameWithOwner}}} " + ITEM_FIELDS,
        )
        return {
            item["content"]["id"]: item
            for item in items
            if (item.get("content") or {})
            .get("repository", {})
            .get("nameWithOwner", "")
            .casefold()
            == self.repo.casefold()
        }

    def _waiting(self, project: dict[str, Any]) -> list[dict[str, Any]]:
        """대기 상태인 이 저장소의 열린 이슈를 판의 수동 순서(POSITION)대로 돌려준다."""
        items = self._pages(
            "query($id:ID!,$cursor:String){node(id:$id){... on ProjectV2{"
            "items(first:100,after:$cursor,orderBy:{field:POSITION,direction:ASC}){nodes{id "
            "content{... on Issue{number title state repository{nameWithOwner}}} "
            + ITEM_FIELDS
            + "}"
            + PAGE
            + "}}}}",
            {"id": project["id"]},
            "node",
            "items",
        )
        waiting = self.states["대기"]
        return [
            item["content"]
            for item in items
            if (item.get("content") or {}).get("state") == "OPEN"
            and item["content"].get("repository", {}).get("nameWithOwner", "").casefold() == self.repo.casefold()
            and self._status(item) == waiting
        ]

    def _mismatches(
        self,
        project: dict[str, Any],
        issues: list[dict[str, Any]],
        items: dict[str, Any],
    ) -> list[tuple[dict[str, Any], str]]:
        changes = []
        for issue in issues:
            item = items.get(issue["id"])
            status = self._status(item)
            reason = None
            target = self.states["대기"]
            if issue["state"] == "OPEN" and item is None:
                reason = "열린 이슈가 판에 없음"
            elif issue["state"] == "OPEN" and not status:
                reason = "열린 이슈의 상태가 미설정"
            elif (
                issue["state"] != "OPEN"
                and item is not None
                and status != self.states["완료"]
            ):
                reason, target = "닫힌 이슈인데 완료가 아님", self.states["완료"]
            elif issue["state"] == "OPEN" and status == self.states["완료"]:
                reason = "열린 이슈인데 완료"
            if reason:
                print(
                    f"프로젝트 {project['number']} #{issue['number']}: {reason} ({status or '미설정'} → {target})"
                )
                changes.append((issue, target))
        return changes

    def _attention(
        self,
        project: dict[str, Any],
        issues: list[dict[str, Any]],
        items: dict[str, Any],
        now: float,
    ) -> int:
        """상태표의 머무는 조건 위반 출력. 상태 변경 없음"""
        found = 0
        for issue in issues:
            if issue.get("state") != "OPEN":
                continue
            item = items.get(issue["id"])
            status = self._status(item)
            reasons = []
            if status == self.states["보류"]:
                if "재개 조건" not in ((item or {}).get("hold") or {}).get("text", ""):
                    reasons.append("보류인데 재개 조건 없음")
                stamp = ((item or {}).get("fieldValueByName") or {}).get("updatedAt")
                if stamp and now - datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp() >= HOLD_DAYS * 86400:
                    reasons.append(f"보류 {HOLD_DAYS}일 이상: 사용자에게 계속·취소 확인")
            for reason in reasons:
                print(f"프로젝트 {project['number']} #{issue['number']}: 주의 {reason}")
            found += len(reasons)
        return found

    def _set(
        self,
        project: dict[str, Any],
        field: dict[str, Any],
        content: dict[str, Any],
        status: str,
        item: dict[str, Any] | None,
    ) -> None:
        if item is not None and self._status(item) == status:
            print(f"#{content['number']}: {status} 유지 (쓰기 없음)")
            return
        option = self._option(field, status, project)
        if item is None:
            result = self._mutate(
                "addProjectV2ItemById",
                {"projectId": project["id"], "contentId": content["id"]},
                "item{id}",
            )
            item = result["item"]
        self._mutate(
            "updateProjectV2ItemFieldValue",
            {
                "projectId": project["id"],
                "itemId": item["id"],
                "fieldId": field["id"],
                "value": {"singleSelectOptionId": option["id"]},
            },
            "projectV2Item{id}",
        )
        print(f"#{content['number']}: {status} 변경")

    def _setup(
        self, project: dict[str, Any], field: dict[str, Any], view_id: str | None
    ) -> None:
        views = self._project_pages(project, "views", "id name layout filter")
        selected = [v for v in views if v["id"] == view_id] if view_id else views
        if len(selected) != 1:
            raise ProjectError("setup은 정확한 --view ID 필요; 선택한 뷰만 변경")
        aliases = {"작업 중": "진행", "검증 중": "검토", "선택 필요": "보류"}
        options = field["options"]
        allowed = set(aliases) | set(self.states.values())
        if any(o["name"] not in allowed for o in options):
            raise ProjectError(
                "알 수 없는 기존 상태: 먼저 의미별 --status-map 지정 필요"
            )
        self._colors(project, field)
        options = field["options"]
        additions = [
            {"name": name, "color": "GRAY", "description": ""}
            for name in self.states.values()
            if name not in {o["name"] for o in options}
        ]
        if additions:
            self._mutate(
                "updateProjectV2Field",
                {"fieldId": field["id"], "singleSelectOptions": options + additions},
                "projectV2Field{... on ProjectV2SingleSelectField{id}}",
            )
            field = self._status_field(project)
        items = self._project_pages(
            project,
            "items",
            'id fieldValueByName(name:"Status"){... on ProjectV2ItemFieldSingleSelectValue{name}} hold:fieldValueByName(name:"보류 사유"){... on ProjectV2ItemFieldTextValue{text}}',
        )
        for item in items:
            old = self._status(item)
            if old not in aliases:
                continue
            if old == "선택 필요":
                self._preserve_hold(project, item)
            option = self._option(field, self.states[aliases[old]], project)
            self._mutate(
                "updateProjectV2ItemFieldValue",
                {
                    "projectId": project["id"],
                    "itemId": item["id"],
                    "fieldId": field["id"],
                    "value": {"singleSelectOptionId": option["id"]},
                },
                "projectV2Item{id}",
            )
        verified = self._project_pages(
            project,
            "items",
            'id fieldValueByName(name:"Status"){... on ProjectV2ItemFieldSingleSelectValue{name}} hold:fieldValueByName(name:"보류 사유"){... on ProjectV2ItemFieldTextValue{text}}',
        )
        if {i["id"] for i in items} != {i["id"] for i in verified} or any(
            self._status(i) in aliases for i in verified
        ):
            raise ProjectError("이관 중 항목 변경 또는 옛 상태 잔존; 선택지 삭제 중단")
        kept = [self._option(field, name, project) for name in self.states.values()]
        if field["options"] != kept:
            self._mutate(
                "updateProjectV2Field",
                {"fieldId": field["id"], "singleSelectOptions": kept},
                "projectV2Field{... on ProjectV2SingleSelectField{id}}",
            )
        view = selected[0]
        current = view.get("filter") or ""
        done = self.states["완료"]
        hold = self.states["보류"]
        current = re.sub(
            r'-status:(?:"[^"\n]*"|[^\s]+)',
            lambda match: " ".join(
                "-status:" + json.dumps(value, ensure_ascii=False)
                for value in match.group()[8:].strip('"').split(",")
                if value not in {hold, "선택 필요"}
            ),
            current,
        ).strip()

        exclusions = re.findall(r'-status:(?:"[^"\n]*"|[^\s]+)', current)
        hidden = any(done in term[8:].strip('"').split(",") for term in exclusions)
        new_filter = (
            current
            if hidden
            else (current + " -status:" + json.dumps(done, ensure_ascii=False)).strip()
        )
        if view["layout"] != "BOARD_LAYOUT" or new_filter != (view.get("filter") or ""):
            self._mutate(
                "updateProjectV2View",
                {"viewId": view["id"], "layout": "BOARD_LAYOUT", "filter": new_filter},
                "projectV2View{id}",
            )
        print("다섯 상태 이관 완료; 보드 그룹 기준·숨긴 열은 실제 화면에서 확인 필요")

    def _preserve_hold(self, project: dict[str, Any], item: dict[str, Any]) -> None:
        fields = self._project_pages(
            project, "fields", "... on ProjectV2Field{id name dataType}"
        )
        field = next((f for f in fields if f.get("name") == "보류 사유"), None)
        if field and field.get("dataType") != "TEXT":
            raise ProjectError("보류 사유 필드가 TEXT가 아님; 변경 중단")
        if not field:
            field = self._mutate(
                "createProjectV2Field",
                {"projectId": project["id"], "dataType": "TEXT", "name": "보류 사유"},
                "projectV2Field{... on ProjectV2Field{id}} ",
            )["projectV2Field"]
        old = (item.get("hold") or {}).get("text", "")
        reason = "결정 대기; 재개 조건: 필요한 결정 확정"
        if reason not in old:
            self._mutate(
                "updateProjectV2ItemFieldValue",
                {
                    "projectId": project["id"],
                    "itemId": item["id"],
                    "fieldId": field["id"],
                    "value": {"text": old + ("\n" if old else "") + reason},
                },
                "projectV2Item{id}",
            )

    def _colored_options(self, options: list[dict[str, Any]]) -> list[dict[str, Any]]:
        colors = dict(STATE_COLORS)
        colors.update(
            {
                name: STATE_COLORS[role]
                for role, name in self.states.items()
                if role in STATE_COLORS
            }
        )
        colors.pop(self.states["완료"], None)
        return [
            {**option, "color": colors.get(option["name"], option["color"])}
            for option in options
        ]

    def _colors(self, project: dict[str, Any], field: dict[str, Any]) -> None:
        options = self._colored_options(field["options"])
        if options == field["options"]:
            print("상태 색상 일치 (쓰기 없음)")
            return
        self._mutate(
            "updateProjectV2Field",
            {"fieldId": field["id"], "singleSelectOptions": options},
            "projectV2Field{... on ProjectV2SingleSelectField{id}}",
        )
        actual = self._status_field(project)
        if actual["options"] != options:
            raise ProjectError("status colors or preserved options differ after update")
        field["options"] = actual["options"]
        print("상태 색상 변경·재조회 완료")

    def _mutate(
        self, name: str, value: dict[str, Any], selection: str
    ) -> dict[str, Any]:
        if (
            name == "updateProjectV2Field"
            and value.get("fieldId") in self._status_field_ids
        ):
            if "singleSelectOptions" in value:
                value = {
                    **value,
                    "singleSelectOptions": self._colored_options(
                        value["singleSelectOptions"]
                    ),
                }
        input_type = name[0].upper() + name[1:] + "Input!"
        return self._query(
            f"mutation($input:{input_type}){{{name}(input:$input){{{selection}}}}}",
            {"input": value},
        )[name]

    @staticmethod
    def _status(item: dict[str, Any] | None) -> str | None:
        return ((item or {}).get("fieldValueByName") or {}).get("name")

    @staticmethod
    def _option(
        field: dict[str, Any], status: str, project: dict[str, Any]
    ) -> dict[str, Any]:
        for option in field["options"]:
            if option["name"] == status:
                return option
        raise ProjectError(
            f"프로젝트 {project['number']}: Status 선택지 없음: {status}; setup 필요"
        )


def run_gh(args: list[str], payload: str | None = None) -> dict[str, Any]:
    result = subprocess.run(
        ["gh", *args], input=payload, text=True, capture_output=True, check=False
    )
    if result.returncode:
        raise ProjectError(
            f"gh failed ({result.returncode}): {result.stderr.strip() or result.stdout.strip()}"
        )
    return json.loads(result.stdout)


def main(argv: list[str] | None = None, gh: Gh = run_gh) -> int:
    parser = StdoutArgumentParser(description=__doc__)
    parser.add_argument("--project", type=int, action="append", default=[])
    parser.add_argument(
        "--status-map", action="append", default=[], metavar="ROLE=NAME"
    )
    parser.add_argument("--repo", help="owner/name (기본: 현재 디렉터리 저장소)")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("set", "setup", "colors", "check", "queue"):
        command_parser = sub.add_parser(command)
        command_parser.add_argument("--repo", default=argparse.SUPPRESS)
        if command == "set":
            command_parser.add_argument("number", type=int)
            command_parser.add_argument("status", choices=STATES)
        if command == "setup":
            command_parser.add_argument("--view", help="변경할 프로젝트 뷰 ID")
        if command == "check":
            command_parser.add_argument("--fix", action="store_true")
            command_parser.add_argument(
                "--number", type=int, help="검사할 이슈 또는 PR 하나"
            )
    parser.set_defaults(fix=False, number=None)
    try:
        args = parser.parse_args(argv)
        states = dict(zip(STATES, STATES))
        for mapping in args.status_map:
            role, separator, name = mapping.partition("=")
            if (
                not separator
                or role not in states
                or not name.strip()
                or any(char in name for char in "\r\n,")
            ):
                raise ProjectError(f"invalid status mapping: {mapping}")
            states[role] = name
        if len(set(states.values())) != len(STATES):
            raise ProjectError("status mapping names must be unique")
        return ProjectStatus(args.repo, gh, states).run(args)
    except (ProjectError, OSError, ValueError, KeyError) as error:
        print(f"오류: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
