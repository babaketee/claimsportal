// Note: no "server-only" import here (unlike most lib/*.ts server modules) —
// this module is also loaded directly by scripts/seed.ts via tsx, outside of
// Next's bundler, where the real "server-only" package always throws.
import * as repo from "./repo";

// ---------------------------------------------------------------------------
// Lightweight configuration engine (design doc section 10): versioned,
// effective-dated settings for fraud thresholds, TAT/SLA targets, approval
// authority limits and document checklists, changed only through a
// maker-checker flow (lib/repo.ts proposeConfig / approveConfig) and fully
// audited via the configurations table's version history.
// ---------------------------------------------------------------------------

export const CONFIG_KEYS = {
  FRAUD_THRESHOLDS: "fraud_thresholds",
  FRAUD_FREQUENCY_WINDOW: "fraud_claim_frequency",
  SLA_TARGETS: "sla_targets",
  APPROVAL_LIMITS: "approval_limits",
} as const;

export interface FraudThresholds {
  mediumFloor: number; // score >= this => at least Medium
  highFloor: number; // score >= this => High
}

export interface FraudFrequencyConfig {
  windowDays: number;
  claimCountFlag: number; // this many-or-more claims in the window triggers the indicator
}

export interface SlaTargets {
  acknowledgementDays: number;
  settlementDays: number;
}

export interface ApprovalLimits {
  claims_officer: number;
  head_of_claims: number;
}

const DEFAULTS = {
  [CONFIG_KEYS.FRAUD_THRESHOLDS]: { mediumFloor: 30, highFloor: 60 } as FraudThresholds,
  [CONFIG_KEYS.FRAUD_FREQUENCY_WINDOW]: { windowDays: 365, claimCountFlag: 3 } as FraudFrequencyConfig,
  [CONFIG_KEYS.SLA_TARGETS]: { acknowledgementDays: 14, settlementDays: 30 } as SlaTargets,
  [CONFIG_KEYS.APPROVAL_LIMITS]: { claims_officer: 300000, head_of_claims: 2000000 } as ApprovalLimits,
};

export function ensureDefaultConfigs() {
  for (const [key, value] of Object.entries(DEFAULTS)) {
    repo.seedConfig(key, value, "System default (see design doc section 10)");
  }
}

export function getConfigValue<T>(key: string): T {
  const row = repo.getActiveConfig(key);
  if (!row) return (DEFAULTS as Record<string, unknown>)[key] as T;
  try {
    return JSON.parse(row.value_json) as T;
  } catch {
    return (DEFAULTS as Record<string, unknown>)[key] as T;
  }
}

export function getFraudThresholds(): FraudThresholds {
  return getConfigValue<FraudThresholds>(CONFIG_KEYS.FRAUD_THRESHOLDS);
}

export function getFraudFrequencyConfig(): FraudFrequencyConfig {
  return getConfigValue<FraudFrequencyConfig>(CONFIG_KEYS.FRAUD_FREQUENCY_WINDOW);
}

export function getSlaTargets(): SlaTargets {
  return getConfigValue<SlaTargets>(CONFIG_KEYS.SLA_TARGETS);
}

export function getApprovalLimits(): ApprovalLimits {
  return getConfigValue<ApprovalLimits>(CONFIG_KEYS.APPROVAL_LIMITS);
}

export const CONFIG_LABELS: Record<string, string> = {
  [CONFIG_KEYS.FRAUD_THRESHOLDS]: "Fraud risk-band thresholds",
  [CONFIG_KEYS.FRAUD_FREQUENCY_WINDOW]: "Fraud claim-frequency window",
  [CONFIG_KEYS.SLA_TARGETS]: "TAT / SLA targets",
  [CONFIG_KEYS.APPROVAL_LIMITS]: "Approval authority limits",
};
