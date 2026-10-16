import type * as T from "./types.ts";
export const renderJson = (verdict: T.WatcherVerdict): string =>
  `${JSON.stringify(verdict)}\n`;
function ciCell(row: T.PrSnapshot): string {
  if (row.kind !== "open") return "-";
  const was = row.ci.hadPreviousPassingCi ? ", 이전 통과" : "";
  switch (row.ci.kind) {
    case "ci-clean":
      return "통과";
    case "ci-pending":
      return `대기 ${row.ci.pending.length}${was}`;
    case "ci-failing":
      return `실패 ${row.ci.failed.length}${row.ci.pending.length ? `, 대기 ${row.ci.pending.length}` : ""}${was}`;
    case "ci-github-rejected":
      return `실패(GitHub이 실패 check를 보고)${was}`;
    default: {
      const exhaustive: never = row.ci;
      return exhaustive;
    }
  }
}
function reviewCell(row: T.PrSnapshot): string {
  if (row.kind !== "open") return "-";
  const open = row.threads.length;
  return row.reviewAutomationRunning
    ? open
      ? `리뷰 봇 실행 중, 열린 스레드 ${open}`
      : "리뷰 봇 실행 중"
    : open
      ? `열린 스레드 ${open}`
      : "통과";
}
function mergeCell(row: T.PrSnapshot): string {
  if (row.kind === "merged") return "머지됨";
  if (row.kind === "closed") return "닫힘";
  if (row.facts.isDraft) return "draft";
  if (row.facts.reviewDecision === "CHANGES_REQUESTED")
    return "변경 요청";
  return row.facts.mergeable === "CONFLICTING" ||
    row.facts.mergeStateStatus === "DIRTY" ||
    row.facts.mergeStateStatus === "CONFLICTING"
    ? "충돌"
    : "가능";
}
export function renderStatusTable(rows: T.NonEmpty<T.PrSnapshot>): string {
  const lines = ["| PR | CI | 리뷰 | 머지 |", "| --- | --- | --- | --- |"];
  for (const row of rows) {
    const url = `https://github.com/${row.context.owner}/${row.context.repo}/pull/${row.context.number}`;
    lines.push(
      `| [#${row.context.number}](${url}) | ${ciCell(row)} | ${reviewCell(row)} | ${mergeCell(row)} |`
    );
  }
  return `${lines.join("\n")}\n`;
}
function threadLine(thread: T.ReviewThread): string {
  const comment = thread.firstComment;
  return [
    thread.id,
    comment?.path ?? "None",
    comment?.line ?? "None",
    comment?.authorLogin ?? "None",
    `isBugBot=${thread.isBugbot}`,
    `bugbotReviewPasses=${thread.bugbotReviewPasses}`,
    (comment?.body ?? "").split(/\r?\n/, 1)[0]?.slice(0, 180) ?? "",
  ].join(" ");
}
type StatusQueryBlocker = {
  readonly kind: "status-query";
  readonly failures: number;
  readonly failure: { readonly detail: string };
};
function renderBlocker(blocker: T.MergeBlocker | StatusQueryBlocker): string {
  switch (blocker.kind) {
    case "merge-conflicts":
      return [
        "BLOCKER: merge-conflicts",
        `pr=${blocker.pr.number}`,
        `mergeable=${blocker.facts.mergeable}`,
        `mergeStateStatus=${blocker.facts.mergeStateStatus}`,
        "action=CI를 기다리기 전에 merge 충돌을 해결",
      ].join("\n");
    case "review-threads":
      return [
        "BLOCKER: review-threads",
        `pr=${blocker.pr.number}`,
        `unresolved=${blocker.threads.length}`,
        ...blocker.threads.map(threadLine),
      ].join("\n");
    case "failing-checks": {
      const failed = blocker.ci.kind === "ci-failing" ? blocker.ci.failed : [];
      const details = failed.map(
        (check) =>
          `${check.name} ${check.reportedState} ${check.description} ${check.link}`
      );
      if (blocker.ci.kind === "ci-github-rejected")
        details.push(
          `mergeStateStatus=${blocker.ci.github.mergeStateStatus}`,
          `headRollupState=${blocker.ci.github.headRollupState}`
        );
      return [
        "BLOCKER: failing-checks",
        `pr=${blocker.pr.number}`,
        `failed=${failed.length}`,
        ...details,
      ].join("\n");
    }
    case "merge-gate": {
      const action =
        blocker.reason === "closed-without-merge"
          ? "닫힌 PR을 되살리거나 대기열 스택에서 뺌"
          : blocker.reason === "draft-pr"
            ? "merge queue를 기다리기 전에 PR을 ready for review로 바꿈"
            : "merge queue를 기다리기 전에 변경 요청 리뷰를 해결";
      return [
        `BLOCKER: ${blocker.reason}`,
        `pr=${blocker.pr.number}`,
        `action=${action}`,
      ].join("\n");
    }
    case "status-query":
      return [
        "BLOCKER: status-query",
        `failures=${blocker.failures}`,
        `detail=${blocker.failure.detail}`,
        "action=현재 PR 맥락, GitHub 인증, API 가용성을 확인한 뒤 다시 실행",
      ].join("\n");
    default: {
      const exhaustive: never = blocker;
      return exhaustive;
    }
  }
}
export function renderPretty(verdict: T.WatcherVerdict): string {
  switch (verdict.kind) {
    case "QUEUE":
      return `QUEUE: PR ${verdict.queue.length}개를 아래부터 위 순서로 고정 ${verdict.queue.map((pr) => `#${pr.number}`).join(",")}\n`;
    case "STATUS":
      return renderStatusTable(verdict.rows);
    case "WAITING":
      return verdict.reason.kind === "pending-checks"
        ? `WAITING: frontier=#${verdict.frontier.number}; 대기 중인 check ${verdict.reason.pending.length}개\n`
        : `WAITING: frontier=#${verdict.frontier.number}에 차단 요인 없음. merge queue 대기 중(머지 안 된 PR ${verdict.reason.unmergedCount}개)\n`;
    case "ADVANCE":
      return `ADVANCE: #${verdict.merged.number} 머지됨; next=#${verdict.frontier.number}; remaining=${verdict.remaining}\n`;
    case "RETRY":
      return `RETRY: GitHub 상태 조회 실패. ${verdict.retryInSeconds}초 뒤 다시 시도\ndetail=${verdict.failure.detail}\n`;
    case "BLOCKER":
      return `${renderBlocker(verdict.blocker)}\n`;
    case "READY": {
      const detail =
        verdict.scope.kind === "single" && verdict.scope.pr.kind === "ready-pr"
          ? `\nmergeStateStatus=${verdict.scope.pr.proof.ci.github.mergeStateStatus}\nreviewDecision=${verdict.scope.pr.proof.gate.reviewDecision}\nisDraft=${verdict.scope.pr.proof.gate.draft === "draft-allowed"}${verdict.scope.pr.proof.gate.draft === "draft-allowed" ? "\nnote=draft 허용(--allow-draft). draft로 두고 ready로 바꾸지 않음" : ""}`
          : "";
      return `READY: merge 충돌, 미해결 리뷰 스레드, 실패하거나 대기 중인 check가 없음${detail}\n`;
    }
    case "COMPLETE":
      return `COMPLETE: 대기열 스택 머지 완료(PR ${verdict.queue.length}개)\n`;
    case "TIMEOUT":
      if (verdict.reason.kind === "pending-checks")
        return "TIMEOUT: check가 아직 대기 중\n";
      if (verdict.reason.kind === "status-unavailable")
        return "TIMEOUT: GitHub 상태를 끝내 읽지 못함\n";
      return `TIMEOUT: 대기열 스택에 머지 안 된 PR ${verdict.reason.unmergedCount}개가 남음; frontier=#${verdict.reason.frontier.number}\n`;
    default: {
      const exhaustive: never = verdict;
      return exhaustive;
    }
  }
}
