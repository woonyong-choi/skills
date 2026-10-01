// claude.ai 계정의 스킬을 원본 저장소의 dist/claude zip과 맞춘다.
// 사용: node claude_upload.mjs [--source <원본>] [--upload <이름,...>] [--delete <이름,...>] [--probe [--click <글자|btn:이름>]...]
// 계정 목록과 원본 zip을 비교해 없는 것을 보고하고, --delete 이름은 삭제, --upload 이름은 업로드한다.
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, chmodSync, readdirSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join, basename } from "node:path";
import { pathToFileURL } from "node:url";

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PROFILE_DIR = join(homedir(), ".config/skills/browser-profile");
const LOG_DIR = join(homedir(), ".config/skills/browser-logs");
const POINTER = join(homedir(), ".config/skills/source");
const SKILLS_URL = "https://claude.ai/customize/skills";
const LOGIN_URL = "https://claude.ai/login";
const LOGIN_WAIT_MS = 15 * 60 * 1000;
const LOGIN_POLL_MS = 10 * 1000;
const MY_SKILLS_URL = "https://claude.ai/customize/skills/yours";

class UiError extends Error {}

const args = parseArgs(process.argv.slice(2));
const playwright = await loadPlaywright();
const source = resolveSource(args.source);
const zips = listZips(source);

mkdirSync(PROFILE_DIR, { recursive: true, mode: 0o700 });
chmodSync(PROFILE_DIR, 0o700);
mkdirSync(LOG_DIR, { recursive: true, mode: 0o700 });

let context = await openContext(true);
try {
  let page = context.pages()[0] ?? (await context.newPage());
  if (!(await isLoggedIn(page))) {
    // headless는 보안 확인(Cloudflare)에 막히거나 로그인이 없을 때만 창을 띄움
    await context.close();
    context = await openContext(false);
    page = context.pages()[0] ?? (await context.newPage());
    if (!(await isLoggedIn(page))) await waitForLogin(page);
  }
  await openMySkills(page);
  if (args.probe) {
    for (const text of args.click) {
      const target = text.startsWith("btn:")
        ? page.getByRole("button", { name: text.slice(4), exact: true })
        : page.getByText(text, { exact: true });
      await target.first().click();
      await page.waitForTimeout(2500);
    }
    await dumpPage(page, "probe");
  } else {
    await syncSkills(page, zips);
  }
} catch (error) {
  console.error(`실패: ${error.message}`);
  process.exitCode = 1;
} finally {
  await context.close();
}

function parseArgs(argv) {
  const out = { source: null, upload: [], delete: [], probe: false, click: [] };
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === "--source") out.source = argv[++i];
    else if (argv[i] === "--upload") out.upload = argv[++i].split(",");
    else if (argv[i] === "--delete") out.delete = argv[++i].split(",");
    else if (argv[i] === "--probe") out.probe = true;
    else if (argv[i] === "--click") out.click.push(argv[++i]);
    else throw new Error(`알 수 없는 인자: ${argv[i]}`);
  }
  return out;
}

async function loadPlaywright() {
  let root;
  try {
    root = execFileSync("npm", ["root", "-g"], { encoding: "utf8" }).trim();
  } catch {
    throw new Error("npm을 찾지 못함. npm install -g playwright-core 필요");
  }
  const entry = join(root, "playwright-core", "index.mjs");
  if (!existsSync(entry)) throw new Error("전역 playwright-core 없음. npm install -g playwright-core 실행");
  return (await import(pathToFileURL(entry).href)).default;
}

function resolveSource(explicit) {
  const candidates = [explicit, process.env.SKILLS_SOURCE];
  if (existsSync(POINTER)) candidates.push(readFileSync(POINTER, "utf8").trim());
  const found = candidates.find((path) => path && existsSync(join(path, "dist/claude")));
  if (!found) throw new Error("원본 저장소를 찾지 못함. --source 지정 필요");
  return found;
}

function listZips(root) {
  const dir = join(root, "dist/claude");
  return readdirSync(dir)
    .filter((file) => file.endsWith(".zip") && existsSync(join(root, basename(file, ".zip"), "SKILL.md")))
    .map((file) => ({ name: basename(file, ".zip"), path: join(dir, file) }));
}

function openContext(headless) {
  return playwright.chromium.launchPersistentContext(PROFILE_DIR, {
    executablePath: CHROME,
    headless,
    viewport: { width: 1280, height: 900 },
    args: ["--disable-blink-features=AutomationControlled"],
  });
}

async function pageState(page) {
  const url = page.url();
  if (/\/(login|logout|onboarding)/.test(url)) return "login";
  const text = await page.evaluate(() => document.body?.innerText ?? "").catch(() => "");
  if (/보안 확인|Just a moment|Verify you are human|사람인지 확인/.test(text)) return "challenge";
  if (!url.startsWith("https://claude.ai/")) return "login";
  return text.length > 200 ? "app" : "loading";
}

async function isLoggedIn(page) {
  await page.goto(SKILLS_URL, { waitUntil: "domcontentloaded" });
  for (let i = 0; i < 10; i += 1) {
    await page.waitForTimeout(3000);
    const state = await pageState(page);
    if (state === "app") return true;
    if (state === "login") return false;
  }
  return false;
}

