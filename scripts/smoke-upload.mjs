import { chromium } from "playwright";

const BASE = "http://localhost:3100";

(async () => {
  const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome" });
  const page = await browser.newPage();

  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.fill('input[name="identifier"]', "officer@insure.demo");
  await page.fill('input[name="password"]', "Handler#99");
  await Promise.all([page.waitForURL(`${BASE}/app`, { timeout: 15000 }), page.click('button[type="submit"]')]);

  await page.goto(`${BASE}/app`, { waitUntil: "networkidle" });
  const href = await page.getAttribute('a[href^="/app/claims/CLM-"]', "href");
  console.log("Using claim:", href);
  await page.goto(`${BASE}${href}`, { waitUntil: "networkidle" });
  await page.click("text=Documents");
  await page.waitForTimeout(300);

  const fileInput = await page.$('input[type="file"][name="file"]');
  await fileInput.setInputFiles("/tmp/test_ocr.png");
  console.log("Uploading and waiting for OCR/EXIF pipeline (can take several seconds)...");
  await Promise.all([
    page.waitForLoadState("networkidle", { timeout: 30000 }),
    page.click('button:has-text("Upload & scan")'),
  ]);
  await page.waitForTimeout(1000);

  const bodyText = await page.textContent("body");
  console.log("Contains OCR text snippet:", bodyText.includes("POLICE ABSTRACT"));
  console.log("Contains 'done' OCR status badge:", bodyText.toLowerCase().includes("done"));

  await browser.close();
})().catch((e) => {
  console.error("UPLOAD SMOKE TEST ERROR:", e);
  process.exit(1);
});
