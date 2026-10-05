// 개인 계정 배포 어댑터
// 인자: --login, 기본 stdin JSON(skills, dryRun)
// 출력: 변경·대조, 종료 0 성공·1 실패
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, chmodSync, readFileSync, writeFileSync, renameSync, unlinkSync, lstatSync } from "node:fs";
import { homedir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PROFILE_DIR = join(homedir(), ".config/skills/browser-profile");
const LOG_DIR = join(homedir(), ".config/skills/browser-logs");
const RECEIPT = join(homedir(), ".config/skills/claude-account.json");
const SKILLS_URL = "https://claude.ai/customize/skills";
const MY_SKILLS_URL = "https://claude.ai/customize/skills/yours";
const UPLOAD_WAIT_MS = 60 * 1000;

class UiError extends Error {}

export function planAccount(skills, present, receipt) {
  if (new Set(present.map((item) => item.name)).size !== present.length) throw new UiError("duplicate account skill names");
  return skills.flatMap((skill) => {
    const found = present.find((item) => item.name === skill.name);
    const saved = receipt.skills[skill.name];
    const reasons = [];
    if (!found) reasons.push("계정 없음");
    if (!saved) reasons.push("영수증 없음");
    else if (saved.sourceHash !== skill.sourceHash || saved.skillHash !== skill.skillHash) reasons.push("해시 다름");
    if (found && found.description !== skill.description) reasons.push("description 다름");
    if (found && saved && saved.accountUpdatedAt !== found.updatedAt) reasons.push("계정 변경");
    return reasons.length ? [{ ...skill, action: found ? "교체" : "업로드", reason: reasons.join(", ") }] : [];
  });
}

// cost: time O(n² + n·b), heap O(n·b), stack O(1), io O(n·q)
// vars: n = 스킬 수, b = 항목 크기, q = 스킬당 계정 조회·업로드 호출 수
// basis: estimate
export async function syncAccount(skills, account, receipt, save, dryRun) {
  let present = await account.list();
  const plan = planAccount(skills, present, receipt);
  for (const item of plan) console.log(`계정 ${item.action}: ${item.name} (${item.reason})`);
  const names = new Set(skills.map((skill) => skill.name));
  console.log(`계정 원본 밖 보존: ${present.filter((item) => !names.has(item.name)).map((item) => item.name).join(", ") || "없음"}`);
  if (dryRun) return plan;
  for (const item of plan) {
    delete receipt.skills[item.name];
    save(receipt);
    await account.upload(item);
    present = await account.list();
    const found = present.find((skill) => skill.name === item.name);
    if (!found || found.description !== item.description) throw new UiError(`account verification failed: ${item.name}`);
    receipt.skills[item.name] = { sourceHash: item.sourceHash, skillHash: item.skillHash,
      description: item.description, accountUpdatedAt: found.updatedAt, verifiedAt: new Date().toISOString() };
    save(receipt);
    console.log(`계정 확인: ${item.name}`);
  }
  present = await account.list();
  const failed = planAccount(skills, present, receipt);
  if (failed.length) throw new UiError(`final account verification failed: ${failed.map((item) => item.name).join(", ")}`);
  console.log(`계정 대조: 원본 ${skills.length}개 이름·description·영수증 일치`);
  return plan;
}

// cost: time O(b), heap O(b), stack O(1), io 2
// vars: b = 영수증 바이트 수
// basis: estimate
export function readReceipt(path = RECEIPT) {
  if (!existsSync(path)) return { version: 1, skills: {} };
  if (lstatSync(path).isSymbolicLink()) throw new UiError("symlink receipt");
  const receipt = JSON.parse(readFileSync(path, "utf8"));
  if (receipt.version !== 1 || !receipt.skills || typeof receipt.skills !== "object" || Array.isArray(receipt.skills)) throw new UiError("invalid account receipt");
  return receipt;
}

// cost: time O(b), heap O(b), stack O(1), io 4
// vars: b = 영수증 바이트 수
// basis: estimate
export function saveReceipt(receipt, path = RECEIPT) {
  const stage = `${path}.${process.pid}`;
  try {
    writeFileSync(stage, JSON.stringify(receipt, null, 2) + "\n", { mode: 0o600, flag: "wx" });
    renameSync(stage, path);
  } finally {
    if (existsSync(stage)) unlinkSync(stage);
  }
}

// cost: time O(n), heap O(n), stack O(1), io O(q)
// vars: n = 계정 목록 글자 수, q = 로딩 대기 UI 조회 수
// basis: estimate
async function listAccount(page) {
  await openMySkills(page);
  const items = await page.locator('[data-testid="skills-tabbed-list-row"]').evaluateAll((rows) => rows.map((row) => {
    const button = row.querySelector('button[aria-label$=" 보기"]');
    const detail = row.querySelector('span.text-secondary.text-footnote');
    const description = detail ? [...detail.childNodes].filter((node) => node.nodeType === Node.TEXT_NODE).map((node) => node.textContent).join("").trim() : null;
    return { name: button?.getAttribute("aria-label")?.slice(0, -3), description, updatedAt: row.querySelector('time')?.getAttribute('datetime') };
  }));
  if (!items.length || items.some((item) => !item.name || !item.description || !item.updatedAt)) await fail(page, "계정 목록의 이름·description·시각 확인 실패");
  return items;
}

// cost: time O(b + n²), heap O(b + n), stack O(1), io O(n·q)
// vars: b = 입력과 영수증 바이트 수, n = 스킬 수, q = 스킬당 UI 호출 수
// basis: estimate
async function main() {
  const login = process.argv.includes("--login");
  if (process.argv.slice(2).some((arg) => arg !== "--login")) throw new UiError("unknown argument");
  const request = login ? null : JSON.parse(readFileSync(0, "utf8"));
  const receipt = login ? null : readReceipt();
  mkdirSync(PROFILE_DIR, { recursive: true, mode: 0o700 });
  chmodSync(PROFILE_DIR, 0o700);
  mkdirSync(LOG_DIR, { recursive: true, mode: 0o700 });
  const context = await openContext(await loadPlaywright(), login);
  try {
    const page = context.pages()[0] ?? await context.newPage();
    if (login) {
      await page.goto(SKILLS_URL, { waitUntil: "domcontentloaded" });
      console.log("이 창에서 로그인·보안 확인을 마친 뒤 창을 닫으세요. 이후 배포 명령을 다시 실행하세요.");
      await new Promise((resolve) => context.once("close", resolve));
      return;
    }
    if (!(await isLoggedIn(page))) await fail(page, "로그인 만료 또는 보안 확인으로 중단");
    const account = { list: () => listAccount(page), upload: async (item) => {
      if (!existsSync(item.path)) throw new UiError(`missing zip: ${item.name}`);
      if (item.action === "교체") await deleteSkill(page, item.name);
      await uploadSkill(page, item);
    } };
    await syncAccount(request.skills, account, receipt, saveReceipt, request.dryRun);
  } catch (error) {
    if (!(error instanceof UiError)) await fail(context.pages()[0], "계정 UI 처리 실패");
    throw error;
  } finally {
    await context.close();
  }
}

// cost: time O(b), heap O(b), stack O(1), io 2
// vars: b = npm 출력과 로드하는 모듈 크기
// basis: estimate
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

// headless는 Cloudflare에 막히므로 창을 화면 밖에 둔 일반 창으로 실행
function openContext(playwright, login) {
  const hidden = ["--window-position=-32000,-32000", "--window-size=960,720"];
  return playwright.chromium.launchPersistentContext(PROFILE_DIR, {
    executablePath: CHROME,
    headless: false,
    viewport: { width: 1280, height: 900 },
    args: [...(login ? [] : hidden)],
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
    if (state === "login" || state === "challenge") return false;
  }
  return false;
}

async function openMySkills(page) {
  await page.goto(MY_SKILLS_URL, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "스킬 추가", exact: true }).waitFor({ timeout: 30000 }).catch(() => fail(page, "스킬 목록 화면의 '스킬 추가' 버튼을 찾지 못함"));
  await page.locator("button[aria-label$=' 보기']").first().waitFor({ timeout: 30000 }).catch(() => fail(page, "스킬 목록의 행이 로드되지 않음"));
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
  await clickOrFail(page, page.getByRole("menuitem", { name: "제거", exact: true }).or(page.getByText("제거", { exact: true })), "'제거' 메뉴 항목");
  const dialog = page.getByRole("alertdialog").or(page.getByRole("dialog"));
  await dialog.first().waitFor({ timeout: 15000 }).catch(() => fail(page, "삭제 확인 대화상자가 열리지 않음"));
  await clickOrFail(page, dialog.first().getByRole("button", { name: "제거", exact: true }), "삭제 확인 대화상자의 '제거' 버튼");
  await dialog.first().waitFor({ state: "detached", timeout: 15000 }).catch(() => fail(page, "삭제 확인 대화상자가 닫히지 않음"));
  // 삭제 요청이 끝나기 전에 페이지를 이동하면 요청이 중단될 수 있으므로 현재 목록에서 확인
  for (let i = 0; i < 10; i += 1) {
    if (!(await accountSkills(page)).includes(name)) return;
    await page.waitForTimeout(3000);
  }
  await fail(page, `'${name}' 삭제 뒤에도 목록에 남아 있음`);
}

// cost: time O(b + n), heap O(b + n), stack O(1), io O(q)
// vars: b = zip 크기, n = 계정 목록 크기, q = 업로드 완료까지 UI 조회 횟수
// basis: estimate
async function uploadSkill(page, zip) {
  await clickOrFail(page, page.getByRole("button", { name: "스킬 추가", exact: true }), "'스킬 추가' 버튼");
  await page.waitForTimeout(1000);
  await clickOrFail(page, page.getByText("스킬 업로드", { exact: true }), "'스킬 업로드' 메뉴 항목");
  const input = page.locator("input[type=file]");
  try {
    await input.first().setInputFiles(zip.path, { timeout: 15000 });
  } catch {
    await fail(page, "업로드 대화상자의 파일 입력을 찾지 못함");
  }
  await clickOrFail(page, page.getByRole("button", { name: "업로드", exact: true }), "대화상자의 '업로드' 버튼");
  await waitForUpload(page, zip.name);
  // 업로드가 끝나면 상세 화면으로 이동하므로 다음 작업 전에 목록 복귀와 저장 확인이 필요하다.
  await openMySkills(page);
  if (!(await accountSkills(page)).includes(zip.name)) await fail(page, `'${zip.name}' 업로드 뒤 목록에 없음`);

}

async function waitForUpload(page, name) {
  const heading = page.getByText("스킬 업로드", { exact: true }).first();
  const replace = page.getByRole("button", { name: "업로드 및 교체", exact: true });
  const deadline = Date.now() + UPLOAD_WAIT_MS;
  while (Date.now() < deadline) {
    if (await replace.isVisible().catch(() => false)) {
      await clickOrFail(page, replace, `'${name}' 업로드의 '업로드 및 교체' 버튼`);
    }
    if (!(await heading.isVisible().catch(() => false))) return;
    await page.waitForTimeout(2000);
  }
  await fail(page, `'${name}' 보안 스캔 또는 업로드가 60초 안에 끝나지 않음`);
}

async function shot(page, label) {
  const path = join(LOG_DIR, `${label}-${Date.now()}.png`);
  await page.screenshot({ path, fullPage: true });
  return path;
}

async function fail(page, what) {
  const state = await pageState(page);
  const recovery = state === "login" || state === "challenge"
    ? " 로그인·보안 확인 필요: python3 tools/skill-sync/scripts/deploy.py --login" : "";
  const path = await shot(page, "fail");
  throw new UiError(`${what}.${recovery} 스크린샷: ${path}`);
}


if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  try { await main(); } catch (error) {
    console.error(`실패: ${error.message}`);
    process.exitCode = 1;
  }
}