async function waitForLogin(page) {
  await page.goto(LOGIN_URL, { waitUntil: "domcontentloaded" });
  console.log("Chrome 창에서 claude.ai에 로그인하세요");
  const deadline = Date.now() + LOGIN_WAIT_MS;
  while (Date.now() < deadline) {
    await page.waitForTimeout(LOGIN_POLL_MS);
    if ((await pageState(page)) === "app") return;
  }
  throw new UiError("로그인 대기 15분 초과");
}

async function openMySkills(page) {
  await page.goto(MY_SKILLS_URL, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "스킬 추가", exact: true }).waitFor({ timeout: 30000 }).catch(() => fail(page, "스킬 목록 화면의 '스킬 추가' 버튼을 찾지 못함"));
  await page.waitForTimeout(2000);
}

async function accountSkills(page) {
  const labels = await page.locator("button[aria-label$=' 보기']").evaluateAll((els) => els.map((el) => el.getAttribute("aria-label")));
  return labels.map((label) => label.slice(0, -" 보기".length));
}

async function clickOrFail(page, locator, what) {
  try {
    await locator.first().click({ timeout: 15000 });
  } catch {
    await fail(page, `${what}을(를) 찾지 못함`);
  }
}

async function deleteSkill(page, name) {
  await clickOrFail(page, page.getByRole("button", { name: `${name}에 대한 추가 작업`, exact: true }), `'${name}' 행의 추가 작업 버튼`);
  await clickOrFail(page, page.getByText("제거", { exact: true }), "'제거' 메뉴 항목");
  await page.waitForTimeout(1500);
  const dialog = page.getByRole("dialog");
  if (await dialog.count()) {
    await clickOrFail(page, dialog.getByRole("button", { name: /^(제거|삭제|확인)$/ }), "삭제 확인 대화상자의 확인 버튼");
  }
  await page.waitForTimeout(3000);
}

async function uploadSkill(page, zip) {
  await clickOrFail(page, page.getByRole("button", { name: "스킬 추가", exact: true }), "'스킬 추가' 버튼");
  await clickOrFail(page, page.getByText("스킬 업로드", { exact: true }), "'스킬 업로드' 메뉴 항목");
  const input = page.locator("input[type=file]");
  try {
    await input.first().setInputFiles(zip.path, { timeout: 15000 });
  } catch {
    await fail(page, "업로드 대화상자의 파일 입력을 찾지 못함");
  }
  await clickOrFail(page, page.getByRole("button", { name: "업로드", exact: true }), "대화상자의 '업로드' 버튼");
  await page.waitForTimeout(8000);
  if (await page.getByRole("button", { name: "취소", exact: true }).count()) {
    await fail(page, `'${zip.name}' 업로드 뒤에도 대화상자가 열려 있음(보안 검사 실패나 이름 충돌 가능)`);
  }
}

async function shot(page, label) {
  const path = join(LOG_DIR, `${label}-${Date.now()}.png`);
  await page.screenshot({ path, fullPage: true });
  return path;
}

async function dumpPage(page, label) {
  const path = await shot(page, label);
  const text = await page.evaluate(() => document.body.innerText);
  const buttons = await page.evaluate(() =>
    [...document.querySelectorAll("button,a,[role=tab],[role=menuitem],input")].map(
      (el) => `${el.tagName} ${el.getAttribute("aria-label") ?? ""} ${el.getAttribute("data-testid") ?? ""} ${(el.innerText || el.value || "").slice(0, 60).replace(/\n/g, " ")}`,
    ),
  );
  console.log(`url: ${page.url()}\n스크린샷: ${path}\n--- text\n${text}\n--- controls\n${buttons.join("\n")}`);
}

async function fail(page, what) {
  const path = await shot(page, "fail");
  throw new UiError(`${what}. 스크린샷: ${path}`);
}

async function syncSkills(page, zips) {
  const known = new Set(zips.map((zip) => zip.name));
  for (const name of args.upload) {
    if (!known.has(name)) throw new UiError(`dist/claude에 ${name}.zip 없음`);
  }
  let present = await accountSkills(page);
  for (const name of args.delete) {
    if (present.includes(name)) {
      await deleteSkill(page, name);
      console.log(`삭제: ${name}`);
    } else {
      console.log(`삭제 불필요(계정에 없음): ${name}`);
    }
  }
  for (const name of args.upload) {
    await uploadSkill(page, zips.find((zip) => zip.name === name));
    console.log(`업로드: ${name}`);
  }
  await openMySkills(page);
  present = await accountSkills(page);
  const problems = [
    ...args.delete.filter((name) => present.includes(name)).map((name) => `${name} 아직 있음`),
    ...args.upload.filter((name) => !present.includes(name)).map((name) => `${name} 아직 없음`),
  ];
  if (problems.length) await fail(page, `확인 실패: ${problems.join(", ")}`);
  const missing = zips.map((zip) => zip.name).filter((name) => !present.includes(name));
  console.log(`확인 완료. 계정 스킬 ${present.length}개`);
  console.log(`계정에 없는 zip: ${missing.length ? missing.join(", ") : "없음"}`);
}
