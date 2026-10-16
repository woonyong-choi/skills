#!/usr/bin/env bun

import { execFileSync } from "node:child_process";
import { join } from "node:path";
import { ensureDependenciesInstalled } from "../bootstrap.ts";
import {
  NotFoundError,
  UsageError,
  openStore,
  parseVerdict,
  type Counts,
  type Frontier,
  type InboxPointer,
  type StandingLine,
  type StatusReport,
  type Store,
  type Unit,
  type Verdict,
} from "./store.ts";

ensureDependenciesInstalled();
const {
  Command: CommanderCommand,
  CommanderError,
  InvalidArgumentError,
  Option,
} = await import("commander");
type Command = InstanceType<typeof CommanderCommand>;

const DISPLAY_LIMIT = 4;

interface Io {
  readonly stdout: (value: string) => void;
  readonly stderr: (value: string) => void;
}

interface GlobalOptions {
  readonly store?: string;
  readonly name?: string;
  readonly json: boolean;
  readonly force: boolean;
}

interface UnitAddOptions {
  readonly track: string;
  readonly brief?: string;
}

interface UnitSetOptions {
  readonly state: string;
  readonly branch?: string;
  readonly pr?: number;
  readonly sha?: string;
}

interface UnitListOptions {
  readonly state?: string;
  readonly track?: string;
}

interface LedgerRecordOptions {
  readonly evidence: string;
  readonly verifier?: string;
}

interface InboxPushOptions {
  readonly report?: string;
}

interface InboxDrainOptions {
  readonly peek: boolean;
}

interface FrontierSetOptions {
  readonly repo?: string;
  readonly prs?: readonly number[];
}

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function positiveInteger(value: string): number {
  const parsed = Number(value);
  if (!/^[1-9]\d*$/.test(value) || !Number.isSafeInteger(parsed)) {
    throw new InvalidArgumentError("양의 정수여야 함");
  }
  return parsed;
}

function prList(value: string): readonly number[] {
  const parts = value.split(",");
  if (parts.some((part) => part.length === 0)) {
    throw new InvalidArgumentError("쉼표로 구분한 PR 번호 목록이어야 함");
  }
  return parts.map(positiveInteger);
}

function countLine(value: Counts): string {
  const entries = Object.entries(value);
  return entries.length === 0
    ? "none"
    : entries.map(([name, count]) => `${name}=${count}`).join(", ");
}

function unitLine(unit: Unit): string {
  return [
    unit.id,
    unit.track,
    unit.state,
    unit.branch,
    unit.pr,
    unit.sha,
    unit.brief,
  ].join("\t");
}

function pointerLine(pointer: InboxPointer): string {
  return [
    pointer.ts,
    pointer.agent,
    pointer.unit,
    pointer.status,
    pointer.report,
  ].join("\t");
}

function compactRows<T>(
  rows: readonly T[],
  format: (row: T) => string,
  empty: string,
  limit: number | null = DISPLAY_LIMIT
): string {
  if (rows.length === 0) {
    return empty;
  }
  const visible = limit === null ? rows : rows.slice(0, limit);
  const lines = visible.map(format);
  if (limit !== null && rows.length > limit) {
    lines.push(`... 외 ${rows.length - limit}개. 전체는 --json`);
  }
  return lines.join("\n");
}

function frontierLine(value: Frontier): string {
  const prs =
    value.prs.length === 0
      ? "none"
      : value.prs
          .map(
            (row) =>
              `${row.branches}#${row.pr}@${row.sha}:${row.state}`
          )
          .join(",");
  return `generation=${value.generation} prs=${prs} lowest-unmerged=${value.lowestUnmerged ?? "none"}`;
}

function statusLines(report: StatusReport): string {
  return [
    `개수: units=${report.units.length}; states=${countLine(report.summary.unitStates)}; ledger=${countLine(report.summary.ledgerVerdicts)}`,
    `변경: ${report.changed}`,
    `inbox: ${report.summary.inboxCount}`,
  ].join("\n");
}

function emit<T>(
  io: Io,
  json: boolean,
  value: T,
  compact: (result: T) => string,
  jsonValue: (result: T) => unknown = (result) => result
): void {
  const rendered = json
    ? JSON.stringify(jsonValue(value), null, 2)
    : compact(value);
  io.stdout(rendered.endsWith("\n") ? rendered : `${rendered}\n`);
}

function repositoryRoot(): string {
  try {
    return execFileSync("git", ["rev-parse", "--show-toplevel"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    }).trim();
  } catch {
    throw new UsageError(
      "--name은 git 저장소 안에서만 쓸 수 있음. 저장소 안에서 실행하거나 --store <dir>를 지정"
    );
  }
}

function storeDirectory(program: Command): string {
  const { store, name } = program.opts<GlobalOptions>();
  if (store !== undefined && store.trim().length > 0) {
    return store;
  }
  if (name === undefined || name.trim().length === 0) {
    throw new UsageError(
      "--name <이름>(.local/orch/<이름>) 또는 --store <dir>를 지정"
    );
  }
  if (!/^[^/\\]+$/.test(name) || name === "." || name === "..") {
    throw new UsageError(`--name에는 폴더 이름 하나만 씀: ${name}`);
  }
  return join(repositoryRoot(), ".local", "orch", name);
}

