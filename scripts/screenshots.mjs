import { chromium } from "playwright";

const BASE = "http://localhost:3100";

(async () => {
  const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome" });
  const page = await browser.newPage({ viewport: { width: 1400, height: 950 } });

  async function login(email, password) {
    await page.context().clearCookies();
    await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
    await page.fill('input[name="identifier"]', email);
    await page.fill('input[name="password"]', password);
    await Promise.all([page.waitForURL(`${BASE}/app`, { timeout: 15000 }), page.click('button[type="submit"]')]);
  }

  await login("hoc@insure.demo", "Oversee#99");
  await page.waitForTimeout(1800);
  await page.screenshot({ path: "/tmp/shot_hoc_dashboard.png", fullPage: true });

  const href = await page.getAttribute('a[href^="/app/claims/CLM-"]', "href");
  await page.goto(`${BASE}${href}`, { waitUntil: "networkidle" });
  await page.click("text=Fraud & Risk");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "/tmp/shot_fraud_panel.png", fullPage: true });

  await page.click("text=Lifecycle");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "/tmp/shot_lifecycle.png", fullPage: true });

  await page.click("text=E-Signatures");
  await page.waitForTimeout(400);
  await page.screenshot({ path: "/tmp/shot_esign.png", fullPage: true });

  await login("admin@insure.demo", "SysCtrl#99");
  await page.goto(`${BASE}/app/admin/config`, { waitUntil: "networkidle" });
  await page.waitForTimeout(400);
  await page.screenshot({ path: "/tmp/shot_config.png", fullPage: true });

  await browser.close();
  console.log("done");
})();
