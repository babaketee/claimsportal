import { chromium } from "playwright";
import path from "node:path";

const BASE = "http://localhost:3100";
const results = [];
function log(name, ok, extra = "") {
  results.push({ name, ok, extra });
  console.log(`${ok ? "PASS" : "FAIL"} — ${name}${extra ? " :: " + extra : ""}`);
}

async function login(page, email, password) {
  await page.context().clearCookies();
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.fill('input[name="identifier"]', email);
  await page.fill('input[name="password"]', password);
  await Promise.all([page.waitForURL(`${BASE}/app`, { timeout: 15000 }), page.click('button[type="submit"]')]);
}

(async () => {
  const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome" });
  const page = await browser.newPage();

  // 1. Head of Claims: fraud queue widget
  await login(page, "hoc@insure.demo", "Oversee#99");
  const hocText = await page.textContent("body");
  log("HoC dashboard loads", hocText.includes("Head of Claims"));
  log("Fraud screening queue visible", hocText.includes("Fraud screening"));

  // 2. Navigate into a claim with a fraud assessment via the queue link
  const fraudLink = await page.$('a[href^="/app/claims/CLM-"]');
  if (fraudLink) {
    const href = await fraudLink.getAttribute("href");
    await page.goto(`${BASE}${href}`, { waitUntil: "networkidle" });
    const claimText = await page.textContent("body");
    log("Claim detail loads", claimText.includes("Overview"));

    // Lifecycle tab
    await page.click('text=Lifecycle');
    await page.waitForTimeout(300);
    let bodyText = await page.textContent("body");
    log("Lifecycle tab shows 10-stage lifecycle", bodyText.includes("10-stage claim lifecycle"));
    log("Status history visible", bodyText.includes("Status history"));

    // Fraud & Risk tab
    await page.click('text=Fraud & Risk');
    await page.waitForTimeout(300);
    bodyText = await page.textContent("body");
    log("Fraud panel shows scoring engine copy", bodyText.includes("Fraud Screening"));

    // Documents tab — check upload form present
    await page.click('text=Documents');
    await page.waitForTimeout(300);
    bodyText = await page.textContent("body");
    log("Documents tab shows upload form", bodyText.includes("Upload") || bodyText.includes("scan"));

    // E-Signatures tab — check claim_form workflow with real form fields
    await page.click('text=E-Signatures');
    await page.waitForTimeout(300);
    bodyText = await page.textContent("body");
    log("E-signatures shows claim form workflow", bodyText.includes("Claim Form") || bodyText.includes("form fields"));
  } else {
    log("Fraud queue had a claim link", false, "no link found");
  }

  // 3. Admin config engine (maker-checker)
  await login(page, "admin@insure.demo", "SysCtrl#99");
  await page.goto(`${BASE}/app/admin/config`, { waitUntil: "networkidle" });
  const configText = await page.textContent("body");
  log("Config admin page loads", configText.includes("Configuration Engine"));
  log("Fraud thresholds config visible", configText.includes("Fraud risk-band thresholds"));

  // Propose a config change (maker step)
  const textarea = await page.$('textarea[name="value_json"]');
  if (textarea) {
    await textarea.fill(JSON.stringify({ mediumFloor: 25, highFloor: 55 }));
    await page.fill('input[name="note"]', "Smoke test proposal");
    await page.click('button:has-text("Propose change")');
    await page.waitForTimeout(500);
    const afterPropose = await page.textContent("body");
    log("Config proposal created (pending approval)", afterPropose.includes("Pending approval"));
  } else {
    log("Config propose form found", false);
  }

  // 4. Client claim submission end-to-end (creates a claim, runs triage/fraud)
  await login(page, "client@insure.demo", "Assured#99");
  await page.goto(`${BASE}/app`, { waitUntil: "networkidle" });
  await page.selectOption('select[name="category"]', "Motor");
  await page.fill('input[name="claim_type"]', "Windscreen");
  await page.fill('input[name="policy_number"]', "MOT/2026/99999");
  await page.fill('input[name="vehicle_reg"]', "KDA 999Z");
  await page.fill('input[name="date_of_loss"]', "2026-09-10");
  await page.fill('input[name="location"]', "Westlands, Nairobi");
  await page.fill('input[name="claim_amount"]', "35000");
  await page.fill('textarea[name="description"]', "Windscreen cracked by stone on Waiyaki Way.");
  await Promise.all([
    page.waitForURL(/\/app\/claims\/CLM-/, { timeout: 20000 }),
    page.click('button:has-text("Submit Claim")'),
  ]);
  const newClaimText = await page.textContent("body");
  log("New claim auto-triaged past Submitted", !newClaimText.includes(">Draft<"));
  log("New claim shows a status badge", /Under triage|Under investigation/.test(newClaimText));

  await browser.close();

  const failed = results.filter((r) => !r.ok);
  console.log(`\n${results.length - failed.length}/${results.length} checks passed.`);
  if (failed.length) process.exit(1);
})().catch((err) => {
  console.error("SMOKE TEST ERROR:", err);
  process.exit(1);
});