function frontierRepo(options: FrontierSetOptions): string {
  const value = options.repo;
  if (value === undefined || value.trim().length === 0) {
    throw new UsageError("--repo <dir> 또는 ORCH_REPO를 지정");
  }
  return value;
}

async function runStore<T>(
  program: Command,
  io: Io,
  operation: (store: Store) => Promise<T>,
  compact: (result: T) => string,
  jsonValue?: (result: T) => unknown
): Promise<void> {
  const options = program.opts<GlobalOptions>();
  const store = openStore(storeDirectory(program), {
    force: options.force,
    onLockStolen: (holder) =>
      io.stderr(`pid ${holder} 프로세스가 잡은 스토어 잠금을 가져옴\n`),
    onStaleLock: (holder) =>
      io.stderr(`끝난 프로세스(pid ${holder})의 스토어 잠금을 교체함\n`),
  });
  try {
    const result = await operation(store);
    emit(io, options.json, result, compact, jsonValue);
  } finally {
    await store.close();
  }
}

function leaf(parent: Command, name: string, description: string): Command {
  return parent
    .command(name)
    .description(description)
    .allowExcessArguments(false);
}

function requireSubcommand(program: Command): never {
  storeDirectory(program);
  throw new UsageError("올바른 명령이 필요함");
}

