"""새 저장소의 연결 보드를 생성하고 브라우저 자동화 설정의 미확인 범위를 반환한다.
인자: --repo owner/name, --project 번호, --audit 원격 읽기 전용
출력: stdout JSON 구조·뷰·자동화 조회, 종료 0 구조 처리 성공·2 오류; 자동화 검증은 별도
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterator

from project_status import PAGE, STATES, ProjectError, ProjectStatus, run_gh


class ProjectBootstrap(ProjectStatus):
    def ensure(self, number: int | None) -> dict[str, Any]:
        projects = self._linked_projects()
        created = not projects
        if created:
            if number:
                raise ProjectError("requested project is not linked to repository")
            projects = [self._create()]
        project = self._select(projects, number)
        if created or project.get("shortDescription") == self._marker():
            self._initialize(project)
            project = self._select(self._linked_projects(), project["number"])
        return self.inspect(project, created=created)

    def audit(self, number: int | None) -> dict[str, Any]:
        return self.inspect(
            self._select(self._linked_projects(), number), created=False
        )

    def inspect(self, project: dict[str, Any], *, created: bool) -> dict[str, Any]:
        field = self._status_field(project)
        views = self._project_pages(project, "views", "id name layout filter")
        workflows = self._project_pages(project, "workflows", "id name enabled")
        return {
            "repository": self.repo,
            "project": project,
            "created": created,
            "states": [option["name"] for option in field["options"]],
            "views": views,
            "workflows": workflows,
            "automation_verified": False,
            "next": "Read references/project-bootstrap.md; configure and re-read native workflows in authenticated browser, then verify actual issue events. Workflow names/enabled flags alone do not verify filters or target values.",
        }

    def _linked_projects(self) -> list[dict[str, Any]]:
        return self._pages(
            "query($owner:String!,$name:String!,$cursor:String){repository(owner:$owner,name:$name){projectsV2(first:100,after:$cursor){nodes{id number title url closed shortDescription}"
            + PAGE
            + "}}}",
            self.repository,
            "repository",
            "projectsV2",
        )

    def _create(self) -> dict[str, Any]:
        repository = self._query(
            "query($owner:String!,$name:String!){repository(owner:$owner,name:$name){id owner{id} viewerPermission}}",
            self.repository,
        )["repository"]
        if repository["viewerPermission"] not in {"ADMIN", "MAINTAIN", "WRITE"}:
            raise ProjectError(
                "repository write permission required before project creation"
            )
        project = self._mutate(
            "createProjectV2",
            {
                "ownerId": repository["owner"]["id"],
                "repositoryId": repository["id"],
                "title": self.repository["name"],
            },
            "projectV2{id number title url closed shortDescription}",
        )["projectV2"]
        self._mutate(
            "updateProjectV2",
            {
                "projectId": project["id"],
                "shortDescription": self._marker(),
                "public": False,
            },
            "projectV2{id}",
        )
        linked = self._linked_projects()
        if project["id"] not in {item["id"] for item in linked}:
            raise ProjectError(
                f"created {project['url']} but repository link is not confirmed; do not create another"
            )
        return project

    def _initialize(self, project: dict[str, Any]) -> None:
        field = self._status_field(project)
        options = field["options"]
        names = {item["name"] for item in options}
        if names == {"Todo", "In Progress", "Done"}:
            mapping = {"Todo": "대기", "In Progress": "진행", "Done": "완료"}
            options = [{**item, "name": mapping[item["name"]]} for item in options]
            options += [
                {"name": name, "color": "GRAY", "description": ""}
                for name in ("검토", "보류")
            ]
            options.sort(key=lambda item: STATES.index(item["name"]))
            self._mutate(
                "updateProjectV2Field",
                {"fieldId": field["id"], "singleSelectOptions": options},
                "projectV2Field{... on ProjectV2SingleSelectField{id}}",
            )
        elif names != set(STATES):
            raise ProjectError(
                f"unexpected status options in {project['url']}; preserve and review before resuming"
            )
        views = self._project_pages(project, "views", "id name layout filter")
        if len(views) != 1:
            raise ProjectError(
                "initialization requires one untouched view; select an existing view explicitly with project_status setup"
            )
        self._mutate(
            "updateProjectV2View",
            {
                "viewId": views[0]["id"],
                "layout": "BOARD_LAYOUT",
                "filter": '-status:"완료"',
            },
            "projectV2View{id}",
        )
        self._mutate(
            "updateProjectV2",
            {
                "projectId": project["id"],
                "shortDescription": f"Work tracking for {self.repo}",
            },
            "projectV2{id}",
        )

    def _marker(self) -> str:
        return f"just do initialization pending: {self.repo}"

    @staticmethod
    def _select(projects: list[dict[str, Any]], number: int | None) -> dict[str, Any]:
        selected = (
            [p for p in projects if p["number"] == number] if number else projects
        )
        if len(selected) != 1 or selected[0]["closed"]:
            raise ProjectError(
                "select exactly one open linked project with --project; existing projects are preserved"
            )
        return selected[0]


# cost: time O(1), heap O(1), stack O(1), io O(1)
# basis: estimate
@contextlib.contextmanager
def repository_lock(repo: str) -> Iterator[None]:
    root = Path.home() / ".config/skills/project-locks"
    root.mkdir(parents=True, exist_ok=True)
    path = root / (hashlib.sha256(repo.lower().encode()).hexdigest() + ".lock")
    with path.open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


# cost: time O(n), heap O(n), stack O(1), io O(p)
# vars: n = returned projects and fields, p = GitHub query and mutation calls
# basis: estimate
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--project", type=int)
    parser.add_argument(
        "--audit", action="store_true", help="read-only; never create or modify"
    )
    args = parser.parse_args()
    try:
        bootstrap = ProjectBootstrap(args.repo, run_gh)
        if args.audit:
            result = bootstrap.audit(args.project)
        else:
            with repository_lock(args.repo):
                result = bootstrap.ensure(args.project)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ProjectError, OSError, ValueError, KeyError) as error:
        print(f"project bootstrap failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
