"""저장소에 연결된 Projects v2의 이슈·PR 등록과 Status를 관리한다.
인자: --repo owner/name, set 번호 상태 | setup | check [--fix]
출력: stdout 프로젝트·상태·불일치·오류, 종료 0 성공·1 불일치·2 실패
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from collections.abc import Callable
from typing import Any, NoReturn, Optional

STATES = ("대기", "작업 중", "검증 중", "선택 필요", "보류", "완료")
PAGE = "pageInfo { hasNextPage endCursor }"
Gh = Callable[[list[str], Optional[str]], dict[str, Any]]


class ProjectError(Exception):
    """조회 또는 상태 변경에 필요한 조건이 충족되지 않은 오류."""


class StdoutArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ProjectError(message)


class ProjectStatus:
    def __init__(self, repo: str | None, gh: Gh) -> None:
        self.gh = gh
        self.repo = (
            repo
            or gh(["repo", "view", "--json", "nameWithOwner"], None)["nameWithOwner"]
        )
        parts = self.repo.split("/")
        if len(parts) != 2 or not all(parts):
            raise ProjectError(f"invalid repository: {self.repo}; expected owner/name")
        self.repository = {"owner": parts[0], "name": parts[1]}

    # cost: time O(n + c + v), heap O(n + c + v), stack O(1), io O(p + c + v)
    # vars: n = 전체 응답 항목 수, p = 전체 조회 페이지, c = 변경 항목, v = 보드 뷰
    # basis: estimate
    def run(self, args: argparse.Namespace) -> int:
        projects = self._pages(
            "query($owner:String!,$name:String!,$cursor:String){"
            "repository(owner:$owner,name:$name){projectsV2(first:100,after:$cursor){"
            "nodes{id number title}" + PAGE + "}}}",
            self.repository,
            "repository",
            "projectsV2",
        )
        if not projects:
            raise ProjectError(
                f"{self.repo}: 연결된 프로젝트 없음; 생성은 사용자 요청 필요"
            )
        content = (
            self._issue_or_pull_request(args.number) if args.command == "set" else None
        )
        issues = self._issues() if args.command == "check" else []
        plans = []
        for project in projects:
            field = self._status_field(project)
            if args.command == "setup":
                plans.append((project, field, []))
                continue
            items = self._items(project)
            changes = (
                [(content, args.status)]
                if content
                else self._mismatches(project, issues, items)
            )
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
        for project, field, changes in plans:
            print(f"프로젝트 {project['number']} {project['title']} ({self.repo})")
            if args.command == "setup":
                self._setup(project, field)
                continue
            count += len(changes)
            if args.command == "set" or args.fix:
                for value, status, item in changes:
                    self._set(project, field, value, status, item)
        if args.command == "check":
            print(f"불일치 {count}개" + ("; 수정 완료" if args.fix and count else ""))
            return 1 if count and not args.fix else 0
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

    # cost: time O(n), heap O(n), stack O(1), io O(p)
    # vars: p = 페이지 수, n = 항목 수
    # basis: estimate
    def _pages(
        self, query: str, variables: dict[str, Any], parent: str, field: str
    ) -> list[dict[str, Any]]:
        nodes = []
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
                return field
        raise ProjectError(f"프로젝트 {project['number']}: Status 단일 선택 필드 없음")

    def _issue_or_pull_request(self, number: int) -> dict[str, Any]:
        data = self._query(
            "query($owner:String!,$name:String!,$number:Int!){"
            "repository(owner:$owner,name:$name){issueOrPullRequest(number:$number){"
            "... on Issue{id number} ... on PullRequest{id number}}}}",
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

    def _items(self, project: dict[str, Any]) -> dict[str, dict[str, Any]]:
        items = self._project_pages(
            project,
            "items",
            "id content{... on Issue{id number state repository{nameWithOwner}}"
            "... on PullRequest{id number repository{nameWithOwner}}}"
            'fieldValueByName(name:"Status"){... on ProjectV2ItemFieldSingleSelectValue{name}}',
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

    # cost: time O(n), heap O(n), stack O(1), io O(n)
    # vars: n = 이슈 수
    # basis: estimate
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
            target = "대기"
            if issue["state"] == "OPEN" and item is None:
                reason = "열린 이슈가 판에 없음"
            elif issue["state"] == "CLOSED" and item is not None and status != "완료":
                reason, target = "닫힌 이슈인데 완료가 아님", "완료"
            elif issue["state"] == "OPEN" and status == "완료":
                reason = "열린 이슈인데 완료"
            if reason:
                print(
                    f"프로젝트 {project['number']} #{issue['number']}: {reason} ({status or '미설정'} → {target})"
                )
                changes.append((issue, target))
        return changes

    # cost: time O(n), heap O(n), stack O(1), io 3
    # vars: n = Status 선택지 수
    # basis: estimate
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

    # cost: time O(n + v), heap O(n + v), stack O(1), io O(p + v)
    # vars: n = Status 선택지 수, p = 뷰 조회 페이지, v = 보드 뷰
    # basis: estimate
    def _setup(self, project: dict[str, Any], field: dict[str, Any]) -> None:
        options = field["options"]
        missing = [
            name
            for name in STATES
            if name not in {option["name"] for option in options}
        ]
        if missing:
            # 기존 ID를 전달해야 기존 항목의 선택 상태가 유지된다.
            additions = [
                {"name": name, "color": "GRAY", "description": ""} for name in missing
            ]
            self._mutate(
                "updateProjectV2Field",
                {"fieldId": field["id"], "singleSelectOptions": options + additions},
                "projectV2Field{... on ProjectV2SingleSelectField{id}}",
            )
            print(f"Status 선택지 추가: {', '.join(missing)}")
        views = self._project_pages(project, "views", "id name layout filter")
        boards = [view for view in views if view["layout"] == "BOARD_LAYOUT"]
        for view in boards:
            current = view.get("filter") or ""
            tokens = shlex.split(current)
            has_filter = any(
                token.startswith("-status:")
                and "완료" in token[len("-status:") :].split(",")
                for token in tokens
            )
            if not has_filter:
                updated = f"{current} -status:완료" if current else "-status:완료"
                self._mutate(
                    "updateProjectV2View",
                    {"viewId": view["id"], "filter": updated},
                    "projectV2View{id}",
                )
                print(f"보드 {view['name']}: 완료 제외 필터 추가")
            print(
                f"보드 {view['name']}: 완료 열 메뉴에서 사람이 'Hide from view' 선택 필요 (열 자체 숨기기 API 미지원)"
            )
        if not boards:
            print("보드 뷰 없음; 필터 적용 대상 없음")

    def _mutate(
        self, name: str, value: dict[str, Any], selection: str
    ) -> dict[str, Any]:
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


# cost: time O(b), heap O(b), stack O(1), io 1
# vars: b = 응답 크기
# basis: estimate
def run_gh(args: list[str], payload: str | None = None) -> dict[str, Any]:
    result = subprocess.run(
        ["gh", *args], input=payload, text=True, capture_output=True, check=False
    )
    if result.returncode:
        raise ProjectError(
            f"gh failed ({result.returncode}): {result.stderr.strip() or result.stdout.strip()}"
        )
    return json.loads(result.stdout)


# cost: time O(n + r), heap O(n), stack O(1), io O(r)
# vars: n = 조회·변경 항목 수, r = 선택한 명령의 조회·변경·출력 횟수
# basis: estimate
def main(argv: list[str] | None = None, gh: Gh = run_gh) -> int:
    parser = StdoutArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="owner/name (기본: 현재 디렉터리 저장소)")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("set", "setup", "check"):
        command_parser = sub.add_parser(command)
        command_parser.add_argument("--repo", default=argparse.SUPPRESS)
        if command == "set":
            command_parser.add_argument("number", type=int)
            command_parser.add_argument("status", choices=STATES)
        if command == "check":
            command_parser.add_argument("--fix", action="store_true")
    parser.set_defaults(fix=False)
    try:
        args = parser.parse_args(argv)
        return ProjectStatus(args.repo, gh).run(args)
    except (ProjectError, OSError, ValueError, KeyError) as error:
        print(f"오류: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