function createProgram(io: Io): Command {
  const program = new CommanderCommand("orch")
    .description("일반 파일로 orchestrate 진행 상태를 기록")
    .usage("[--name <이름> | --store <dir>] [--json] [--force] <command>")
    .configureOutput({ writeOut: io.stdout, writeErr: io.stderr })
    .exitOverride()
    .showHelpAfterError()
    .allowExcessArguments(false)
    .addOption(
      new Option(
        "--name <이름>",
        "저장소의 .local/orch/<이름>을 스토어로 씀(또는 ORCH_NAME)"
      ).env("ORCH_NAME")
    )
    .addOption(
      new Option(
        "--store <dir>",
        "스토어 폴더를 직접 지정, --name보다 먼저(또는 ORCH_STORE)"
      ).env("ORCH_STORE")
    )
    .option("--json", "전체 행을 JSON으로 출력", false)
    .option("--force", "다른 프로세스의 스토어 잠금을 가져옴", false);

  leaf(program, "init", "스토어 폴더 초기화").action(() =>
    runStore(
      program,
      io,
      (store) => store.init(),
      (result) => `초기화함 ${result.store}`
    )
  );

  const unit = program
    .command("unit")
    .description("작업 unit 관리")
    .action(() => requireSubcommand(program));
  leaf(unit, "add <issue>", "하위 이슈 번호로 unit 추가")
    .requiredOption("--track <track>", "unit 트랙")
    .option("--brief <path>", "작업 지시 파일 경로")
    .action((id: string, options: UnitAddOptions) =>
      runStore(
        program,
        io,
        (store) =>
          store.units.add({
            id,
            track: options.track,
            brief: options.brief,
          }),
        unitLine
      )
    );
  leaf(unit, "set <issue>", "unit 갱신")
    .requiredOption("--state <state>", "unit 상태")
    .option("--branch <branch>", "브랜치 이름")
    .option("--pr <number>", "PR 번호", positiveInteger)
    .option("--sha <sha>", "커밋 SHA")
    .action((id: string, options: UnitSetOptions) =>
      runStore(
        program,
        io,
        (store) =>
          store.units.set({
            id,
            state: options.state,
            branch: options.branch,
            pr: options.pr,
            sha: options.sha,
          }),
        unitLine
      )
    );
  leaf(unit, "get <issue>", "unit 조회").action((id: string) =>
    runStore(program, io, (store) => store.units.get(id), unitLine)
  );
  leaf(unit, "list", "unit 목록")
    .option("--state <state>", "상태로 거르기")
    .option("--track <track>", "트랙으로 거르기")
    .action((options: UnitListOptions) =>
      runStore(
        program,
        io,
        (store) => store.units.list(options),
        (rows) => compactRows(rows, unitLine, "(unit 없음)")
      )
    );
  leaf(unit, "counts", "상태별 unit 개수").action(() =>
    runStore(program, io, (store) => store.units.counts(), countLine)
  );

  const ledger = program
    .command("ledger")
    .description("검증 기록 관리")
    .action(() => requireSubcommand(program));
  leaf(ledger, "record", "검증 판정 기록")
    .argument("<pr>", "PR 번호", positiveInteger)
    .argument("<sha>", "커밋 SHA")
    .argument("<verdict>", "검증 판정", parseVerdict)
    .requiredOption("--evidence <path>", "증거 경로")
    .option("--verifier <name>", "검증자 이름")
    .action(
      (
        pr: number,
        sha: string,
        verdict: Verdict,
        options: LedgerRecordOptions
      ) =>
        runStore(
          program,
          io,
          (store) =>
            store.ledger.record({
              pr,
              sha,
              verdict,
              evidence: options.evidence,
              verifier: options.verifier,
            }),
          (row) => `${row.pr}\t${row.sha}\t${row.verdict}`
        )
    );
  leaf(ledger, "check", "검증 판정 확인")
    .argument("<pr>", "PR 번호", positiveInteger)
    .argument("<sha>", "커밋 SHA")
    .action((pr: number, sha: string) =>
      runStore(
        program,
        io,
        (store) => store.ledger.check({ pr, sha }),
        (row) => row.verdict
      )
    );
  leaf(ledger, "summary", "판정별 개수").action(() =>
    runStore(program, io, (store) => store.ledger.summary(), countLine)
  );

  const inbox = program
    .command("inbox")
    .description("에이전트 완료 포인터 관리")
    .action(() => requireSubcommand(program));
  leaf(inbox, "push <agent> <unit> <status>", "inbox 포인터 추가")
    .option("--report <path>", "보고서 경로")
    .action(
      (
        agent: string,
        unitId: string,
        status: string,
        options: InboxPushOptions
      ) =>
        runStore(
          program,
          io,
          (store) =>
            store.inbox.push({
              agent,
              unit: unitId,
              status,
              report: options.report,
            }),
          (result) =>
            `${result.pointer.unit}\t${result.pointer.status}\t${result.filename}`,
          (result) => result.pointer
        )
    );
  leaf(inbox, "drain", "inbox 포인터 수거")
    .option("--peek", "수거하지 않고 읽기만", false)
    .action((options: InboxDrainOptions) =>
      runStore(
        program,
        io,
        (store) =>
          options.peek ? store.inbox.peek() : store.inbox.drain(),
        (rows) => compactRows(rows, pointerLine, "(비어 있음)", null)
      )
    );
  leaf(inbox, "count", "inbox 포인터 개수").action(() =>
    runStore(
      program,
      io,
      (store) => store.inbox.count(),
      String,
      (count) => ({ count })
    )
  );

  const frontier = program
    .command("frontier")
    .description("스택 frontier 관리")
    .action(() => requireSubcommand(program));
  leaf(
    frontier,
    "set",
    "gh로 PR base 체인을 계산해 frontier 설정"
  )
    .addOption(
      new Option(
        "--repo <dir>",
        "저장소 폴더(또는 ORCH_REPO)"
      ).env("ORCH_REPO")
    )
    .option(
      "--prs <n,...>",
      "기대하는 PR 순서 고정(선택)",
      prList
    )
    .action((options: FrontierSetOptions) =>
      runStore(
        program,
        io,
        (store) =>
          store.frontier.set({
            repo: frontierRepo(options),
            prs: options.prs,
          }),
        frontierLine
      )
    );
  leaf(frontier, "show", "frontier 보기").action(() =>
    runStore(program, io, (store) => store.frontier.show(), frontierLine)
  );

  leaf(program, "status", "status.md를 만들고 요약 출력").action(() =>
    runStore(program, io, (store) => store.status.render(), statusLines)
  );

  const standing = program
    .command("standing")
    .description("상시 지시 관리")
    .action(() => requireSubcommand(program));
  leaf(standing, "show", "상시 지시 보기").action(() =>
    runStore(
      program,
      io,
      (store) => store.standing.show(),
      (rows) =>
        compactRows(
          rows,
          (item: StandingLine) => `${item.number}. ${item.line}`,
          "(상시 지시 없음)"
        )
    )
  );
  leaf(standing, "add <line>", "상시 지시 추가").action((line: string) =>
    runStore(
      program,
      io,
      (store) => store.standing.add({ line }),
      (item) => `${item.number}. ${item.line}`
    )
  );

  program.action(() => requireSubcommand(program));
  return program;
}

function handleError(error: unknown, program: Command, io: Io): number {
  if (error instanceof CommanderError) {
    return error.exitCode === 0 ? 0 : 1;
  }
  const json = program.opts<GlobalOptions>().json;
  if (error instanceof NotFoundError) {
    const output = error.output;
    if (output === undefined) {
      io.stderr(`오류: ${error.message}\n`);
    } else {
      emit(io, json, output.json, () => output.compact);
    }
    return 2;
  }
  io.stderr(`오류: ${message(error)}\n`);
  if (error instanceof UsageError) {
    io.stderr(program.helpInformation());
  }
  return 1;
}

export async function main(
  argv: readonly string[],
  io: Io = {
    stdout: (value) => process.stdout.write(value),
    stderr: (value) => process.stderr.write(value),
  }
): Promise<number> {
  const program = createProgram(io);
  try {
    await program.parseAsync(argv, { from: "user" });
    return 0;
  } catch (error) {
    return handleError(error, program, io);
  }
}

if (import.meta.main) {
  process.exitCode = await main(process.argv.slice(2));
}
