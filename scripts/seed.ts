/**
 * Seed script — generates 220+ realistic Kenyan motor & business insurance
 * claims plus their full lifecycle data (reserves, diary entries,
 * communications, expert assignments, settlements, documents with simulated
 * OCR/EXIF metadata, investigator reports, AI fraud assessments, DocuSeal
 * e-signature records, RFQs/bids) so every one of the 12 role dashboards has
 * real data to show on first run — modelled on the Stackwire workflow
 * design document's 10-stage lifecycle and 14-state status model.
 *
 * Run: npm run seed   (wipes and rebuilds data/claims.db)
 */
import fs from "node:fs";
import path from "node:path";
import { getDb, markSeeded } from "../lib/db";
import { DEMO_ACCOUNTS } from "../lib/accounts";
import * as repo from "../lib/repo";
import { ensureDefaultConfigs } from "../lib/config";
import { runFraudScreening } from "../lib/fraud";
import { formKeyForClaimType } from "../lib/claim-forms";
import { stageForStatus, type ClaimCategory, type ClaimStatus, type Urgency } from "../lib/types";

// ---------------------------------------------------------------------------
// Deterministic PRNG so re-runs are stable
// ---------------------------------------------------------------------------
function mulberry32(seed: number) {
  return function () {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rnd = mulberry32(20250915);
const pick = <T,>(arr: T[]): T => arr[Math.floor(rnd() * arr.length)];
const pickWeighted = <T,>(items: [T, number][]): T => {
  const total = items.reduce((s, [, w]) => s + w, 0);
  let r = rnd() * total;
  for (const [item, w] of items) {
    if (r < w) return item;
    r -= w;
  }
  return items[items.length - 1][0];
};
const randInt = (min: number, max: number) => Math.floor(rnd() * (max - min + 1)) + min;
const randFloat = (min: number, max: number) => rnd() * (max - min) + min;
const maybe = (p: number) => rnd() < p;

const TODAY = "2026-09-15";

// ---------------------------------------------------------------------------
// Reset DB
// ---------------------------------------------------------------------------
const dbFile = path.join(process.cwd(), "data", "claims.db");
for (const f of [dbFile, `${dbFile}-wal`, `${dbFile}-shm`]) {
  if (fs.existsSync(f)) fs.rmSync(f);
}
const uploadsDir = path.join(process.cwd(), "data", "uploads");
if (fs.existsSync(uploadsDir)) fs.rmSync(uploadsDir, { recursive: true });
const db = getDb();
ensureDefaultConfigs();

// ---------------------------------------------------------------------------
// Reference data pools
// ---------------------------------------------------------------------------
const FIRST_NAMES = [
  "Kamau", "Wanjiru", "Otieno", "Achieng", "Mwangi", "Njeri", "Kiptoo", "Chebet",
  "Wafula", "Nafula", "Mutua", "Wambui", "Odhiambo", "Auma", "Kipchoge", "Jerop",
  "Njoroge", "Wangui", "Omondi", "Adhiambo", "Kariuki", "Nyambura", "Barasa",
  "Naliaka", "Cheruiyot", "Chepkemoi", "Karanja", "Wairimu", "Ochieng", "Akinyi",
  "Mburu", "Waithera", "Kimani", "Muthoni", "Onyango", "Atieno", "Rotich", "Jepkosgei",
  "Gitau", "Wangari",
];
const LAST_NAMES = [
  "Mwangi", "Otieno", "Kamau", "Njoroge", "Odhiambo", "Kiplagat", "Wafula", "Mutiso",
  "Kariuki", "Omondi", "Kipruto", "Wekesa", "Chege", "Owino", "Maina", "Njuguna",
  "Barasa", "Kilonzo", "Ndungu", "Onyango",
];
const BUSINESS_POOL = [
  { name: "Muthoni Enterprises Ltd", pin: "A000123456B" },
  { name: "Karimi Wholesale", pin: "A000234567C" },
  { name: "Otieno & Sons Construction", pin: "A000345678D" },
  { name: "Transline Logistics Ltd", pin: "A000456789E" },
  { name: "Savannah Retailers Ltd", pin: "A000567890F" },
  { name: "Rift Valley Millers Ltd", pin: "A000678901G" },
  { name: "Coastline Freight Movers", pin: "A000789012H" },
  { name: "Nyanza Agro Processors", pin: "A000890123J" },
  { name: "Kilimani Business Park Ltd", pin: "A000901234K" },
  { name: "Highlands Cold Storage Ltd", pin: "A001012345L" },
  { name: "Zenith Hardware Distributors", pin: "A001123456M" },
  { name: "Pioneer Timber & Fittings", pin: "A001234567N" },
];
const LOCATIONS = [
  "Kasarani, Nairobi", "Mombasa Road, Nairobi", "Westlands, Nairobi", "Karen, Nairobi",
  "Eastleigh, Nairobi", "Ruaka, Kiambu", "Kileleshwa, Nairobi", "Embakasi, Nairobi",
  "Ngong Road, Nairobi", "Kilimani, Nairobi", "Ruiru, Kiambu", "Thika Road, Nairobi",
  "Industrial Area, Nairobi", "Syokimau, Machakos", "Nakuru CBD", "Kisumu CBD",
  "Eldoret Town", "Athi River, Machakos", "Mombasa CBD", "Nyeri Town", "Kitengela",
  "Rongai, Kajiado", "Pangani, Nairobi", "Yaya Centre, Nairobi", "Sagana, Kirinyaga",
];
const MOTOR_TYPES: [string, number, number, "assessor" | "garage" | "investigator"][] = [
  ["Motor Bumper", 25000, 120000, "garage"],
  ["Windscreen", 12000, 55000, "garage"],
  ["Theft", 150000, 1800000, "investigator"],
  ["Third Party Bodily Harm", 200000, 1500000, "investigator"],
  ["Third Party Property", 60000, 550000, "assessor"],
  ["Fire Damage", 90000, 950000, "assessor"],
  ["Flood Damage", 40000, 480000, "assessor"],
  ["Own Damage — Collision", 45000, 620000, "garage"],
];
const BUSINESS_TYPES: [string, number, number][] = [
  ["Business Fire", 150000, 2200000],
  ["Business Burglary", 80000, 1400000],
  ["WIBA", 120000, 900000],
  ["Goods in Transit", 90000, 950000],
  ["Business Interruption", 200000, 1600000],
  ["Public Liability", 100000, 1100000],
];
const GARAGES = [
  ["Kiambu Auto Works Ltd", "0711234567"],
  ["Westlands Auto Garage", "0722334455"],
  ["Mombasa Rd Motor Clinic", "0733445566"],
  ["Nakuru Precision Autobody", "0744556677"],
  ["Kisumu Lakeside Garage", "0755667788"],
];
const ASSESSORS = [
  ["Apollo Surveyors Kenya", "0712345678"],
  ["J. Kamau & Associates", "0723456789"],
  ["Crestline Loss Adjusters", "0734567890"],
  ["Baraka Assessors Ltd", "0745678901"],
];
const INVESTIGATORS = [
  ["Eastleigh Detective Agency", "0713456789"],
  ["Sentinel Risk Investigators", "0724567890"],
  ["Falcon Claims Investigations", "0735678901"],
];
const SPARE_PARTS_PROVIDERS = [
  { name: "AutoSpares Kenya Ltd", brand: "Toyota Genuine", rating: 4.5 },
  { name: "Parts Unlimited Nairobi", brand: "Aftermarket", rating: 3.8 },
  { name: "Motospares East Africa", brand: "TRD / OEM", rating: 4.8 },
  { name: "Tyre & Parts Hub", brand: "Aftermarket", rating: 3.9 },
  { name: "SpeedParts Mombasa", brand: "Toyota OEM", rating: 4.2 },
  { name: "Coast Auto Parts", brand: "Aftermarket", rating: 3.5 },
  { name: "Mombasa Spares Direct", brand: "Toyota Genuine", rating: 4.7 },
];
const PART_DESCRIPTIONS = [
  "Front bumper assembly", "Windscreen (laminated)", "Radiator", "Headlamp unit (LHS)",
  "Rear tail-light cluster", "Side mirror assembly", "Door panel (front, RHS)",
  "Bonnet / hood", "Wing mirror set", "Suspension strut (front pair)",
];

// Weighted pool over the 14-state status model. Draft/Withdrawn/Reopened are
// intentionally rare — most demo claims should show a claim actively moving
// through the pipeline or resolved, matching a mature book of business.
function statusPool(category: ClaimCategory): [ClaimStatus, number][] {
  return [
    ["Draft", 3],
    ["Submitted", 6],
    ["Under triage", 6],
    ["Under investigation and assessment", category === "Motor" ? 16 : 12],
    ["On hold - awaiting information", 5],
    ["Pending approval", 9],
    ["Approved", 7],
    ["Under repair", category === "Motor" ? 8 : 1],
    ["Awaiting reinspection", category === "Motor" ? 5 : 1],
    ["Pending payment", 7],
    ["Paid", 30],
    ["Closed", 9],
    ["Repudiated", 7],
    ["Withdrawn", 3],
  ];
}

function regPlate(): string {
  const letters = () =>
    Array.from({ length: 3 }, () => String.fromCharCode(65 + Math.floor(rnd() * 26))).join("");
  return `K${letters().slice(0, 2)} ${randInt(100, 999)}${String.fromCharCode(
    65 + Math.floor(rnd() * 26)
  )}`;
}

function isoDateBetween(startISO: string, endISO: string): string {
  const start = new Date(startISO).getTime();
  const end = new Date(endISO).getTime();
  return new Date(start + rnd() * (end - start)).toISOString().slice(0, 10);
}

function addDays(iso: string, days: number): string {
  const d = new Date(iso);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

function daysFromToday(delta: number): string {
  const d = new Date(TODAY);
  d.setDate(d.getDate() + delta);
  return d.toISOString().slice(0, 10);
}

const OFFICERS = ["officer@insure.demo"];
const CLIENT_DEMO = "client@insure.demo";

// ---------------------------------------------------------------------------
// 1. Users
// ---------------------------------------------------------------------------
const insertUser = db.prepare(
  "INSERT OR REPLACE INTO users (email, password, role, full_name, phone) VALUES (?, ?, ?, ?, ?)"
);
for (const [email, acct] of Object.entries(DEMO_ACCOUNTS)) {
  insertUser.run(email, acct.password, acct.role, acct.full_name, "0700000000");
}

// ---------------------------------------------------------------------------
// 2. Claims + lifecycle records
// ---------------------------------------------------------------------------
const TOTAL_CLAIMS = 220;
const CLIENT_OWNED_COUNT = 11; // claims visible to the client@insure.demo demo login
let motorSeq = 1;
let businessSeq = 1;
let rfqCounter = 1;

const allRefs: { ref: string; category: ClaimCategory; status: ClaimStatus; amount: number }[] = [];

async function run() {
  for (let i = 0; i < TOTAL_CLAIMS; i++) {
    const category: ClaimCategory = maybe(0.68) ? "Motor" : "Business";
    const year = pickWeighted<number>([
      [2024, 30],
      [2025, 45],
      [2026, 25],
    ]);
    const yearEnd = year === 2026 ? "2026-08-20" : `${year}-12-20`;
    const dateOfLoss = isoDateBetween(`${year}-01-02`, yearEnd);

    // Most claims are reported promptly; a small slice have a long delay,
    // which the fraud engine treats as a "late notification" signal.
    const reportDelay = maybe(0.08) ? randInt(35, 90) : randInt(0, 5);
    let dateReported = addDays(dateOfLoss, reportDelay);
    if (new Date(dateReported) > new Date(TODAY)) dateReported = TODAY;

    const status = pickWeighted(statusPool(category));
    const stage = stageForStatus(status);

    let claim_ref: string;
    let claim_type: string;
    let amount: number;
    let expertTypeDefault: "assessor" | "garage" | "investigator" | null = null;
    let insured_name: string;
    let vehicle_reg: string | null = null;
    let policy_number: string;
    let client_email: string | null = null;

    const isClientOwned = i < CLIENT_OWNED_COUNT;

    if (category === "Motor") {
      claim_ref = `CLM-${year}-M${String(motorSeq++).padStart(4, "0")}`;
      const [label, lo, hi, expert] = pick(MOTOR_TYPES);
      claim_type = label;
      amount = stage <= 1 ? 0 : Math.round(randFloat(lo, hi));
      expertTypeDefault = expert;
      vehicle_reg = regPlate();
      policy_number = `MOT/${year}/${randInt(10000, 99999)}`;
      if (isClientOwned) {
        insured_name = "Kamau Mwangi";
        client_email = CLIENT_DEMO;
      } else {
        insured_name = `${pick(FIRST_NAMES)} ${pick(LAST_NAMES)}`;
      }
    } else {
      claim_ref = `CLM-${year}-B${String(businessSeq++).padStart(4, "0")}`;
      const [label, lo, hi] = pick(BUSINESS_TYPES);
      claim_type = label;
      amount = stage <= 1 ? 0 : Math.round(randFloat(lo, hi));
      expertTypeDefault = maybe(0.7) ? "assessor" : "investigator";
      const biz = pick(BUSINESS_POOL);
      insured_name = biz.name;
      policy_number = `BUS/${year}/${randInt(10000, 99999)}`;
    }

    // A handful of round-number and outlier amounts to give the fraud
    // engine's "round amount" / "amount outlier" indicators something to
    // find, without dominating the dataset.
    if (maybe(0.06) && amount > 0) amount = Math.round(amount / 10000) * 10000;
    if (maybe(0.04) && amount > 0) amount = Math.round(amount * randFloat(2.2, 3.5));

    const urgency: Urgency =
      amount > 700000 || status === "Under investigation and assessment" || status === "On hold - awaiting information"
        ? "High"
        : amount > 200000 || stage <= 4
          ? "Medium"
          : "Low";

    const location = pick(LOCATIONS);
    const description = buildDescription(claim_type, location, status);

    // Create at "Draft" first, then fast-forward to the target status via
    // updateClaimStatus so a real (if compressed) audit-trail entry exists.
    repo.createClaim({
      claim_ref,
      category,
      claim_type,
      status: "Draft",
      policy_number,
      insured_name,
      client_email,
      vehicle_reg,
      location,
      date_of_loss: dateOfLoss,
      date_reported: dateReported,
      claim_amount: amount,
      urgency,
      description,
      assigned_officer: pick(OFFICERS),
      expert_type: stage >= 6 ? expertTypeDefault : null,
    });
    if (status !== "Draft") {
      repo.updateClaimStatus(
        claim_ref,
        status,
        "system",
        `Seed data: fast-forwarded through the lifecycle to "${status}" for demo purposes.`
      );
    }

    allRefs.push({ ref: claim_ref, category, status, amount });

    await seedLifecycle({
      claim_ref,
      category,
      claim_type,
      status,
      stage,
      amount,
      dateOfLoss,
      dateReported,
      expertType: stage >= 6 ? expertTypeDefault : null,
      insured_name,
    });
  }

  markSeeded();

  const byStatus: Record<string, number> = {};
  for (const c of allRefs) byStatus[c.status] = (byStatus[c.status] ?? 0) + 1;

  console.log(`✅ Seeded ${allRefs.length} claims`);
  console.log("   By status:", byStatus);
  console.log(
    `   Motor: ${allRefs.filter((c) => c.category === "Motor").length} · Business: ${
      allRefs.filter((c) => c.category === "Business").length
    }`
  );
  console.log("   Run: npm run dev");
}

function buildDescription(claimType: string, location: string, status: ClaimStatus): string {
  const templates: Record<string, string[]> = {
    "Motor Bumper": ["Rear bumper damaged in parking incident", "Front bumper cracked in low-speed collision"],
    Windscreen: ["Stone chip crack spread across windscreen", "Windscreen shattered by flying debris on highway"],
    Theft: ["Vehicle reported stolen from parking area", "Break-in and theft of vehicle overnight"],
    "Third Party Bodily Harm": ["Pedestrian injured in collision", "Third party sustained injuries in road accident"],
    "Third Party Property": ["Collision with roadside structure", "Vehicle collided with third-party property"],
    "Fire Damage": ["Engine bay fire of undetermined origin", "Electrical fault caused fire damage"],
    "Flood Damage": ["Vehicle flooded while crossing water logged section", "Water damage after heavy rains"],
    "Own Damage — Collision": ["Multi-vehicle collision on highway", "Single-vehicle collision with road barrier"],
    "Business Fire": ["Warehouse fire damaged stock and fittings", "Office fire — equipment and furniture lost"],
    "Business Burglary": ["Break-in reported, stock stolen", "Forced entry overnight, safe and stock taken"],
    WIBA: ["Employee injured on site during works", "Workplace injury claim under WIBA"],
    "Goods in Transit": ["Cargo damaged in transit accident", "Goods lost after truck breakdown en route"],
    "Business Interruption": ["Premises closed after insured peril, income loss claimed", "Trading halted following covered incident"],
    "Public Liability": ["Third party injury on insured premises", "Property damage claim against insured's operations"],
  };
  const base = pick(templates[claimType] ?? ["Claim reported for review"]);
  const suffix = status === "Repudiated" || status === "Withdrawn" ? " — under review, exclusion may apply" : "";
  return `${base}, ${location}${suffix}.`;
}

// ---------------------------------------------------------------------------
// Lifecycle: reserves, assignments, comms, diary, settlements, documents,
// investigator reports and fraud screening.
// ---------------------------------------------------------------------------

async function seedLifecycle(opts: {
  claim_ref: string;
  category: ClaimCategory;
  claim_type: string;
  status: ClaimStatus;
  stage: number;
  amount: number;
  dateOfLoss: string;
  dateReported: string;
  expertType: "assessor" | "garage" | "investigator" | null;
  insured_name: string;
}) {
  const { claim_ref, status, stage, amount, expertType, insured_name, claim_type } = opts;
  const officer = "officer@insure.demo";
  const hoc = "hoc@insure.demo";
  const closed = status === "Paid" || status === "Closed" || status === "Repudiated" || status === "Withdrawn";

  // --- Communications
  if (stage >= 4) {
    repo.logCommunication({
      claim_ref,
      channel: pick(["sms", "email", "call"]),
      direction: "outbound",
      summary: `FNOL acknowledgement sent for ${claim_type} claim`,
      created_by: officer,
      contact_name: insured_name,
      contact_phone: "0700123456",
      consent: true,
    });
  }
  if (stage >= 6) {
    repo.logCommunication({
      claim_ref,
      channel: pick(["sms", "call", "whatsapp"]),
      direction: maybe(0.5) ? "outbound" : "inbound",
      summary: pick([
        "Requested additional supporting documents",
        "Updated claimant on assessment progress",
        "Confirmed appointment with assigned expert",
      ]),
      created_by: officer,
      contact_name: insured_name,
      contact_phone: "0700123456",
      outcome: "Acknowledged",
    });
  }
  if (closed) {
    repo.logCommunication({
      claim_ref,
      channel: "letter",
      direction: "outbound",
      summary:
        status === "Paid" || status === "Closed"
          ? "Settlement confirmation letter sent"
          : status === "Repudiated"
            ? "Repudiation letter sent, reasons explained"
            : "Withdrawal acknowledged",
      created_by: officer,
      contact_name: insured_name,
      contact_phone: "0700123456",
    });
  }

  // --- Reserves (pushed at triage, per the "reserve movements at every
  // stage" design principle — not only at final payout)
  if (stage >= 5 && status !== "Withdrawn") {
    const reserveAmount = Math.min(amount * randFloat(0.4, 0.65), 550000);
    const rId = repo.setReserve({
      claim_ref,
      reserve_type: "initial",
      amount: Math.round(reserveAmount),
      purpose: "Initial reserve set at triage",
      created_by: officer,
      note: `Initial reserve for ${claim_type}`,
    });
    if (rId && stage >= 8) repo.approveReserve(rId, hoc);
    if (rId && stage >= 9 && maybe(0.4)) {
      const supId = repo.setReserve({
        claim_ref,
        reserve_type: "supplemental",
        amount: Math.round(amount * randFloat(0.1, 0.25)),
        purpose: pick(["repair", "legal", "investigation"]),
        created_by: officer,
        note: "Supplemental reserve — revised estimate",
      });
      if (supId && stage >= 9) repo.approveReserve(supId, hoc);
    }
  }

  // --- Expert assignment (Stage 6 — parallel investigation & assessment)
  if (expertType && stage >= 6) {
    const providerPool =
      expertType === "garage" ? GARAGES : expertType === "assessor" ? ASSESSORS : INVESTIGATORS;
    const [name, phone] = pick(providerPool);
    const assignmentId = repo.assignExpert({
      claim_ref,
      expert_type: expertType,
      expert_name: name,
      expert_phone: phone,
      assigned_by: officer,
      estimated_cost: Math.round(amount * 0.08),
      note: `Assigned for ${claim_type}`,
    });
    if (stage >= 7) repo.updateAssignmentStatus(assignmentId, "accepted");
    if (stage >= 9)
      repo.updateAssignmentStatus(assignmentId, "completed", Math.round(amount * randFloat(0.06, 0.1)));
    else if (stage === 8) repo.updateAssignmentStatus(assignmentId, "in_progress");

    if (stage >= 9 && maybe(0.35)) {
      const subId = repo.createDocusealRecord({
        claim_ref,
        workflow: "engagement_letter",
        template_id: null,
        docuseal_submission_id: null,
        signer_name: name,
        signer_email: `${name.toLowerCase().replace(/[^a-z]+/g, ".")}@provider.demo`,
        status: "completed",
        embed_src: null,
        created_by: officer,
      });
      repo.markDocusealCompleted(subId);
    }

    // Investigator "Notification of Incident" report — the 7th claim form,
    // filed by the investigator and feeding the fraud-screening engine.
    if (expertType === "investigator" && maybe(0.55)) {
      const fraudSuspected = maybe(0.16);
      repo.fileInvestigatorReport({
        claim_ref,
        investigator_name: name,
        mode_of_report: pick(["Telephone", "Walk-in", "Media", "Mobile App"]),
        accident_datetime: `${opts.dateOfLoss}T${String(randInt(6, 21)).padStart(2, "0")}:00:00`,
        location: pick(LOCATIONS),
        police_station: `${pick(LOCATIONS).split(",")[0]} Police Station`,
        injured_count: claim_type === "Third Party Bodily Harm" ? randInt(1, 2) : 0,
        deceased_count: 0,
        fraud_suspected: fraudSuspected ? "yes" : "no",
        fraud_basis: fraudSuspected
          ? pick([
              "Inconsistent account of events between insured and third party.",
              "No corroborating witnesses found at the scene despite claimed circumstances.",
              "Vehicle damage pattern inconsistent with the reported collision.",
              "Claimant has a history of similar claims in a short period.",
            ])
          : "",
        created_by: "investigator@insure.demo",
      });
    }
  }

  // --- Diary entries
  if (stage >= 4 && stage < 9) {
    repo.addDiaryEntry({
      claim_ref,
      task: pick([
        `Follow up outstanding documents for ${claim_type}`,
        "Chase assessor report",
        "Confirm reserve adequacy",
        "Call claimant for update",
      ]),
      due_date: maybe(0.3) ? daysFromToday(-randInt(1, 12)) : daysFromToday(randInt(1, 21)),
      assigned_to: officer,
      priority: pick(["normal", "high", "urgent", "low"]),
      created_by: officer,
    });
    if (maybe(0.3)) {
      const doneId = repo.addDiaryEntry({
        claim_ref,
        task: "Initial document checklist review",
        due_date: daysFromToday(-randInt(5, 30)),
        assigned_to: officer,
        priority: "normal",
        created_by: officer,
      });
      repo.completeDiaryEntry(doneId);
    }
  }

  // --- Settlements
  if (stage >= 7 && amount > 0 && status !== "Repudiated" && status !== "Withdrawn") {
    const stlId = repo.recommendSettlement({
      claim_ref,
      amount,
      payee_name: insured_name,
      payee_type: "insured",
      recommended_by: officer,
      note: `Settlement recommendation for ${claim_type}`,
    });
    if (stage >= 8) repo.approveSettlement(stlId, hoc);
    if (status === "Paid") {
      repo.markSettlementPaid(stlId, `FT${randInt(100000000, 999999999)}`);

      // Discharge voucher — signed for most (not all) paid claims, so the
      // "hard precondition to payment" gate has something to demonstrate.
      if (maybe(0.75)) {
        const sub = repo.createDocusealRecord({
          claim_ref,
          workflow: "settlement_discharge",
          template_id: null,
          docuseal_submission_id: null,
          signer_name: insured_name,
          signer_email: "client@insure.demo",
          status: "completed",
          embed_src: null,
          created_by: "finance@insure.demo",
        });
        repo.markDocusealCompleted(sub);
      }
    }

    if (opts.category === "Motor" && expertType && expertType !== "investigator" && maybe(0.6)) {
      const svcAmount = Math.round(amount * randFloat(0.05, 0.12));
      const svcId = repo.recommendSettlement({
        claim_ref,
        amount: svcAmount,
        payee_name: expertType === "garage" ? "Assigned Garage" : "Assigned Assessor",
        payee_type: expertType,
        recommended_by: officer,
        note: "Service provider payment",
      });
      if (stage >= 8) repo.approveSettlement(svcId, hoc);
      if (status === "Paid") repo.markSettlementPaid(svcId, `FT${randInt(100000000, 999999999)}`);
    }
  }

  // --- Repudiation demand letter
  if (status === "Repudiated") {
    repo.registerDocument({
      claim_ref,
      doc_type: "demand_letter",
      filename: `Demand_Letter_${claim_ref}.pdf`,
      file_size: randInt(80, 400) * 1024,
      mime_type: "application/pdf",
      uploaded_by: "legal@insure.demo",
      note: "Repudiation grounds and demand letter",
      ocr_status: "unsupported",
    });
    if (maybe(0.5)) {
      const sub = repo.createDocusealRecord({
        claim_ref,
        workflow: "demand_letter",
        template_id: null,
        docuseal_submission_id: null,
        signer_name: insured_name,
        signer_email: "client@insure.demo",
        status: "completed",
        embed_src: null,
        created_by: "legal@insure.demo",
      });
      repo.markDocusealCompleted(sub);
    }
  }

  // --- Claim form & DPA consent (DocuSeal) — the real per-claim-type form
  if (stage >= 4 && maybe(insured_name === "Kamau Mwangi" ? 0.85 : 0.4)) {
    const formKey = formKeyForClaimType(claim_type);
    const sub = repo.createDocusealRecord({
      claim_ref,
      workflow: "claim_form",
      form_key: formKey,
      template_id: null,
      docuseal_submission_id: null,
      signer_name: insured_name,
      signer_email: "client@insure.demo",
      status: stage >= 5 ? "completed" : "pending",
      embed_src: null,
      created_by: "officer@insure.demo",
    });
    if (stage >= 5) repo.markDocusealCompleted(sub);
  }

  // --- Documents (with simulated OCR text / EXIF metadata for demo realism
  // — real uploads through the app run the live OCR/EXIF pipeline instead)
  type DocSeed = { type: Parameters<typeof repo.registerDocument>[0]["doc_type"]; file: string; ocrText?: string; exif?: object };
  const docSeeds: DocSeed[] = [];
  if (opts.category === "Motor") {
    docSeeds.push({ type: "id_document", file: "National_ID.pdf", ocrText: `REPUBLIC OF KENYA - NATIONAL ID - ${insured_name.toUpperCase()}` });
    if (stage >= 4) {
      const lossDate = new Date(opts.dateOfLoss);
      const mismatch = maybe(0.1);
      const capturedDate = new Date(lossDate.getTime() + (mismatch ? randInt(4, 20) : randInt(0, 1)) * 86400000);
      docSeeds.push({
        type: "photo",
        file: "Damage_Photo_1.jpg",
        exif: {
          captured_at: capturedDate.toISOString(),
          gps_lat: maybe(0.7) ? -1.2921 + randFloat(-0.3, 0.3) : null,
          gps_lng: maybe(0.7) ? 36.8219 + randFloat(-0.3, 0.3) : null,
          camera_make: pick(["Apple", "Samsung", "Xiaomi", null]),
          camera_model: pick(["iPhone 13", "Galaxy A54", "Redmi Note 12", null]),
          has_gps: true,
          days_from_loss: Math.round((capturedDate.getTime() - lossDate.getTime()) / 86400000),
          flags: mismatch
            ? [`Photo capture date is ${Math.round((capturedDate.getTime() - lossDate.getTime()) / 86400000)} day(s) after the claimed loss date — possible staged or recycled loss photo.`]
            : [],
        },
      });
    }
    if (stage >= 6) docSeeds.push({ type: "surveyor_report", file: "Assessment_Report.pdf", ocrText: `ASSESSMENT REPORT for ${claim_ref} — vehicle inspected, damage consistent with reported incident.` });
    if (claim_type === "Theft" || claim_type.includes("Third Party"))
      docSeeds.push({ type: "police_abstract", file: "Police_Abstract.pdf", ocrText: `OB NUMBER ${randInt(1000, 9999)}/${new Date(opts.dateOfLoss).getFullYear()} — POLICE ABSTRACT` });
    if (stage >= 9) docSeeds.push({ type: "invoice", file: "Garage_Invoice.pdf", ocrText: `TAX INVOICE — Total KES ${amount.toLocaleString()}` });
  } else {
    docSeeds.push({ type: "other", file: "Policy_Schedule.pdf", ocrText: `POLICY SCHEDULE — ${policyNumberFor(insured_name)}` });
    if (stage >= 6) docSeeds.push({ type: "surveyor_report", file: "Loss_Adjuster_Report.pdf" });
    if (stage >= 9) docSeeds.push({ type: "invoice", file: "Supplier_Invoice.pdf" });
  }
  for (const d of docSeeds) {
    const doc_id = repo.registerDocument({
      claim_ref,
      doc_type: d.type,
      filename: d.file,
      file_size: randInt(60, 900) * 1024,
      mime_type: d.file.endsWith(".pdf") ? "application/pdf" : "image/jpeg",
      uploaded_by: officer,
      ocr_status: d.ocrText ? "done" : d.exif ? "done" : "unsupported",
    });
    if (d.ocrText) repo.updateDocumentOcr(doc_id, "done", d.ocrText);
    if (d.exif) repo.updateDocumentExif(doc_id, JSON.stringify(d.exif));
  }

  // --- RFQs for a slice of garage-assigned motor claims (spare parts flow)
  if (opts.category === "Motor" && expertType === "garage" && stage >= 6 && maybe(0.35)) {
    const rfq_ref = `RFQ-${opts.dateReported.replace(/-/g, "")}${String(rfqCounter++).padStart(3, "0")}`;
    db.prepare(
      `INSERT INTO rfqs (rfq_ref, claim_ref, part_description, quantity, status, created_by, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?)`
    ).run(rfq_ref, claim_ref, pick(PART_DESCRIPTIONS), randInt(1, 2), stage >= 9 ? "awarded" : "open", officer, new Date().toISOString());
    const bidCount = randInt(2, 4);
    const providers = [...SPARE_PARTS_PROVIDERS].sort(() => rnd() - 0.5).slice(0, bidCount);
    const bidRefs: string[] = [];
    for (const provider of providers) {
      const bidRef = repo.submitBid({
        rfq_ref,
        provider: provider.name,
        brand: provider.brand,
        condition: maybe(0.6) ? "New (Genuine OEM)" : "New (Aftermarket)",
        unit_price: Math.round(randFloat(3500, 45000)),
        lead_days: randInt(1, 5),
        warranty: pick(["3 months", "6 months", "12 months"]),
        rating: provider.rating,
      });
      bidRefs.push(bidRef);
    }
    if (stage >= 9 && bidRefs.length) repo.awardBid(pick(bidRefs), rfq_ref);
  }

  // --- AI-assisted fraud screening & triage (Stage 5) — runs the same
  // production rules engine used live, so the fraud queue is populated with
  // real, explainable scores rather than faked numbers.
  if (stage >= 4) {
    await runFraudScreening(claim_ref, "system");

    // Claims that have progressed well past triage would realistically have
    // already had their fraud assessment reviewed at some point in their
    // history — leave only earlier-stage claims in the live "pending
    // review" queue, so the Head of Claims dashboard reflects a queue being
    // worked down rather than an ever-growing backlog.
    if (stage >= 7) {
      const latest = repo.getLatestFraudAssessment(claim_ref);
      if (latest && latest.review_status === "pending_review") {
        const decision = latest.risk_band === "High" ? "escalate_to_investigator" : maybe(0.5) ? "proceed" : "cleared";
        repo.reviewFraudAssessment(latest.assessment_id, hoc, decision, "Seed data: reviewed during normal claim progression.");
      }
    }
  }
}

function policyNumberFor(name: string): string {
  return `BUS/${new Date().getFullYear()}/${(name.length * 137) % 90000 + 10000}`;
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
